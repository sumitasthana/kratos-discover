"""GRC Component Extractor Node for the Agent1 pipeline.

Node 3.5: Extracts Policy, Risk, and Control components from table chunks
using the discovered schema. Runs between Confidence Gate (Node 3) and
Requirement Atomizer (Node 4).
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from models.chunks import ContentChunk
from models.grc_components import (
    ControlComponent,
    GRCComponentsResponse,
    PolicyComponent,
    RiskComponent,
)
from models.schema_map import SchemaMap
from models.state import Phase1State
from utils.llm_client import get_anthropic_client

logger = structlog.get_logger(__name__)

# Configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "grc_extractor"


class GRCComponentExtractorNode:
    """
    LangGraph node that extracts Policy, Risk, and Control components
    from table chunks using the GRC schema.
    
    Input: state.chunks (ContentChunk[]), state.schema_map
    Output: partial state update with grc_components and component_index
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._prompt_cache: dict[str, dict] = {}

    def __call__(self, state: Phase1State) -> dict:
        """LangGraph node entrypoint. Returns partial state update."""
        chunks = state.get("chunks", [])
        schema_map = state.get("schema_map")

        if not chunks:
            logger.warning("grc_extractor_no_chunks")
            return self._empty_result("No chunks provided")

        if not schema_map:
            logger.warning("grc_extractor_no_schema_map")
            return self._empty_result("No schema map provided")

        logger.info(
            "grc_extractor_started",
            total_chunks=len(chunks),
        )

        # Filter to extractable table chunks grouped by record_type
        chunks_by_type = self._get_extractable_chunks(chunks)
        
        if not chunks_by_type:
            logger.info("grc_extractor_no_table_chunks")
            return self._empty_result("No table chunks with record_type annotations")

        logger.info(
            "grc_extractor_chunks_grouped",
            types=list(chunks_by_type.keys()),
            counts={k: len(v) for k, v in chunks_by_type.items()},
        )

        # Load prompt configuration
        prompt_config = self._load_prompt("v1.0")
        if not prompt_config:
            logger.error("grc_extractor_prompt_load_failed")
            return self._empty_result("Failed to load prompt configuration")

        # Extract components for each type
        all_policies: list[PolicyComponent] = []
        all_risks: list[RiskComponent] = []
        all_controls: list[ControlComponent] = []
        validation_errors: list[str] = []

        for record_type, type_chunks in chunks_by_type.items():
            try:
                components = self._extract_components(
                    record_type=record_type,
                    chunks=type_chunks,
                    schema_map=schema_map,
                    prompt_config=prompt_config,
                )
                
                if record_type == "policy":
                    all_policies.extend(components)
                elif record_type == "risk":
                    all_risks.extend(components)
                elif record_type == "control":
                    all_controls.extend(components)
                    
            except Exception as e:
                logger.error(
                    "grc_extractor_type_failed",
                    record_type=record_type,
                    error=str(e),
                )
                validation_errors.append(f"Failed to extract {record_type}: {str(e)}")

        # Build response
        grc_response = GRCComponentsResponse(
            policies=all_policies,
            risks=all_risks,
            controls=all_controls,
        )

        # Validate cross-references
        cross_ref_errors = self._validate_cross_references(grc_response)
        validation_errors.extend(cross_ref_errors)

        # Build cross-reference index
        grc_response.cross_reference_index = self._build_cross_reference_index(grc_response)

        # Build extraction summary
        grc_response.extraction_summary = {
            "total_policies": len(all_policies),
            "total_risks": len(all_risks),
            "total_controls": len(all_controls),
            "validation_errors": validation_errors,
            "extraction_timestamp": datetime.utcnow().isoformat(),
        }

        # Build component_index for atomizer linkage
        component_index = self._build_component_index(grc_response)

        logger.info(
            "grc_extractor_completed",
            policies=len(all_policies),
            risks=len(all_risks),
            controls=len(all_controls),
            validation_errors=len(validation_errors),
        )

        return {
            "grc_components": grc_response,
            "component_index": component_index,
            "prompt_versions": {
                **state.get("prompt_versions", {}),
                "grc_extractor": "v1.0",
            },
        }

    def _empty_result(self, error_msg: str) -> dict:
        """Return empty result with error."""
        return {
            "grc_components": GRCComponentsResponse(
                extraction_summary={"error": error_msg}
            ),
            "component_index": {},
            "errors": [error_msg],
        }

    def _get_extractable_chunks(
        self, chunks: list[ContentChunk]
    ) -> dict[str, list[ContentChunk]]:
        """Group table chunks by record_type for extraction."""
        by_type: dict[str, list[ContentChunk]] = defaultdict(list)
        for chunk in chunks:
            record_type = chunk.annotations.get("record_type")
            if chunk.chunk_type == "table" and record_type:
                by_type[record_type.lower()].append(chunk)
        return dict(by_type)

    def _load_prompt(self, version: str) -> dict | None:
        """Load prompt configuration from YAML file."""
        if version in self._prompt_cache:
            return self._prompt_cache[version]

        prompt_file = PROMPTS_DIR / f"{version}.yaml"
        if not prompt_file.exists():
            logger.warning("grc_extractor_prompt_not_found", path=str(prompt_file))
            return None

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            self._prompt_cache[version] = config
            return config
        except Exception as e:
            logger.error("grc_extractor_prompt_parse_error", error=str(e))
            return None

    def _extract_components(
        self,
        record_type: str,
        chunks: list[ContentChunk],
        schema_map: SchemaMap,
        prompt_config: dict,
    ) -> list[PolicyComponent | RiskComponent | ControlComponent]:
        """Extract components of a specific type from chunks."""
        # Build prompt
        system_prompt = self._build_system_prompt(prompt_config, record_type, schema_map)
        user_message = self._build_user_message(prompt_config, chunks)

        # Call Claude with retries
        client = get_anthropic_client()
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    temperature=0.0,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                content = response.content[0].text if response.content else "[]"
                
                logger.debug(
                    "grc_extractor_llm_response",
                    record_type=record_type,
                    response_length=len(content),
                )

                # Parse response
                components = self._parse_response(content, record_type, chunks)
                
                logger.info(
                    "grc_extractor_batch",
                    record_type=record_type,
                    chunks_processed=len(chunks),
                    components_extracted=len(components),
                )
                
                return components

            except Exception as e:
                last_error = e
                logger.warning(
                    "grc_extractor_retry",
                    attempt=attempt,
                    record_type=record_type,
                    error=str(e),
                )
                time.sleep(RETRY_BACKOFF_BASE ** attempt)

        raise last_error or RuntimeError("LLM call failed")

    def _build_system_prompt(
        self, prompt_config: dict, record_type: str, schema_map: SchemaMap
    ) -> str:
        """Build system prompt for component extraction."""
        role = prompt_config.get("role", "")
        instructions = prompt_config.get("instructions", "")
        
        # Get component-specific fields from config
        component_types = prompt_config.get("component_types", {})
        component_spec = component_types.get(record_type, {})
        
        # Build schema context
        schema_context = self._build_schema_context(schema_map, record_type)
        
        return f"""{role}

You are extracting {record_type.upper()} components.

{instructions}

SCHEMA CONTEXT:
{schema_context}

COMPONENT FIELDS FOR {record_type.upper()}:
{json.dumps(component_spec, indent=2)}

OUTPUT FORMAT:
Return a JSON array of {record_type} components. Each component must have:
- component_id: The ID from the source (e.g., P-001, R-001, C-001)
- All applicable fields from the component specification above

Example output:
[
  {{"component_id": "{record_type[0].upper()}-001", "component_type": "{record_type}", ...}}
]
"""

    def _build_schema_context(self, schema_map: SchemaMap, record_type: str) -> str:
        """Build schema context for the prompt."""
        lines = [f"Document Format: {schema_map.document_format}"]
        
        for entity in schema_map.entities:
            if entity.discovered_label.lower() == record_type:
                lines.append(f"\nEntity: {entity.discovered_label}")
                lines.append(f"Record Count: {entity.record_count}")
                lines.append("Fields:")
                for field in entity.fields:
                    lines.append(f"  - {field.raw_label} ({field.inferred_type})")
        
        return "\n".join(lines)

    def _build_user_message(
        self, prompt_config: dict, chunks: list[ContentChunk]
    ) -> str:
        """Build user message with chunk content."""
        template = prompt_config.get("user_message_template", "Extract components from:\n{chunks_content}")
        
        chunks_content = []
        for chunk in chunks:
            record_id = chunk.annotations.get("record_id", "unknown")
            chunks_content.append(
                f"--- CHUNK {chunk.chunk_id} [RECORD: {record_id}] ---\n"
                f"Location: {chunk.source_location}\n\n"
                f"{chunk.content_text}\n"
            )
        
        return template.format(chunks_content="\n".join(chunks_content))

    def _parse_response(
        self,
        content: str,
        record_type: str,
        chunks: list[ContentChunk],
    ) -> list[PolicyComponent | RiskComponent | ControlComponent]:
        """Parse LLM response into component objects."""
        # Extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            logger.warning("grc_extractor_no_json_array", content_preview=content[:200])
            return []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning("grc_extractor_json_parse_error", error=str(e))
            return []

        if not isinstance(data, list):
            data = [data]

        # Build chunk lookup
        chunk_map = {c.chunk_id: c for c in chunks}
        record_id_to_chunk = {
            c.annotations.get("record_id"): c 
            for c in chunks 
            if c.annotations.get("record_id")
        }

        components = []
        for item in data:
            if not isinstance(item, dict):
                continue

            # Normalize fields
            item = self._normalize_component(item, record_type)
            
            # Find source chunk
            component_id = item.get("component_id", "")
            source_chunk = record_id_to_chunk.get(component_id)
            if source_chunk:
                item["source_chunk_id"] = source_chunk.chunk_id
                item["source_location"] = source_chunk.source_location

            # Create appropriate component type
            try:
                if record_type == "policy":
                    components.append(PolicyComponent(**item))
                elif record_type == "risk":
                    components.append(RiskComponent(**item))
                elif record_type == "control":
                    components.append(ControlComponent(**item))
            except Exception as e:
                logger.warning(
                    "grc_extractor_component_parse_error",
                    record_type=record_type,
                    component_id=component_id,
                    error=str(e),
                )

        return components

    def _normalize_component(self, item: dict, record_type: str) -> dict:
        """Normalize component fields (lists, dates, control types)."""
        # Normalize list fields
        list_fields = [
            "related_controls", "related_risks", "related_policies",
            "mitigation_controls", "related_regulations", "detailed_requirements",
            "roles_responsibilities",
        ]
        for field in list_fields:
            if field in item:
                item[field] = self._normalize_list(item[field])

        # Normalize date fields
        date_fields = ["effective_date", "review_cycle"]
        for field in date_fields:
            if field in item:
                item[field] = self._normalize_date_field(item[field])

        # Normalize control_type for controls
        if record_type == "control" and "control_type" in item:
            item["control_type"] = self._normalize_control_type_field(item["control_type"])

        return item

    def _normalize_list(self, value: Any) -> list[str]:
        """Split comma-separated strings into arrays."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        if isinstance(value, str):
            # Split on comma, semicolon, or newline
            items = re.split(r'[,;\n]', value)
            return [item.strip() for item in items if item.strip()]
        return [str(value)]

    def _normalize_date_field(self, value: Any) -> str | None:
        """Normalize date field, keeping original if unparseable."""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() if value.strip() else None
        return str(value)

    def _normalize_control_type_field(self, value: Any) -> dict | str:
        """Parse control_type like 'Preventive / Automated' into {nature, automation}."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            # Try to parse "Nature / Automation" format
            if "/" in value:
                parts = [p.strip() for p in value.split("/")]
                if len(parts) >= 2:
                    return {"nature": parts[0], "automation": parts[1]}
            return value
        return str(value)

    def _validate_cross_references(
        self, grc: GRCComponentsResponse
    ) -> list[str]:
        """Validate that cross-references point to existing components."""
        errors = []
        
        # Build set of all component IDs
        all_ids = set()
        for p in grc.policies:
            if p.component_id:
                all_ids.add(p.component_id)
        for r in grc.risks:
            if r.component_id:
                all_ids.add(r.component_id)
        for c in grc.controls:
            if c.component_id:
                all_ids.add(c.component_id)

        # Check policy references
        for p in grc.policies:
            for ref in (p.related_controls or []):
                if ref and ref not in all_ids:
                    errors.append(f"Policy {p.component_id} references missing control {ref}")
            for ref in (p.related_risks or []):
                if ref and ref not in all_ids:
                    errors.append(f"Policy {p.component_id} references missing risk {ref}")

        # Check risk references
        for r in grc.risks:
            for ref in (r.related_controls or []) + (r.mitigation_controls or []):
                if ref and ref not in all_ids:
                    errors.append(f"Risk {r.component_id} references missing control {ref}")
            for ref in (r.related_policies or []):
                if ref and ref not in all_ids:
                    errors.append(f"Risk {r.component_id} references missing policy {ref}")

        # Check control references
        for c in grc.controls:
            for ref in (c.related_policies or []):
                if ref and ref not in all_ids:
                    errors.append(f"Control {c.component_id} references missing policy {ref}")
            for ref in (c.related_risks or []):
                if ref and ref not in all_ids:
                    errors.append(f"Control {c.component_id} references missing risk {ref}")

        if errors:
            logger.warning(
                "grc_extractor_cross_reference_errors",
                error_count=len(errors),
                sample_errors=errors[:5],
            )

        return errors

    def _build_cross_reference_index(
        self, grc: GRCComponentsResponse
    ) -> dict[str, list[str]]:
        """Build index mapping component_id to related component_ids."""
        index: dict[str, list[str]] = {}

        for p in grc.policies:
            if p.component_id:
                refs = list(set((p.related_controls or []) + (p.related_risks or [])))
                if refs:
                    index[p.component_id] = refs

        for r in grc.risks:
            if r.component_id:
                refs = list(set(
                    (r.related_controls or []) + 
                    (r.mitigation_controls or []) + 
                    (r.related_policies or [])
                ))
                if refs:
                    index[r.component_id] = refs

        for c in grc.controls:
            if c.component_id:
                refs = list(set((c.related_policies or []) + (c.related_risks or [])))
                if refs:
                    index[c.component_id] = refs

        return index

    def _build_component_index(
        self, grc: GRCComponentsResponse
    ) -> dict[str, str]:
        """Map source_chunk_id → component_id for atomizer linkage."""
        index = {}
        for component in [*grc.policies, *grc.risks, *grc.controls]:
            if component.source_chunk_id and component.component_id:
                index[component.source_chunk_id] = component.component_id
        return index


def grc_component_extractor_agent(state: Phase1State) -> dict:
    """LangGraph node function wrapper."""
    node = GRCComponentExtractorNode()
    return node(state)
