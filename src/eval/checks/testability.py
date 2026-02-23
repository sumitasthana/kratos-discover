"""Testability check for Eval node."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.requirements import RegulatoryRequirement

from eval.models import TestabilityIssue


def check_testability(requirement: "RegulatoryRequirement") -> TestabilityIssue | None:
    """
    Check if a requirement is testable (has clear pass/fail condition).
    
    Returns TestabilityIssue if problems found, None if testable.
    """
    issues: list[str] = []
    rule_type = requirement.rule_type.value
    attrs = requirement.attributes
    desc_lower = (requirement.rule_description or "").lower()
    
    # Check for unknown rule type
    if rule_type == "unknown":
        issues.append("rule_type not mapped")
    
    # data_quality_threshold must have threshold_value and metric
    if rule_type == "data_quality_threshold":
        if not attrs.get("threshold_value") and not attrs.get("metric_type"):
            # Check for legacy field names
            if not attrs.get("metric"):
                issues.append("missing metric definition")
        if not attrs.get("threshold_value"):
            issues.append("missing threshold_value (cannot test)")
    
    # documentation_requirement must specify WHAT and BY WHEN
    if rule_type == "documentation_requirement":
        if not attrs.get("document_type") and not attrs.get("documentation_type"):
            issues.append("missing documentation_type")
        if not attrs.get("required_by") and not attrs.get("applies_when"):
            issues.append("missing trigger condition (applies_when)")
    
    # update_timeline must have timeline value
    if rule_type == "update_timeline":
        if not attrs.get("timeline_value") and not attrs.get("threshold_value"):
            issues.append("missing timeline value")
    
    # update_requirement must have frequency
    if rule_type == "update_requirement":
        if not attrs.get("update_frequency") and not attrs.get("applies_when"):
            issues.append("missing update frequency")
    
    # beneficial_ownership_threshold must have threshold
    if rule_type == "beneficial_ownership_threshold":
        if not attrs.get("threshold_value"):
            issues.append("missing ownership threshold value")
    
    # Check if description is purely definitional
    if desc_lower.startswith("a ") and " means " in desc_lower:
        issues.append("appears to be a definition, not an obligation")
    if desc_lower.startswith("the term "):
        issues.append("appears to be a definition, not an obligation")
    
    # Check for vague language without quantification
    vague_patterns = ["appropriate", "reasonable", "adequate", "sufficient", "as needed"]
    has_vague = any(p in desc_lower for p in vague_patterns)
    has_number = any(c.isdigit() for c in desc_lower)
    if has_vague and not has_number:
        issues.append("vague language without quantification")
    
    if not issues:
        return None
    
    severity = "high" if len(issues) > 1 else "medium"
    return TestabilityIssue(
        req_id=requirement.requirement_id,
        issues=issues,
        severity=severity,
    )
