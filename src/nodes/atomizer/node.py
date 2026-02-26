"""Requirement Atomizer Node - Main orchestration for Node 4 in the LangGraph pipeline.

This is a thin orchestration wrapper that coordinates the batch processor,
response parser, and schema repairer to extract requirements from chunks.
"""
from __future__ import annotations

import structlog

from models.chunks import ContentChunk
from models.requirements import (
    ChunkSkipReason,
    ChunkSkipRecord,
    ExtractionMetadata,
    RegulatoryRequirement,
    validate_requirement_attributes,
)
from models.schema_map import SchemaMap
from models.state import Phase1State
from models.control_metadata import enrich_requirement_metadata
from scoring.confidence_scorer import score_requirement
from scoring.verb_replacer import replace_vague_verbs
from nodes.atomizer.batch_processor import BatchProcessor
from nodes.atomizer.prompt_builder import PromptBuilder
from nodes.atomizer.response_parser import ResponseParser
from nodes.atomizer.schema_repair import SchemaRepairer
from config.loader import get_config, get_llm_model, get_confidence_thresholds, get_fragment_pronouns

logger = structlog.get_logger(__name__)

# Load configuration
_config = get_config()
DEFAULT_MODEL = get_llm_model()
BATCH_FAILURE_THRESHOLD = _config.get("atomizer.failure_handling.batch_failure_threshold", 0.50)
CONFIDENCE_THRESHOLD_PASS1 = get_confidence_thresholds(iteration=1)
CONFIDENCE_THRESHOLD_PASS2 = get_confidence_thresholds(iteration=2)
FRAGMENT_PRONOUNS = tuple(get_fragment_pronouns())


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
        self.batch_processor = BatchProcessor(model_name)
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        self.schema_repairer = SchemaRepairer()

    def __call__(self, state: Phase1State) -> dict:
        """LangGraph node entrypoint. Returns partial state update."""
        chunks = state.get("chunks", [])
        schema_map = state.get("schema_map")
        extraction_iteration = state.get("extraction_iteration", 1)
        component_index = state.get("component_index") or {}

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
        prompt_config = self.prompt_builder.load_prompt(prompt_version)
        if not prompt_config:
            logger.error("atomizer_prompt_load_failed", version=prompt_version)
            return self._empty_result(extraction_iteration, f"Failed to load prompt {prompt_version}")

        # Build batches
        batches = self.batch_processor.build_batches(chunks)
        logger.info("atomizer_batches_created", batch_count=len(batches))

        # Process batches
        all_requirements: list[RegulatoryRequirement] = []
        chunks_with_zero: list[str] = []
        skipped_chunks: list[ChunkSkipRecord] = []
        total_llm_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        failed_batches = 0

        for batch_idx, batch in enumerate(batches):
            try:
                batch_reqs, input_tokens, output_tokens, skip_reason = self.batch_processor.process_batch(
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
                        skipped_chunks.append(ChunkSkipRecord(
                            chunk_id=chunk.chunk_id,
                            skip_reason=skip_reason or ChunkSkipReason.NO_EXTRACTABLE_CONTENT,
                            detail=f"Batch {batch_idx}: no requirements extracted",
                        ))
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
                    skipped_chunks.append(ChunkSkipRecord(
                        chunk_id=chunk.chunk_id,
                        skip_reason=ChunkSkipReason.LLM_ERROR,
                        detail=str(e)[:200],
                    ))

        # Check failure threshold
        if len(batches) > 0 and failed_batches / len(batches) > BATCH_FAILURE_THRESHOLD:
            raise AtomizerFailure(
                f"Too many batch failures: {failed_batches}/{len(batches)}"
            )

        # Deduplicate requirements
        all_requirements = self.response_parser.deduplicate_requirements(all_requirements)

        # Link requirements to parent GRC components
        for req in all_requirements:
            source_chunk_id = req.metadata.source_chunk_id
            parent_id = component_index.get(source_chunk_id)
            if parent_id:
                req.parent_component_id = parent_id

        # Validate attributes and adjust confidence
        validated_requirements, inference_rejected = self._validate_and_adjust(
            all_requirements, extraction_iteration
        )

        # Build extraction metadata
        extraction_metadata = self._build_metadata(
            requirements=validated_requirements,
            chunks_with_zero=chunks_with_zero,
            skipped_chunks=skipped_chunks,
            total_chunks=len(chunks),
            extraction_iteration=extraction_iteration,
            prompt_version=prompt_version,
            total_llm_calls=total_llm_calls,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            inference_rejected_count=len(inference_rejected),
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

    def _validate_and_adjust(
        self, requirements: list[RegulatoryRequirement], extraction_iteration: int = 1
    ) -> tuple[list[RegulatoryRequirement], list[RegulatoryRequirement]]:
        """Validate attributes and compute feature-based confidence scores.
        
        Returns:
            Tuple of (validated_requirements, inference_rejected_requirements)
        """
        validated: list[RegulatoryRequirement] = []
        inference_rejected: list[RegulatoryRequirement] = []
        
        # Determine confidence threshold based on extraction iteration
        min_threshold = CONFIDENCE_THRESHOLD_PASS2 if extraction_iteration == 2 else CONFIDENCE_THRESHOLD_PASS1

        for req in requirements:
            # Post-extraction schema validation with auto-repair
            is_valid, missing = validate_requirement_attributes(req)
            repair_applied = False
            
            if not is_valid:
                # Attempt auto-repair for common issues
                req, repair_applied = self.schema_repairer.attempt_repair(req, missing)
                
                # Re-validate after repair
                is_valid, missing = validate_requirement_attributes(req)
                
                if not is_valid:
                    logger.warning(
                        "atomizer_schema_validation_rejected",
                        requirement_id=req.requirement_id,
                        missing_fields=missing,
                        repair_attempted=repair_applied,
                    )
                    req.attributes["_schema_validation"] = {
                        "status": "rejected",
                        "missing_fields": missing,
                        "repair_attempted": repair_applied,
                    }
                else:
                    req.attributes["_schema_validation"] = {
                        "status": "repaired",
                        "repaired_fields": missing,
                    }
                    logger.info(
                        "atomizer_schema_validation_repaired",
                        requirement_id=req.requirement_id,
                    )
            else:
                req.attributes["_schema_validation"] = {"status": "valid"}

            # Compute feature-based confidence score
            confidence_result = score_requirement(req)
            req.confidence = confidence_result.score
            
            # Store confidence metadata
            req.attributes["_confidence_features"] = confidence_result.features.to_dict()
            req.attributes["_confidence_rationale"] = confidence_result.rationale
            req.attributes["_grounding_classification"] = confidence_result.grounding_classification
            req.attributes["_grounding_evidence"] = confidence_result.grounding_evidence

            # CHANGE 1: Hard-reject INFERENCE grounded requirements
            if confidence_result.grounding_classification == "INFERENCE":
                logger.warning(
                    "atomizer_inference_rejected",
                    requirement_id=req.requirement_id,
                    rule_description=req.rule_description[:100],
                )
                inference_rejected.append(req)
                continue

            # CHANGE 3: Enforce confidence threshold gate
            if req.confidence < min_threshold:
                logger.info(
                    "atomizer_confidence_below_threshold",
                    requirement_id=req.requirement_id,
                    confidence=req.confidence,
                    threshold=min_threshold,
                    iteration=extraction_iteration,
                )
                continue

            # Issue 4: Detect fragments (requirements starting with demonstrative pronouns)
            # These indicate missing context from previous chunk
            desc_lower = req.rule_description.lower()
            if any(desc_lower.startswith(pronoun) for pronoun in FRAGMENT_PRONOUNS):
                logger.warning(
                    "atomizer_fragment_detected",
                    requirement_id=req.requirement_id,
                    rule_description=req.rule_description[:100],
                    reason="starts_with_demonstrative_pronoun",
                )
                req.attributes["_fragment_warning"] = True
                req.attributes["_fragment_reason"] = "starts_with_demonstrative_pronoun"

            # Replace vague verbs
            verb_result = replace_vague_verbs(req.rule_description, req.attributes)
            if verb_result.has_vague_verbs:
                req.attributes["_original_description"] = req.rule_description
                req.attributes["_verb_replacements"] = verb_result.replacements_made
                req.attributes["_actionable_description"] = verb_result.replaced

            # Enrich with control metadata
            control_metadata = enrich_requirement_metadata(
                rule_type=req.rule_type.value,
                rule_description=req.rule_description,
                attributes=req.attributes,
            )
            req.attributes["_control_metadata"] = control_metadata.to_dict()

            logger.debug(
                "atomizer_confidence_scored",
                requirement_id=req.requirement_id,
                confidence=confidence_result.score,
                grounding_classification=confidence_result.grounding_classification,
            )

            validated.append(req)

        return validated, inference_rejected

    def _build_metadata(
        self,
        requirements: list[RegulatoryRequirement],
        chunks_with_zero: list[str],
        skipped_chunks: list[ChunkSkipRecord],
        total_chunks: int,
        extraction_iteration: int,
        prompt_version: str,
        total_llm_calls: int,
        total_input_tokens: int,
        total_output_tokens: int,
        inference_rejected_count: int = 0,
    ) -> ExtractionMetadata:
        """Build extraction metadata from results."""
        avg_confidence = 0.0
        if requirements:
            avg_confidence = sum(r.confidence for r in requirements) / len(requirements)

        distribution: dict[str, int] = {}
        for req in requirements:
            rule_type = req.rule_type.value
            distribution[rule_type] = distribution.get(rule_type, 0) + 1

        return ExtractionMetadata(
            total_chunks_processed=total_chunks,
            total_requirements_extracted=len(requirements),
            chunks_with_zero_extractions=list(set(chunks_with_zero)),
            skipped_chunks=skipped_chunks,
            avg_confidence=avg_confidence,
            rule_type_distribution=distribution,
            extraction_iteration=extraction_iteration,
            prompt_version=prompt_version,
            model_used=self.model_name,
            total_llm_calls=total_llm_calls,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            inference_rejected_count=inference_rejected_count,
        )


def requirement_atomizer_agent(state: Phase1State) -> dict:
    """LangGraph node function wrapper."""
    node = RequirementAtomizerNode()
    return node(state)
