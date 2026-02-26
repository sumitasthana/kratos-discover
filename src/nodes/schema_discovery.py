from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel

from models.chunks import ContentChunk
from models.schema_map import SchemaMap
from models.state import Phase1State
from cache.schema_cache import get_cached_schema, cache_schema
from utils.llm_client import get_anthropic_client
from utils.error_handler import handle_anthropic_error, APIError
from config.loader import get_config, get_llm_model, get_llm_max_tokens

logger = structlog.get_logger(__name__)

SCHEMA_DISCOVERY_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "schema_discovery"

# Load configuration
_config = get_config()
MAX_CHUNKS_PER_ENTITY_TYPE = _config.get("schema_discovery.max_chunks_per_entity_type", 3)
MAX_TOTAL_CHUNKS = _config.get("schema_discovery.max_total_chunks", 15)
MAX_RETRIES = _config.get("schema_discovery.max_retries", 3)


def compute_schema_hash(schema_map: SchemaMap) -> str:
    """Deterministic hash of schema content for versioning."""
    content = schema_map.model_dump_json(
        exclude={"schema_version", "avg_confidence"}
    )
    return f"schema-{hashlib.sha256(content.encode()).hexdigest()[:12]}"


def compute_avg_confidence(schema_map: SchemaMap) -> float:
    """Mean confidence across all discovered fields."""
    all_confs = [
        f.confidence
        for entity in schema_map.entities
        for f in entity.fields
    ]
    if not all_confs:
        return 0.0
    return sum(all_confs) / len(all_confs)


def stratified_sample_chunks(chunks: list[ContentChunk]) -> tuple[list[ContentChunk], dict]:
    """
    Sample chunks ensuring all entity types are represented.
    Returns (sampled_chunks, entity_stats).
    """
    # Group chunks by entity type from annotations
    by_entity_type: dict[str, list[ContentChunk]] = defaultdict(list)
    unannotated: list[ContentChunk] = []
    
    for chunk in chunks:
        record_type = chunk.annotations.get("record_type")
        if record_type:
            by_entity_type[record_type].append(chunk)
        else:
            unannotated.append(chunk)
    
    # Build entity stats for accurate counts
    entity_stats = {}
    for entity_type, entity_chunks in by_entity_type.items():
        # Count unique record_ids
        record_ids = set()
        full_records = 0
        stub_records = 0
        for c in entity_chunks:
            rid = c.annotations.get("record_id")
            if rid:
                record_ids.add(rid)
            if c.annotations.get("incomplete_record"):
                stub_records += 1
            else:
                full_records += 1
        
        entity_stats[entity_type] = {
            "total_chunks": len(entity_chunks),
            "unique_records": len(record_ids),
            "full_records": full_records,
            "stub_records": stub_records,
            "record_ids": sorted(record_ids),
        }
    
    # Sample: prioritize table chunks with full records (not stubs)
    sampled: list[ContentChunk] = []
    
    for entity_type, entity_chunks in by_entity_type.items():
        # Prefer table chunks with complete records
        full_table_chunks = [
            c for c in entity_chunks 
            if c.chunk_type == "table" and not c.annotations.get("incomplete_record")
        ]
        full_prose_chunks = [
            c for c in entity_chunks 
            if c.chunk_type == "prose" and not c.annotations.get("incomplete_record")
        ]
        stub_chunks = [
            c for c in entity_chunks 
            if c.annotations.get("incomplete_record")
        ]
        
        # Take up to MAX_CHUNKS_PER_ENTITY_TYPE, prioritizing full tables
        to_sample = full_table_chunks[:MAX_CHUNKS_PER_ENTITY_TYPE]
        remaining = MAX_CHUNKS_PER_ENTITY_TYPE - len(to_sample)
        if remaining > 0:
            to_sample.extend(full_prose_chunks[:remaining])
        remaining = MAX_CHUNKS_PER_ENTITY_TYPE - len(to_sample)
        if remaining > 0:
            to_sample.extend(stub_chunks[:1])  # Include 1 stub as example
        
        sampled.extend(to_sample)
    
    # Add some unannotated chunks for context (headers, metadata)
    remaining_slots = MAX_TOTAL_CHUNKS - len(sampled)
    if remaining_slots > 0:
        # Prefer table chunks from unannotated
        unannotated_tables = [c for c in unannotated if c.chunk_type == "table"]
        unannotated_prose = [c for c in unannotated if c.chunk_type == "prose"]
        sampled.extend(unannotated_tables[:min(2, remaining_slots)])
        remaining_slots = MAX_TOTAL_CHUNKS - len(sampled)
        if remaining_slots > 0:
            sampled.extend(unannotated_prose[:remaining_slots])
    
    logger.info(
        "stratified_sample",
        entity_types=list(by_entity_type.keys()),
        sampled_count=len(sampled),
        entity_stats=entity_stats,
    )
    
    return sampled, entity_stats


