"""Failure classification and remediation suggestions for Eval node."""
from __future__ import annotations

from typing import Any, Literal


def classify_failure(
    coverage_ratio: float,
    testability_issues: list,
    grounding_issues: list,
    hallucination_flags: list,
    schema_compliance_issues: list,
    dedup_ratio: float,
    extraction_iteration: int,
) -> tuple[str, str, bool]:
    """
    Classify failure type and determine if retry is worthwhile.
    
    Returns:
        (failure_type, severity, is_retryable)
        
    failure_type: "none", "coverage", "testability", "grounding", "schema", "dedup", "hallucination", "multi"
    severity: "low", "medium", "high", "critical"
    is_retryable: bool (iteration < 2 AND failure is coverage/dedup)
    """
    failure_type: str = "none"
    severity: str = "low"
    is_retryable = False
    
    failure_counts = {
        "coverage": 0,
        "testability": 0,
        "grounding": 0,
        "schema": 0,
        "dedup": 0,
        "hallucination": 0,
    }
    
    # Coverage issue
    if coverage_ratio < 0.60:
        failure_counts["coverage"] = 1
        severity = "high"
        is_retryable = extraction_iteration < 2
    elif coverage_ratio < 0.80:
        failure_counts["coverage"] = 0.5  # Warning level
    
    # Testability issues
    testability_count = len(testability_issues)
    if testability_count > 5:
        failure_counts["testability"] = 1
        severity = "high"
        # Testability issues are usually prompt problems, retry unlikely to help
        is_retryable = False
    elif testability_count > 2:
        failure_counts["testability"] = 0.5
    
    # Grounding issues
    grounding_count = len(grounding_issues)
    if grounding_count > 3:
        failure_counts["grounding"] = 1
        if severity == "low":
            severity = "medium"
    elif grounding_count > 1:
        failure_counts["grounding"] = 0.5
    
    # Schema compliance issues
    schema_count = len(schema_compliance_issues)
    high_severity_schema = sum(1 for i in schema_compliance_issues if i.severity == "high")
    if high_severity_schema > 3:
        failure_counts["schema"] = 1
        if severity == "low":
            severity = "medium"
    elif schema_count > 5:
        failure_counts["schema"] = 0.5
    
    # Deduplication issues
    if dedup_ratio < 0.70:
        failure_counts["dedup"] = 1
        if severity == "low":
            severity = "medium"
        is_retryable = extraction_iteration < 2
    elif dedup_ratio < 0.85:
        failure_counts["dedup"] = 0.5
    
    # Hallucination flags (most severe)
    hallucination_count = len(hallucination_flags)
    critical_hallucinations = sum(1 for h in hallucination_flags if h.risk == "critical")
    high_hallucinations = sum(1 for h in hallucination_flags if h.risk == "high")
    
    if critical_hallucinations > 0:
        failure_counts["hallucination"] = 1
        severity = "critical"
        is_retryable = False
    elif high_hallucinations > 3:
        failure_counts["hallucination"] = 1
        severity = "high"
        is_retryable = False
    elif hallucination_count > 5:
        failure_counts["hallucination"] = 0.5
    
    # Determine primary failure type
    active_failures = [k for k, v in failure_counts.items() if v >= 1]
    
    if len(active_failures) == 0:
        failure_type = "none"
    elif len(active_failures) == 1:
        failure_type = active_failures[0]
    else:
        failure_type = "multi"
        severity = "high" if severity != "critical" else severity
    
    return failure_type, severity, is_retryable


def generate_suggestions(
    failure_type: str,
    coverage_ratio: float,
    dedup_ratio: float,
    testability_issues: list,
    grounding_issues: list,
    schema_compliance_issues: list,
    hallucination_flags: list,
) -> list[str]:
    """Generate human-readable remediation suggestions."""
    suggestions: list[str] = []
    
    # Coverage suggestions
    if coverage_ratio < 0.60:
        suggestions.append(
            f"Coverage ratio {coverage_ratio:.1%} too low. Retry with broader rule extraction "
            f"(relax confidence threshold or expand rule_type scope)."
        )
    elif coverage_ratio < 0.80:
        suggestions.append(
            f"Coverage ratio {coverage_ratio:.1%} below target. Review chunks with zero extractions."
        )
    
    # Testability suggestions
    if testability_issues:
        suggestions.append(
            f"Testability issues found ({len(testability_issues)}). Review rule descriptions; "
            f"ensure each has measurable pass/fail condition. Require threshold_value for data_quality rules."
        )
    
    # Grounding suggestions
    if grounding_issues:
        suggestions.append(
            f"Grounding issues ({len(grounding_issues)}). Verify grounded_in cites source text; "
            f"ensure confidence scores reflect actual inference level."
        )
    
    # Schema compliance suggestions
    if schema_compliance_issues:
        missing_fields = set()
        for issue in schema_compliance_issues:
            missing_fields.update(issue.missing_fields)
        if missing_fields:
            suggestions.append(
                f"Schema compliance issues ({len(schema_compliance_issues)}). "
                f"Missing fields: {', '.join(list(missing_fields)[:5])}. "
                f"Update prompt to require these fields."
            )
    
    # Deduplication suggestions
    if dedup_ratio < 0.70:
        suggestions.append(
            f"Deduplication ratio {dedup_ratio:.1%} suggests content repetition. "
            f"Review potential duplicates; merge or remove lower-confidence variants."
        )
    
    # Hallucination suggestions
    if hallucination_flags:
        critical_count = sum(1 for h in hallucination_flags if h.risk == "critical")
        if critical_count > 0:
            suggestions.append(
                f"CRITICAL: {critical_count} requirements flagged for potential hallucination. "
                f"Manual review required before proceeding."
            )
        else:
            suggestions.append(
                f"Hallucination risk detected ({len(hallucination_flags)} flags). "
                f"Review low-confidence requirements; consider stricter extraction."
            )
    
    if not suggestions:
        suggestions.append("All checks passed. Requirements ready for downstream processing.")
    
    return suggestions


def compute_overall_quality_score(
    coverage_ratio: float,
    avg_confidence: float,
    dedup_ratio: float,
    testability_issues: list,
    grounding_issues: list,
    schema_compliance_issues: list,
    hallucination_flags: list,
    total_requirements: int,
) -> float:
    """
    Compute overall quality score (0.0-1.0).
    
    Weighted combination of:
    - Coverage: 25%
    - Avg confidence: 25%
    - Dedup ratio: 15%
    - Testability: 15%
    - Grounding: 10%
    - Schema compliance: 10%
    """
    if total_requirements == 0:
        return 0.0
    
    # Normalize issue counts to ratios
    testability_ratio = 1.0 - min(1.0, len(testability_issues) / max(total_requirements, 1))
    grounding_ratio = 1.0 - min(1.0, len(grounding_issues) / max(total_requirements, 1))
    schema_ratio = 1.0 - min(1.0, len(schema_compliance_issues) / max(total_requirements, 1))
    
    # Penalize for hallucination flags
    hallucination_penalty = min(0.3, len(hallucination_flags) * 0.05)
    
    score = (
        0.25 * coverage_ratio +
        0.25 * avg_confidence +
        0.15 * dedup_ratio +
        0.15 * testability_ratio +
        0.10 * grounding_ratio +
        0.10 * schema_ratio -
        hallucination_penalty
    )
    
    return max(0.0, min(1.0, score))
