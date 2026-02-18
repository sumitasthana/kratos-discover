"""Eval node for quality assessment of extracted requirements.

Runs after Atomizer and before Router to compute quality metrics,
detect failure patterns, and signal Router decision.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from agent1.eval.models import (
    EvalReport,
    TestabilityIssue,
    GroundingIssue,
    HallucinationFlag,
    SchemaComplianceIssue,
    PotentialDuplicate,
)
from agent1.eval.checks.coverage import analyze_coverage
from agent1.eval.checks.testability import check_testability
from agent1.eval.checks.grounding import check_grounding
from agent1.eval.checks.hallucination import check_hallucination
from agent1.eval.checks.deduplication import check_deduplication
from agent1.eval.checks.schema_compliance import check_schema_compliance
from agent1.eval.classifier import (
    classify_failure,
    generate_suggestions,
    compute_overall_quality_score,
)
from agent1.models.state import Phase1State

logger = structlog.get_logger(__name__)


def _compute_confidence_distribution(requirements: list) -> dict[str, int]:
    """Compute confidence score distribution by tier."""
    distribution = {
        "0.90-0.99": 0,
        "0.80-0.89": 0,
        "0.70-0.79": 0,
        "0.60-0.69": 0,
        "0.50-0.59": 0,
    }
    
    for req in requirements:
        conf = req.confidence
        if conf >= 0.90:
            distribution["0.90-0.99"] += 1
        elif conf >= 0.80:
            distribution["0.80-0.89"] += 1
        elif conf >= 0.70:
            distribution["0.70-0.79"] += 1
        elif conf >= 0.60:
            distribution["0.60-0.69"] += 1
        else:
            distribution["0.50-0.59"] += 1
    
    return distribution


def _compute_requirements_by_type(requirements: list) -> dict[str, int]:
    """Count requirements by rule type."""
    by_type: dict[str, int] = {}
    for req in requirements:
        rule_type = req.rule_type.value
        by_type[rule_type] = by_type.get(rule_type, 0) + 1
    return by_type


def _validate_enrichments(requirements: list) -> list[dict]:
    """CF-14: Self-validation pass for Eval enrichments.
    
    Validates that enrichments added by Eval/Atomizer are internally consistent:
    - Confidence score integrity (score matches features sum within tolerance)
    - Template error detection (doubled words, empty placeholders)
    - Enrichment grounding checks (system mappings have keywords if inferred)
    """
    issues: list[dict] = []
    
    for req in requirements:
        attrs = req.attributes if hasattr(req, "attributes") else {}
        req_id = req.requirement_id if hasattr(req, "requirement_id") else "unknown"
        
        # 1. Confidence score integrity check
        features = attrs.get("_confidence_features", {})
        if features:
            raw_total = features.get("raw_total", 0)
            declared_conf = req.confidence if hasattr(req, "confidence") else 0
            # Allow for floor/ceiling transform (0.50-0.99 range)
            expected_clamped = min(0.99, max(0.50, raw_total))
            if abs(declared_conf - expected_clamped) > 0.05:
                issues.append({
                    "req_id": req_id,
                    "issue_type": "confidence_integrity",
                    "detail": f"Declared {declared_conf:.2f} vs expected {expected_clamped:.2f} (raw={raw_total:.3f})",
                })
        
        # 2. Template error detection (doubled words)
        import re
        doubled_pattern = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
        
        # Check control_objective
        control_obj = attrs.get("control_metadata", {}).get("control_objective", "")
        if control_obj and doubled_pattern.search(control_obj):
            issues.append({
                "req_id": req_id,
                "issue_type": "template_error",
                "detail": f"Doubled word in control_objective: {doubled_pattern.search(control_obj).group()}",
            })
        
        # Check test_procedure
        test_proc = attrs.get("control_metadata", {}).get("test_procedure", "")
        if test_proc and "{" in test_proc and "}" in test_proc:
            # Unfilled placeholder
            issues.append({
                "req_id": req_id,
                "issue_type": "template_error",
                "detail": "Unfilled placeholder in test_procedure",
            })
        
        # 3. Enrichment grounding check
        ctrl_meta = attrs.get("control_metadata", {})
        sys_source = ctrl_meta.get("system_mapping_source", "")
        sys_keywords = ctrl_meta.get("system_mapping_keywords", [])
        
        if sys_source == "keyword_inferred" and not sys_keywords:
            issues.append({
                "req_id": req_id,
                "issue_type": "enrichment_grounding",
                "detail": "system_mapping_source=keyword_inferred but no keywords recorded",
            })
        
        # Check evidence_type_source
        ev_source = ctrl_meta.get("evidence_type_source", "")
        if ev_source == "extracted":
            # Should have grounding evidence - but we don't extract yet, so flag
            issues.append({
                "req_id": req_id,
                "issue_type": "enrichment_grounding",
                "detail": "evidence_type_source=extracted but extraction not implemented",
            })
    
    return issues


def _compute_schema_coverage(requirements: list, schema_map: Any) -> dict[str, int]:
    """Compute how many requirements reference each schema entity."""
    coverage: dict[str, int] = {}
    
    if not schema_map or not hasattr(schema_map, "entities"):
        return coverage
    
    for entity in schema_map.entities:
        # DiscoveredEntity uses discovered_label, not name
        entity_name = getattr(entity, "discovered_label", getattr(entity, "name", "unknown"))
        entity_name_lower = entity_name.lower()
        count = 0
        for req in requirements:
            # Check if entity name appears in attributes or description
            attrs_str = str(req.attributes).lower()
            desc_str = (req.rule_description or "").lower()
            if entity_name_lower in attrs_str or entity_name_lower in desc_str:
                count += 1
        coverage[entity_name] = count
    
    return coverage


def eval_quality(state: Phase1State) -> dict:
    """
    LangGraph node: Evaluate quality of extracted requirements.
    
    Computes quality metrics, detects failure patterns, and prepares
    Router decision signal.
    
    Returns partial state update with eval_report.
    """
    requirements = state.get("requirements", [])
    chunks = state.get("chunks", [])
    schema_map = state.get("schema_map")
    extraction_metadata = state.get("extraction_metadata")
    extraction_iteration = state.get("extraction_iteration", 1)
    prompt_versions = state.get("prompt_versions", {})
    
    logger.info(
        "eval_started",
        total_requirements=len(requirements),
        total_chunks=len(chunks),
        extraction_iteration=extraction_iteration,
    )
    
    # 1. Coverage analysis
    total_chunks, chunks_processed, chunks_with_zero, coverage_ratio = analyze_coverage(
        chunks, requirements
    )
    
    # CF-2: Reconcile with extraction_metadata if available
    # Use extraction_metadata as source of truth for skipped chunks
    if extraction_metadata:
        meta_zero = getattr(extraction_metadata, "chunks_with_zero_extractions", [])
        if hasattr(extraction_metadata, "chunks_with_zero_extractions"):
            meta_zero = extraction_metadata.chunks_with_zero_extractions
        elif isinstance(extraction_metadata, dict):
            meta_zero = extraction_metadata.get("chunks_with_zero_extractions", [])
        
        # Merge: use extraction_metadata's list if it has more entries
        if len(meta_zero) > len(chunks_with_zero):
            chunks_with_zero = list(meta_zero)
            # Recalculate coverage ratio
            if total_chunks > 0:
                coverage_ratio = 1.0 - (len(chunks_with_zero) / total_chunks)
    
    # 2. Testability check
    testability_issues: list[TestabilityIssue] = []
    for req in requirements:
        issue = check_testability(req)
        if issue:
            testability_issues.append(issue)
    
    # 3. Grounding check (integrates with confidence scorer)
    grounding_issues: list[GroundingIssue] = []
    for req in requirements:
        issue = check_grounding(req)
        if issue:
            grounding_issues.append(issue)
    
    # 4. Hallucination detection
    hallucination_flags: list[HallucinationFlag] = []
    for req in requirements:
        flag = check_hallucination(req)
        if flag:
            hallucination_flags.append(flag)
    
    # 5. Schema compliance check (integrates with canonical_schemas)
    schema_compliance_issues: list[SchemaComplianceIssue] = []
    for req in requirements:
        issue = check_schema_compliance(req)
        if issue:
            schema_compliance_issues.append(issue)
    
    # 6. Deduplication analysis
    dedup_ratio, potential_duplicates = check_deduplication(requirements)
    
    # 7. CF-14: Self-validation of enrichments
    enrichment_validation_issues = _validate_enrichments(requirements)
    if enrichment_validation_issues:
        logger.warning(
            "eval_enrichment_validation_issues",
            count=len(enrichment_validation_issues),
            issues=enrichment_validation_issues[:5],  # Log first 5
        )
    
    # 8. Compute metrics
    avg_confidence = 0.0
    if requirements:
        avg_confidence = sum(r.confidence for r in requirements) / len(requirements)
    
    confidence_distribution = _compute_confidence_distribution(requirements)
    requirements_by_type = _compute_requirements_by_type(requirements)
    schema_coverage = _compute_schema_coverage(requirements, schema_map)
    
    # 8. Classify failure
    failure_type, failure_severity, is_retryable = classify_failure(
        coverage_ratio=coverage_ratio,
        testability_issues=testability_issues,
        grounding_issues=grounding_issues,
        hallucination_flags=hallucination_flags,
        schema_compliance_issues=schema_compliance_issues,
        dedup_ratio=dedup_ratio,
        extraction_iteration=extraction_iteration,
    )
    
    # 9. Generate suggestions
    suggestions = generate_suggestions(
        failure_type=failure_type,
        coverage_ratio=coverage_ratio,
        dedup_ratio=dedup_ratio,
        testability_issues=testability_issues,
        grounding_issues=grounding_issues,
        schema_compliance_issues=schema_compliance_issues,
        hallucination_flags=hallucination_flags,
    )
    
    # 10. Compute overall quality score
    overall_quality_score = compute_overall_quality_score(
        coverage_ratio=coverage_ratio,
        avg_confidence=avg_confidence,
        dedup_ratio=dedup_ratio,
        testability_issues=testability_issues,
        grounding_issues=grounding_issues,
        schema_compliance_issues=schema_compliance_issues,
        hallucination_flags=hallucination_flags,
        total_requirements=len(requirements),
    )
    
    # Build report
    report = EvalReport(
        total_chunks=total_chunks,
        chunks_processed=chunks_processed,
        chunks_with_zero_extractions=chunks_with_zero,
        coverage_ratio=coverage_ratio,
        total_requirements=len(requirements),
        requirements_by_type=requirements_by_type,
        avg_confidence=avg_confidence,
        confidence_distribution=confidence_distribution,
        testability_issues=testability_issues,
        grounding_issues=grounding_issues,
        hallucination_flags=hallucination_flags,
        schema_compliance_issues=schema_compliance_issues,
        enrichment_validation_issues=enrichment_validation_issues,  # CF-14
        unique_requirement_count=len(requirements) - len(potential_duplicates),
        potential_duplicates=potential_duplicates,
        dedup_ratio=dedup_ratio,
        schema_entities=len(schema_map.entities) if schema_map and hasattr(schema_map, "entities") else 0,
        schema_coverage=schema_coverage,
        failure_type=failure_type,
        failure_severity=failure_severity,
        is_retryable=is_retryable,
        remediation_suggestions=suggestions,
        eval_timestamp=datetime.utcnow().isoformat(),
        extraction_iteration=extraction_iteration,
        prompt_version=prompt_versions.get("requirement_atomizer", "unknown"),
        overall_quality_score=overall_quality_score,
    )
    
    logger.info(
        "eval_completed",
        failure_type=failure_type,
        failure_severity=failure_severity,
        is_retryable=is_retryable,
        coverage_ratio=coverage_ratio,
        avg_confidence=avg_confidence,
        overall_quality_score=overall_quality_score,
        testability_issues=len(testability_issues),
        grounding_issues=len(grounding_issues),
        hallucination_flags=len(hallucination_flags),
        schema_compliance_issues=len(schema_compliance_issues),
        potential_duplicates=len(potential_duplicates),
    )
    
    return {
        "eval_report": report.model_dump(),
    }