def extract_field_labels_from_chunks(chunks: list[ContentChunk]) -> dict[str, list[dict]]:
    """
    Extract actual field labels from table data to ground the schema.
    Returns {entity_type: [{label, example_value, chunk_type}, ...]}.
    """
    fields_by_entity: dict[str, list[dict]] = defaultdict(list)
    seen_labels: dict[str, set] = defaultdict(set)
    
    for chunk in chunks:
        entity_type = chunk.annotations.get("record_type", "unknown")
        
        if chunk.table_data and len(chunk.table_data) >= 2:
            # Vertical key-value table: first column is labels
            if chunk.col_count == 2:
                for row in chunk.table_data:
                    if len(row) >= 2:
                        label = (row[0] or "").strip()
                        value = (row[1] or "").strip()
                        if label and label not in seen_labels[entity_type]:
                            seen_labels[entity_type].add(label)
                            fields_by_entity[entity_type].append({
                                "raw_label": label,
                                "example_value": value[:100] if value else "",
                                "source": "table_kv",
                            })
            # Horizontal table: first row is headers
            else:
                headers = chunk.table_data[0]
                values = chunk.table_data[1] if len(chunk.table_data) > 1 else []
                for i, header in enumerate(headers):
                    label = (header or "").strip()
                    value = (values[i] if i < len(values) else "") or ""
                    if label and label not in seen_labels[entity_type]:
                        seen_labels[entity_type].add(label)
                        fields_by_entity[entity_type].append({
                            "raw_label": label,
                            "example_value": str(value)[:100],
                            "source": "table_horizontal",
                        })
    
    return dict(fields_by_entity)


def _load_schema_discovery_prompt(version: str = "v1.0") -> dict | None:
    """Load schema discovery prompt from YAML file."""
    prompt_file = SCHEMA_DISCOVERY_PROMPTS_DIR / f"{version}.yaml"
    if not prompt_file.exists():
        logger.warning("schema_discovery_prompt_not_found", path=str(prompt_file))
        return None
    
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("schema_discovery_prompt_parse_error", error=str(e))
        return None


