"""Requirement Atomizer Agent - Node 4 in the LangGraph pipeline."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, ValidationError

from agent1.models.chunks import ContentChunk
from agent1.models.requirements import (
    ExtractionMetadata,
    RegulatoryRequirement,
    RuleMetadata,
    RuleType,
    RULE_TYPE_CODES,
    validate_requirement_attributes,
)
from agent1.models.schema_map import SchemaMap
from agent1.models.state import Phase1State

logger = structlog.get_logger(__name__)

# Configuration constants
MAX_BATCH_CHARS = 12000  # Target 80% of context window
MAX_RETRIES_PER_BATCH = 3
RETRY_BACKOFF_BASE = 2.0
BATCH_FAILURE_THRESHOLD = 0.50  # Fail if >50% of batches fail
DEFAULT_MODEL = "claude-sonnet-4-20250514"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "requirement_atomizer"


class AtomizerFailure(Exception):
    """Raised when atomizer fails catastrophically."""
    pass


class RequirementAtomizerNode:
    """
    LangGraph node that extracts RegulatoryRequirement[] from ContentChunk[]
    using a resolved SchemaMap for field guidance.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._prompts_cache: dict[str, dict] = {}

    def __call__(self, state: Phase1State) -> dict:
        """LangGraph node entrypoint. Returns partial state update."""
        chunks = state.get("chunks", [])
        schema_map = state.get("schema_map")
        extraction_iteration = state.get("extraction_iteration", 1)

        if not chunks:
            logger.warning("atomizer_no_chunks")
            return self._empty_result(extraction_iteration, "No chunks provided")

        if not schema_map:
            logger.error("atomizer_no_schema_map")
            return self._empty_result(extraction_iteration, "No schema map provided")

        logger.info(
            "atomizer_started",
            total_chunks=len(chunks),
            extraction_iteration=extraction_iteration,
        )

        # Load appropriate prompt
        prompt_version = "v1.0_retry" if extraction_iteration == 2 else "v1.0"
        prompt_config = self._load_prompt(prompt_version)
        if not prompt_config:
            logger.error("atomizer_prompt_load_failed", version=prompt_version)
            return self._empty_result(extraction_iteration, f"Failed to load prompt {prompt_version}")

        # Build batches
        batches = self._build_batches(chunks)
        logger.info("atomizer_batches_created", batch_count=len(batches))

        # Process batches
        all_requirements: list[RegulatoryRequirement] = []
        chunks_with_zero: list[str] = []
        total_llm_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        failed_batches = 0

        for batch_idx, batch in enumerate(batches):
            try:
                batch_reqs, input_tokens, output_tokens = self._process_batch(
                    batch=batch,
                    schema_map=schema_map,
                    prompt_config=prompt_config,
                    prompt_version=prompt_version,
                    extraction_iteration=extraction_iteration,
                )
                total_llm_calls += 1
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                if not batch_reqs:
                    for chunk in batch:
                        chunks_with_zero.append(chunk.chunk_id)
                else:
                    all_requirements.extend(batch_reqs)

                logger.info(
                    "atomizer_batch_completed",
                    batch_idx=batch_idx,
                    requirements_extracted=len(batch_reqs),
                )

            except Exception as e:
                failed_batches += 1
                logger.error(
                    "atomizer_batch_failed",
                    batch_idx=batch_idx,
                    error=str(e),
                )
                for chunk in batch:
                    chunks_with_zero.append(chunk.chunk_id)

        # Check failure threshold
        if len(batches) > 0 and failed_batches / len(batches) > BATCH_FAILURE_THRESHOLD:
            raise AtomizerFailure(
                f"Too many batch failures: {failed_batches}/{len(batches)}"
            )

        # Deduplicate requirements
        all_requirements = self._deduplicate_requirements(all_requirements)

        # Validate attributes and adjust confidence
        validated_requirements = self._validate_and_adjust(all_requirements)

        # Build extraction metadata
        extraction_metadata = self._build_metadata(
            requirements=validated_requirements,
            chunks_with_zero=chunks_with_zero,
            total_chunks=len(chunks),
            extraction_iteration=extraction_iteration,
            prompt_version=prompt_version,
            total_llm_calls=total_llm_calls,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
        )

        logger.info(
            "atomizer_completed",
            total_requirements=len(validated_requirements),
            avg_confidence=extraction_metadata.avg_confidence,
            rule_type_distribution=extraction_metadata.rule_type_distribution,
        )

        return {
            "requirements": validated_requirements,
            "extraction_metadata": extraction_metadata,
            "prompt_versions": {
                **state.get("prompt_versions", {}),
                "requirement_atomizer": prompt_version,
            },
        }

    def _empty_result(self, extraction_iteration: int, error_msg: str) -> dict:
        """Return empty result with error."""
        return {
            "requirements": [],
            "extraction_metadata": ExtractionMetadata(
                total_chunks_processed=0,
                total_requirements_extracted=0,
                chunks_with_zero_extractions=[],
                avg_confidence=0.0,
                rule_type_distribution={},
                extraction_iteration=extraction_iteration,
                prompt_version="",
                model_used=self.model_name,
                total_llm_calls=0,
                total_input_tokens=0,
                total_output_tokens=0,
            ),
            "errors": [error_msg],
        }

    def _load_prompt(self, version: str) -> dict | None:
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

    def _build_batches(self, chunks: list[ContentChunk]) -> list[list[ContentChunk]]:
        """
        Group chunks into batches that fit within context window.
        Includes overlap for deduplication continuity.
        """
        batches: list[list[ContentChunk]] = []
        current_batch: list[ContentChunk] = []
        current_chars = 0

        # Group by entity type when possible
        entity_chunks: dict[str, list[ContentChunk]] = {}
        other_chunks: list[ContentChunk] = []

        for chunk in chunks:
            entity_type = chunk.annotations.get("record_type")
            if entity_type:
                entity_chunks.setdefault(entity_type, []).append(chunk)
            else:
                other_chunks.append(chunk)

        # Process entity-grouped chunks first
        all_ordered: list[ContentChunk] = []
        for entity_type in sorted(entity_chunks.keys()):
            all_ordered.extend(entity_chunks[entity_type])
        all_ordered.extend(other_chunks)

        for chunk in all_ordered:
            chunk_chars = chunk.char_count

            # If single chunk exceeds budget, process alone
            if chunk_chars > MAX_BATCH_CHARS:
                if current_batch:
                    batches.append(current_batch)
                batches.append([chunk])
                current_batch = []
                current_chars = 0
                continue

            # Check if adding this chunk exceeds budget
            if current_chars + chunk_chars > MAX_BATCH_CHARS:
                if current_batch:
                    batches.append(current_batch)
                    # Overlap: include last chunk of previous batch
                    current_batch = [current_batch[-1], chunk]
                    current_chars = current_batch[0].char_count + chunk_chars
                else:
                    current_batch = [chunk]
                    current_chars = chunk_chars
            else:
                current_batch.append(chunk)
                current_chars += chunk_chars

        if current_batch:
            batches.append(current_batch)

        return batches

    def _process_batch(
        self,
        batch: list[ContentChunk],
        schema_map: SchemaMap,
        prompt_config: dict,
        prompt_version: str,
        extraction_iteration: int,
    ) -> tuple[list[RegulatoryRequirement], int, int]:
        """Process a single batch of chunks through the LLM."""
        import httpx
        from anthropic import Anthropic

        # Build schema context
        schema_context = self._build_schema_context(schema_map)

        # Build chunks content
        chunks_content = self._build_chunks_content(batch)

        # Build system prompt
        system_prompt = self._build_system_prompt(prompt_config, schema_context)

        # Build user message
        user_message = prompt_config.get("user_message_template", "").format(
            chunks_content=chunks_content
        )

        # Set temperature based on iteration
        temperature = 0.0 if extraction_iteration == 2 else 0.1

        # Call LLM with retries
        verify_ssl = os.getenv("ANTHROPIC_VERIFY_SSL", "true").lower() != "false"
        if not verify_ssl:
            http_client = httpx.Client(verify=False)
            client = Anthropic(http_client=http_client)
        else:
            client = Anthropic()

        last_error = None
        for attempt in range(MAX_RETRIES_PER_BATCH):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                # Extract token usage
                input_tokens = response.usage.input_tokens if response.usage else 0
                output_tokens = response.usage.output_tokens if response.usage else 0

                # Parse response
                content = response.content[0].text if response.content else "[]"
                requirements = self._parse_llm_response(
                    content=content,
                    batch=batch,
                    schema_version=schema_map.schema_version,
                    prompt_version=prompt_version,
                    extraction_iteration=extraction_iteration,
                )

                return requirements, input_tokens, output_tokens

            except Exception as e:
                last_error = e
                logger.warning(
                    "atomizer_llm_retry",
                    attempt=attempt,
                    error=str(e),
                )
                time.sleep(RETRY_BACKOFF_BASE ** attempt)

        raise last_error or RuntimeError("LLM call failed")

    def _build_schema_context(self, schema_map: SchemaMap) -> str:
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

    def _build_chunks_content(self, batch: list[ContentChunk]) -> str:
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

    def _build_system_prompt(self, prompt_config: dict, schema_context: str) -> str:
        """Build the full system prompt."""
        role = prompt_config.get("role", "")
        instructions = prompt_config.get("instructions", "")

        # Replace schema placeholder
        instructions = instructions.replace("{schema_map_context}", schema_context)

        return f"{role}\n\n{instructions}"

    def _parse_llm_response(
        self,
        content: str,
        batch: list[ContentChunk],
        schema_version: str,
        prompt_version: str,
        extraction_iteration: int,
    ) -> list[RegulatoryRequirement]:
        """Parse LLM response into RegulatoryRequirement objects."""
        requirements: list[RegulatoryRequirement] = []

        # Clean content (remove markdown if present)
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("atomizer_json_parse_error", error=str(e))
            return []

        if not isinstance(data, list):
            data = [data]

        # Map chunk IDs for metadata
        chunk_id_map = {chunk.chunk_id: chunk for chunk in batch}
        default_chunk = batch[0] if batch else None

        for item in data:
            try:
                # Validate rule_type
                rule_type_str = item.get("rule_type", "")
                try:
                    rule_type = RuleType(rule_type_str)
                except ValueError:
                    logger.warning(
                        "atomizer_invalid_rule_type",
                        rule_type=rule_type_str,
                    )
                    continue

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
                requirement = RegulatoryRequirement(
                    requirement_id=requirement_id,
                    rule_type=rule_type,
                    rule_description=rule_description,
                    grounded_in=grounded_in,
                    confidence=item.get("confidence", 0.70),
                    attributes=item.get("attributes", {}),
                    metadata=metadata,
                )

                requirements.append(requirement)

            except ValidationError as e:
                logger.warning(
                    "atomizer_requirement_validation_error",
                    error=str(e),
                )
                continue

        return requirements

    def _deduplicate_requirements(
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

    def _validate_and_adjust(
        self, requirements: list[RegulatoryRequirement]
    ) -> list[RegulatoryRequirement]:
        """Validate attributes and adjust confidence for invalid ones."""
        validated: list[RegulatoryRequirement] = []

        for req in requirements:
            is_valid, missing = validate_requirement_attributes(req)

            if not is_valid:
                logger.warning(
                    "atomizer_attribute_validation_failed",
                    requirement_id=req.requirement_id,
                    missing_fields=missing,
                )
                # Cap confidence at 0.60 for invalid attributes
                req.confidence = min(req.confidence, 0.60)

            validated.append(req)

        return validated

    def _build_metadata(
        self,
        requirements: list[RegulatoryRequirement],
        chunks_with_zero: list[str],
        total_chunks: int,
        extraction_iteration: int,
        prompt_version: str,
        total_llm_calls: int,
        total_input_tokens: int,
        total_output_tokens: int,
    ) -> ExtractionMetadata:
        """Build extraction metadata from results."""
        # Calculate average confidence
        avg_confidence = 0.0
        if requirements:
            avg_confidence = sum(r.confidence for r in requirements) / len(requirements)

        # Build rule type distribution
        distribution: dict[str, int] = {}
        for req in requirements:
            rule_type = req.rule_type.value
            distribution[rule_type] = distribution.get(rule_type, 0) + 1

        return ExtractionMetadata(
            total_chunks_processed=total_chunks,
            total_requirements_extracted=len(requirements),
            chunks_with_zero_extractions=list(set(chunks_with_zero)),
            avg_confidence=avg_confidence,
            rule_type_distribution=distribution,
            extraction_iteration=extraction_iteration,
            prompt_version=prompt_version,
            model_used=self.model_name,
            total_llm_calls=total_llm_calls,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
        )


def requirement_atomizer_agent(state: Phase1State) -> dict:
    """LangGraph node function wrapper."""
    node = RequirementAtomizerNode()
    return node(state)
