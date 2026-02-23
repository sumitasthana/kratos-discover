"""Prompt building utilities for the Requirement Atomizer.

Handles construction of system prompts, schema context, and chunk content
for LLM extraction calls.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from models.chunks import ContentChunk
from models.schema_map import SchemaMap

logger = structlog.get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "requirement_atomizer"


class PromptBuilder:
    """Builds prompts for the atomizer LLM calls."""
    
    def __init__(self):
        self._prompts_cache: dict[str, dict] = {}
    
    def load_prompt(self, version: str) -> dict | None:
        """Load prompt configuration from YAML file."""
        if version in self._prompts_cache:
            return self._prompts_cache[version]

        prompt_file = PROMPTS_DIR / f"{version}.yaml"
        if not prompt_file.exists():
            logger.warning("atomizer_prompt_not_found", path=str(prompt_file))
            return None

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            self._prompts_cache[version] = config
            return config
        except Exception as e:
            logger.error("atomizer_prompt_parse_error", error=str(e))
            return None

    def build_schema_context(self, schema_map: SchemaMap) -> str:
        """Build schema context string for the prompt."""
        lines = ["Document Schema:"]
        lines.append(f"  Format: {schema_map.document_format}")
        lines.append(f"  Pattern: {schema_map.structural_pattern}")
        lines.append(f"  Category: {schema_map.inferred_document_category}")
        lines.append("")
        lines.append("Entities:")

        for entity in schema_map.entities:
            lines.append(f"  - {entity.discovered_label} ({entity.record_count} records)")
            lines.append("    Fields:")
            for field in entity.fields:
                lines.append(
                    f"      - {field.raw_label} ({field.inferred_type})"
                )

        return "\n".join(lines)

    def build_chunks_content(self, batch: list[ContentChunk]) -> str:
        """Build chunks content string for the prompt."""
        parts = []
        for chunk in batch:
            ann = chunk.annotations
            entity_info = ""
            if ann.get("record_type"):
                entity_info = f" [ENTITY: {ann.get('record_type').upper()}]"
                if ann.get("record_id"):
                    entity_info += f" [ID: {ann.get('record_id')}]"

            parts.append(
                f"--- CHUNK {chunk.chunk_id} [{chunk.chunk_type.upper()}]{entity_info} ---\n"
                f"Location: {chunk.source_location}\n"
                f"Parent: {chunk.parent_heading or 'None'}\n\n"
                f"{chunk.content_text}\n"
            )

        return "\n".join(parts)

    def build_system_prompt(self, prompt_config: dict, schema_context: str) -> str:
        """Build the full system prompt."""
        role = prompt_config.get("role", "")
        instructions = prompt_config.get("instructions", "")

        # Replace schema placeholder
        instructions = instructions.replace("{schema_map_context}", schema_context)

        return f"{role}\n\n{instructions}"

    def build_user_message(self, prompt_config: dict, chunks_content: str) -> str:
        """Build the user message from template."""
        return prompt_config.get("user_message_template", "").format(
            chunks_content=chunks_content
        )