def build_discovery_prompt(chunks: list[ContentChunk], entity_stats: dict, extracted_fields: dict) -> str:
    """Build the prompt from chunks with grounded entity stats and field labels."""
    # Build chunk text with annotations
    chunks_text_parts = []
    for chunk in chunks:
        ann = chunk.annotations
        entity_info = ""
        if ann.get("record_type"):
            entity_info = f" [ENTITY: {ann.get('record_type').upper()} ID={ann.get('record_id', '?')}]"
            if ann.get("incomplete_record"):
                entity_info += " [STUB/INCOMPLETE]"
        chunks_text_parts.append(
            f"[{chunk.chunk_type.upper()}]{entity_info}\n{chunk.content_text[:800]}"
        )
    chunks_text = "\n\n---\n\n".join(chunks_text_parts)
    
    # Build entity stats summary
    stats_lines = []
    total_records = 0
    for entity_type, stats in entity_stats.items():
        stats_lines.append(
            f"- {entity_type.upper()}: {stats['unique_records']} records "
            f"({stats['full_records']} full, {stats['stub_records']} stubs)"
        )
        total_records += stats['unique_records']
    entity_stats_text = "\n".join(stats_lines) if stats_lines else "No annotated entities found"
    
    # Build extracted fields summary
    fields_lines = []
    for entity_type, fields in extracted_fields.items():
        field_labels = [f['raw_label'] for f in fields]
        fields_lines.append(f"- {entity_type.upper()} fields: {field_labels}")
    extracted_fields_text = "\n".join(fields_lines) if fields_lines else "No fields extracted from tables"
    
    # Build JSON example with dynamic values
    control_record_count = entity_stats.get('control', {}).get('unique_records', 0)
    json_example = f'''{{
  "document_format": "docx",
  "structural_pattern": "vertical_key_value_tables",
  "structural_confidence": 0.85,
  "inferred_document_category": "grc_library",
  "entities": [
    {{
      "discovered_label": "Control",
      "identifier_field": "control_id",
      "record_count": {control_record_count},
      "fields": [
        {{
          "raw_label": "Control ID",
          "canonical_field": "control_id",
          "inferred_type": "identifier",
          "confidence": 0.95,
          "mapping_rationale": "Field labeled 'Control ID' contains unique identifiers like C-001",
          "example_values": ["C-001", "C-002"]
        }}
      ]
    }}
  ],
  "relationships": [],
  "unmapped_fields": [],
  "anomalies": ["Specific anomaly: Record C-005 missing field X"],
  "total_records_estimated": {total_records},
  "schema_version": "",
  "avg_confidence": 0.85
}}'''
    
    # Try to load from YAML
    prompt_config = _load_schema_discovery_prompt("v1.0")
    if prompt_config:
        role = prompt_config.get("role", "")
        instructions = prompt_config.get("instructions", "")
        
        # Format the instructions with dynamic values
        formatted_instructions = instructions.format(
            entity_stats_text=entity_stats_text,
            extracted_fields_text=extracted_fields_text,
            chunks_text=chunks_text,
            json_example=json_example,
        )
        
        return f"{role}\n{formatted_instructions}"
    
    # Fallback to inline prompt if YAML not found
    logger.warning("schema_discovery_using_fallback_prompt")
    return f"""You are a schema discovery expert analyzing a GRC (Governance, Risk, Compliance) document.

## GROUND TRUTH FROM PARSER (use these exact counts and field labels):

ENTITY COUNTS (from document annotations):
{entity_stats_text}

FIELD LABELS EXTRACTED FROM TABLES (use these exact labels, do NOT invent fields):
{extracted_fields_text}

## DOCUMENT CHUNKS (samples from each entity type):

{chunks_text}

## YOUR TASK:

Create a schema map for this document. You MUST:
1. Include ALL entity types listed above (Policy, Control, Risk, etc.)
2. Use the EXACT field labels extracted from tables - do NOT invent field names
3. Use the EXACT record counts from the parser annotations
4. For each field, provide:
   - mapping_rationale: explain WHY this field maps to the canonical name
   - example_values: include 1-2 actual values from the chunks above
5. For anomalies, be SPECIFIC: name the exact record IDs and fields affected

Return ONLY valid JSON (no markdown, no explanation):

{json_example}

CONSTRAINTS:
- inferred_type: identifier, text, date, enum, composite_enum, reference_list, number, boolean, person_or_role, list, unknown
- structural_pattern: vertical_key_value_tables, horizontal_tables, section_based_prose, flat_spreadsheet, mixed, unknown
- inferred_document_category: grc_library, regulatory, data_dictionary, unknown
- relationships: LEAVE AS EMPTY ARRAY [] - do not add relationships
- unmapped_fields: list of field name strings that couldn't be mapped
- anomalies: list of SPECIFIC descriptions with record IDs

CRITICAL: 
1. Only use field labels that appear in the FIELD LABELS EXTRACTED section above. Do NOT hallucinate fields.
2. You MUST include ALL entity types from the ENTITY COUNTS section (Policy, Control, Risk).
3. Leave relationships as empty array []."""


