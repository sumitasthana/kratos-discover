"""Response parsing utilities for the Requirement Atomizer.

Handles JSON parsing, requirement construction, and deduplication
of LLM extraction responses.
"""
from __future__ import annotations

import json
import re
from typing import Any

import structlog
from pydantic import ValidationError

from models.chunks import ContentChunk
from models.requirements import RegulatoryRequirement, RuleMetadata
from models.shared import RuleType
from utils.error_handler import handle_anthropic_error
from config.loader import get_deduplication_threshold

logger = structlog.get_logger(__name__)

# Load configuration
JACCARD_SIMILARITY_THRESHOLD = get_deduplication_threshold()

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
        """Deduplicate requirements, keeping higher confidence version.
        
        Uses Jaccard similarity on tokenized descriptions to catch semantic near-duplicates.
        Threshold of 0.85 catches variations like:
        - "The hold must be aggregated across all accounts"
        - "Aggregate the hold across all accounts"
        while preserving distinct requirements.
        """
        seen: dict[int, RegulatoryRequirement] = {}
        processed_indices: set[int] = set()

        def _tokenize(text: str) -> set[str]:
            """Tokenize description into words, removing stop words."""
            # Remove punctuation and split into words
            words = re.findall(r'\b\w+\b', text.lower())
            # Remove common stop words that don't add semantic meaning
            stop_words = {'a', 'an', 'the', 'is', 'are', 'be', 'been', 'being', 'have', 'has', 'had',
                         'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                         'must', 'can', 'and', 'or', 'but', 'if', 'in', 'on', 'at', 'to', 'for',
                         'of', 'with', 'by', 'from', 'as', 'that', 'this', 'which', 'who', 'what'}
            return set(w for w in words if w not in stop_words)

        def _jaccard_similarity(desc1: str, desc2: str) -> float:
            """Compute Jaccard similarity between two descriptions."""
            tokens1 = _tokenize(desc1)
            tokens2 = _tokenize(desc2)
            if not tokens1 or not tokens2:
                return 0.0
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            return intersection / union if union > 0 else 0.0

        for i, req in enumerate(requirements):
            if i in processed_indices:
                continue

            similar_group = [i]
            
            for j in range(i + 1, len(requirements)):
                if j in processed_indices:
                    continue
                
                other = requirements[j]
                if req.rule_type != other.rule_type:
                    continue
                
                # Issue 2: Use Jaccard similarity for semantic near-duplicate detection
                similarity = _jaccard_similarity(req.rule_description, other.rule_description)
                
                # Issue 2: Threshold of 0.75 catches AC-03 style near-duplicates
                # ("must be populated from Pending File" vs "must produce this table by reading from Pending File")
                # while preserving distinct requirements
                if similarity >= 0.75:
                    similar_group.append(j)

            # Keep highest confidence from similar group
            best_idx = max(similar_group, key=lambda idx: requirements[idx].confidence)
            seen[best_idx] = requirements[best_idx]
            processed_indices.update(similar_group)

        return [seen[idx] for idx in sorted(seen.keys())]
