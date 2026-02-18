"""Response parsing utilities for the Requirement Atomizer.

Handles JSON parsing, requirement construction, and deduplication
of LLM extraction responses.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import ValidationError

from agent1.models.chunks import ContentChunk
from agent1.models.requirements import (
    RegulatoryRequirement,
    RuleMetadata,
    RuleType,
)

logger = structlog.get_logger(__name__)


class ResponseParser:
    """Parses LLM responses into RegulatoryRequirement objects."""

    def parse_response(
        self,
        content: str,
        batch: list[ContentChunk],
        schema_version: str,
        prompt_version: str,
        extraction_iteration: int,
    ) -> list[RegulatoryRequirement]:
        """Parse LLM response into RegulatoryRequirement objects."""
        requirements, _ = self.parse_response_with_status(
            content, batch, schema_version, prompt_version, extraction_iteration
        )
        return requirements

    def parse_response_with_status(
        self,
        content: str,
        batch: list[ContentChunk],
        schema_version: str,
        prompt_version: str,
        extraction_iteration: int,
    ) -> tuple[list[RegulatoryRequirement], bool]:
        """Parse LLM response with parse error status.
        
        Returns: (requirements, had_parse_error)
        """
        requirements: list[RegulatoryRequirement] = []
        had_parse_error = False

        # Clean content (remove markdown if present)
        content = self._clean_content(content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("atomizer_json_parse_error", error=str(e))
            return [], True  # Parse error

        if not isinstance(data, list):
            data = [data]

        # Map chunk IDs for metadata
        chunk_id_map = {chunk.chunk_id: chunk for chunk in batch}
        default_chunk = batch[0] if batch else None

        for item in data:
            try:
                requirement = self._parse_item(
                    item=item,
                    chunk_id_map=chunk_id_map,
                    default_chunk=default_chunk,
                    schema_version=schema_version,
                    prompt_version=prompt_version,
                    extraction_iteration=extraction_iteration,
                )
                if requirement:
                    requirements.append(requirement)
            except ValidationError as e:
                logger.warning("atomizer_requirement_validation_error", error=str(e))
                had_parse_error = True
                continue

        return requirements, had_parse_error

    def _clean_content(self, content: str) -> str:
        """Clean LLM response content (remove markdown fences)."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        return content

    def _parse_item(
        self,
        item: dict[str, Any],
        chunk_id_map: dict[str, ContentChunk],
        default_chunk: ContentChunk | None,
        schema_version: str,
        prompt_version: str,
        extraction_iteration: int,
    ) -> RegulatoryRequirement | None:
        """Parse a single item from the LLM response."""
        # Validate rule_type
        rule_type_str = item.get("rule_type", "")
        try:
            rule_type = RuleType(rule_type_str)
        except ValueError:
            logger.warning("atomizer_invalid_rule_type", rule_type=rule_type_str)
            return None

        # Get source chunk
        source_chunk_id = item.get("source_chunk_id", "")
        source_chunk = chunk_id_map.get(source_chunk_id, default_chunk)

        # Generate requirement ID
        rule_description = item.get("rule_description", "")
        grounded_in = item.get("grounded_in", "")
        requirement_id = RegulatoryRequirement.generate_requirement_id(
            rule_type=rule_type,
            rule_description=rule_description,
            grounded_in=grounded_in,
        )

        # Build metadata
        metadata = RuleMetadata(
            source_chunk_id=source_chunk.chunk_id if source_chunk else "",
            source_location=source_chunk.source_location if source_chunk else "",
            schema_version=schema_version,
            prompt_version=prompt_version,
            extraction_iteration=extraction_iteration,
        )

        # Create requirement
        return RegulatoryRequirement(
            requirement_id=requirement_id,
            rule_type=rule_type,
            rule_description=rule_description,
            grounded_in=grounded_in,
            confidence=item.get("confidence", 0.70),
            attributes=item.get("attributes", {}),
            metadata=metadata,
        )

    def deduplicate_requirements(
        self, requirements: list[RegulatoryRequirement]
    ) -> list[RegulatoryRequirement]:
        """Deduplicate requirements, keeping higher confidence version."""
        seen: dict[str, RegulatoryRequirement] = {}

        for req in requirements:
            # Normalize key: rule_type + lowercase stripped description
            key = f"{req.rule_type.value}|{req.rule_description.lower().strip()}"

            if key not in seen:
                seen[key] = req
            elif req.confidence > seen[key].confidence:
                seen[key] = req

        return list(seen.values())
