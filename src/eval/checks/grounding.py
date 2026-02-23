"""Grounding check for Eval node.

Integrates with confidence_scorer to use grounding classification.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.requirements import RegulatoryRequirement

from eval.models import GroundingIssue


def check_grounding(requirement: "RegulatoryRequirement") -> GroundingIssue | None:
    """
    Check if requirement has proper grounding in source text.
    
    Uses grounding classification from confidence scorer if available.
    Returns GroundingIssue if problems found, None if well-grounded.
    """
    issues: list[str] = []
    attrs = requirement.attributes
    
    # Get grounding classification from confidence scorer (if available)
    grounding_classification = attrs.get("_grounding_classification", "")
    confidence_features = attrs.get("_confidence_features", {})
    grounding_match = confidence_features.get("grounding_match", 0.0)
    
    # Must have grounded_in field
    if not requirement.grounded_in or not requirement.grounded_in.strip():
        issues.append("missing grounded_in citation")
    
    # Check grounding classification
    if grounding_classification == "INFERENCE":
        issues.append(f"grounding classified as INFERENCE (weak source match)")
    
    # Check grounding match score
    if grounding_match < 0.10:
        issues.append(f"very low grounding match ({grounding_match:.2f})")
    
    # Get iteration from metadata
    iteration = requirement.metadata.extraction_iteration
    confidence = requirement.confidence
    
    # Confidence thresholds by iteration
    if iteration == 1 and confidence < 0.70:
        issues.append(f"low confidence ({confidence:.2f}) on first iteration")
    
    if iteration >= 2 and confidence < 0.75:
        issues.append(f"low confidence ({confidence:.2f}) on retry iteration {iteration}")
    
    if not issues:
        return None
    
    severity = "high" if "missing" in str(issues) or confidence < 0.60 else "medium"
    return GroundingIssue(
        req_id=requirement.requirement_id,
        issues=issues,
        severity=severity,
        grounding_classification=grounding_classification,
    )
