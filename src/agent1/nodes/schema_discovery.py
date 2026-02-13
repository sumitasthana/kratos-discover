from __future__ import annotations

import hashlib
import structlog
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

from agent1.models.chunks import ContentChunk
from agent1.models.schema_map import SchemaMap
from agent1.models.state import Phase1State
from agent1.cache.schema_cache import get_cached_schema, cache_schema

logger = structlog.get_logger(__name__)

MAX_CHUNKS_FOR_DISCOVERY = 10
MAX_RETRIES = 3


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


def build_discovery_prompt(chunks: list[ContentChunk]) -> str:
    """Build the prompt from chunks."""
    chunks_text = "\n\n".join(
        f"[{chunk.chunk_type.upper()}] {chunk.content_text[:500]}"
        for chunk in chunks
    )
    return f"""Analyze these document chunks and infer the schema structure:

{chunks_text}

Return a JSON object with the SchemaMap structure."""


def call_claude_structured(prompt: str, output_model: type[BaseModel]) -> BaseModel:
    """Call Claude with structured output."""
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=4096,
    )
    structured_llm = llm.with_structured_output(output_model)

    for attempt in range(MAX_RETRIES):
        try:
            result = structured_llm.invoke(prompt)
            return result
        except Exception as e:
            logger.warning("claude_call_failed", attempt=attempt, error=str(e))
            if attempt == MAX_RETRIES - 1:
                raise
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

    # Take first N chunks
    sample_chunks = chunks[:MAX_CHUNKS_FOR_DISCOVERY]

    # Check cache first
    doc_format = state.get("file_path", "unknown").split(".")[-1].lower()
    cached = get_cached_schema(doc_format)
    if cached:
        logger.info("schema_discovery_cache_hit", document_format=doc_format)
        return {
            "schema_map": cached,
            "prompt_versions": {
                **state.get("prompt_versions", {}),
                "schema_discovery": "v1_cached",
            },
        }

    # Build prompt and call Claude
    prompt = build_discovery_prompt(sample_chunks)
    schema_map = call_claude_structured(prompt, SchemaMap)

    # Compute derived fields
    schema_map.schema_version = compute_schema_hash(schema_map)
    schema_map.avg_confidence = compute_avg_confidence(schema_map)

    # Cache result
    cache_schema(doc_format, schema_map)

    logger.info(
        "schema_discovery_completed",
        entities=len(schema_map.entities),
        avg_confidence=schema_map.avg_confidence,
        structural_pattern=schema_map.structural_pattern,
    )

    return {
        "schema_map": schema_map,
        "prompt_versions": {
            **state.get("prompt_versions", {}),
            "schema_discovery": "v1",
        },
    }
