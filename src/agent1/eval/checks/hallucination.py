"""Hallucination detection for Eval node."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent1.models.requirements import RegulatoryRequirement

from agent1.eval.models import HallucinationFlag


def check_hallucination(requirement: "RegulatoryRequirement") -> HallucinationFlag | None:
    """
    Detect potential hallucination based on confidence tiers.
    
    Rules:
    - 0.90-0.99: Direct quote; safe
    - 0.80-0.89: Minor inference; acceptable on iter 1, risky on iter 2+
    - 0.70-0.79: Moderate inference; flag on retry pass
    - <0.70: Never accept on retry; reject on iter 1
    
    Returns HallucinationFlag if risk detected, None if safe.
    """
    flags: list[str] = []
    risk = "low"
    
    confidence = requirement.confidence
    iteration = requirement.metadata.extraction_iteration
    attrs = requirement.attributes
    
    # Get grounding classification from confidence scorer
    grounding_classification = attrs.get("_grounding_classification", "")
    
    # First iteration checks
    if iteration == 1:
        if confidence < 0.60:
            flags.append(f"Confidence {confidence:.2f} critically low on first pass")
            risk = "critical"
        elif confidence < 0.70:
            flags.append(f"Confidence {confidence:.2f} below safe threshold on first pass")
            risk = "high"
        elif confidence < 0.80:
            flags.append(f"Moderate inference ({confidence:.2f}); recommend human review")
            risk = "medium"
    
    # Retry iteration checks (stricter thresholds)
    if iteration >= 2:
        if confidence < 0.70:
            flags.append(f"Retry pass: confidence {confidence:.2f} critically low")
            risk = "critical"
        elif confidence < 0.75:
            flags.append(f"Retry pass: confidence {confidence:.2f} still below retry threshold (0.75)")
            risk = "high"
        elif confidence < 0.85:
            flags.append(f"Retry pass: moderate inference ({confidence:.2f}); borderline")
            risk = "medium"
    
    # INFERENCE classification is always a flag
    if grounding_classification == "INFERENCE":
        if "INFERENCE" not in str(flags):
            flags.append("Grounding classified as INFERENCE (potential fabrication)")
            if risk == "low":
                risk = "medium"
    
    if not flags:
        return None
    
    return HallucinationFlag(
        req_id=requirement.requirement_id,
        flags=flags,
        risk=risk,
        confidence=confidence,
        iteration=iteration,
    )