def call_claude_structured(prompt: str, output_model: type[BaseModel]) -> BaseModel:
    """Call Claude with structured output."""
    import time
    client = get_anthropic_client()
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            
            # Extract content with better error handling
            if not response.content:
                logger.error("claude_empty_response", attempt=attempt, response_obj=str(response))
                raise ValueError("Claude returned empty response content")
            
            content = response.content[0].text
            if not content or not content.strip():
                logger.error("claude_empty_text", attempt=attempt, content_length=len(content) if content else 0)
                raise ValueError(f"Claude returned empty or whitespace-only text: {repr(content)}")
            
            logger.debug("claude_response_received", attempt=attempt, content_length=len(content))
            data = json.loads(content)
            return output_model(**data)
        except json.JSONDecodeError as e:
            content_preview = content[:200] if content else ""
            logger.warning("claude_json_parse_failed", attempt=attempt, error=str(e), content_preview=content_preview)
            last_error = e
            if attempt == MAX_RETRIES - 1:
                raise ValueError(f"Failed to parse Claude response as JSON after {MAX_RETRIES} attempts. Last error: {str(e)}. Response preview: {content[:500] if content else 'empty'}")
            # Exponential backoff before retry
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            # Convert Anthropic SDK exceptions to user-friendly errors
            api_error = handle_anthropic_error(e)
            logger.warning(
                "claude_call_failed",
                attempt=attempt,
                error_type=api_error.error_type,
                message=api_error.message,
                is_retryable=api_error.is_retryable,
            )
            last_error = api_error
            if attempt == MAX_RETRIES - 1:
                raise api_error
            # Exponential backoff before retry
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    raise RuntimeError("Exhausted retries")


def schema_discovery_agent(state: Phase1State) -> dict:
    """LangGraph node: Schema Discovery Agent."""
    chunks = state.get("chunks", [])

    if not chunks:
        logger.warning("schema_discovery_no_chunks")
        return {
            "schema_map": None,
            "errors": [*state.get("errors", []), "No chunks provided to schema discovery"],
        }

    # Stratified sampling: ensure all entity types are represented
    sample_chunks, entity_stats = stratified_sample_chunks(chunks)
    
    # Extract field labels from table data to ground the schema
    extracted_fields = extract_field_labels_from_chunks(chunks)
    
    logger.info(
        "schema_discovery_grounding",
        entity_types=list(entity_stats.keys()),
        extracted_field_counts={k: len(v) for k, v in extracted_fields.items()},
    )

    # Check cache first (disabled for now to ensure fresh discovery)
    # doc_format = state.get("file_path", "unknown").split(".")[-1].lower()
    # cached = get_cached_schema(doc_format)
    # if cached:
    #     logger.info("schema_discovery_cache_hit", document_format=doc_format)
    #     return {
    #         "schema_map": cached,
    #         "prompt_versions": {
    #             **state.get("prompt_versions", {}),
    #             "schema_discovery": "v2_cached",
    #         },
    #     }

    # Build prompt with grounded data and call Claude
    prompt = build_discovery_prompt(sample_chunks, entity_stats, extracted_fields)
    
    try:
        schema_map = call_claude_structured(prompt, SchemaMap)
    except Exception as e:
        logger.error("schema_discovery_claude_failed", error=str(e))
        # Create minimal fallback schema from extracted fields
        logger.warning("schema_discovery_using_fallback", reason=str(e))
        from models.schema_map import Entity, Field
        
        fallback_entities = []
        for entity_type in entity_stats.keys():
            fields = []
            if entity_type in extracted_fields:
                for field_name in extracted_fields[entity_type][:5]:  # Limit to 5 fields per entity
                    fields.append(Field(
                        field_label=field_name,
                        field_type="string",
                        required=False,
                        description=f"Field: {field_name}"
                    ))
            
            fallback_entities.append(Entity(
                discovered_label=entity_type,
                entity_type=entity_type.upper(),
                fields=fields,
                confidence=0.5,
                evidence_count=entity_stats.get(entity_type, 0)
            ))
        
        schema_map = SchemaMap(
            entities=fallback_entities,
            relationships=[],
            structural_pattern="table",
            confidence=0.5,
            anomalies=[]
        )

    # Compute derived fields
    schema_map.schema_version = compute_schema_hash(schema_map)
    schema_map.avg_confidence = compute_avg_confidence(schema_map)

    # Cache result
    doc_format = state.get("file_path", "unknown").split(".")[-1].lower()
    cache_schema(doc_format, schema_map)

    logger.info(
        "schema_discovery_completed",
        entities=len(schema_map.entities),
        entity_types=[e.discovered_label for e in schema_map.entities],
        avg_confidence=schema_map.avg_confidence,
        structural_pattern=schema_map.structural_pattern,
    )

    return {
        "schema_map": schema_map,
        "prompt_versions": {
            **state.get("prompt_versions", {}),
            "schema_discovery": "v2",
        },
    }
