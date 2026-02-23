"""Deduplication analysis for Eval node."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.requirements import RegulatoryRequirement

from eval.models import PotentialDuplicate


def check_deduplication(
    requirements: list["RegulatoryRequirement"],
    similarity_threshold: float = 0.75,
) -> tuple[float, list[PotentialDuplicate]]:
    """
    Detect near-duplicate requirements.
    
    Uses Jaccard similarity on rule descriptions.
    
    Args:
        requirements: List of requirements to check
        similarity_threshold: Minimum similarity to flag as duplicate (default 0.75)
    
    Returns:
        (dedup_ratio, potential_duplicates)
    """
    if not requirements:
        return 1.0, []
    
    potential_dups: list[PotentialDuplicate] = []
    
    for i, req_a in enumerate(requirements):
        for req_b in requirements[i + 1:]:
            # Quick check: same rule type
            if req_a.rule_type != req_b.rule_type:
                continue
            
            # Compute Jaccard similarity on descriptions
            desc_a = set((req_a.rule_description or "").lower().split())
            desc_b = set((req_b.rule_description or "").lower().split())
            
            if not desc_a or not desc_b:
                continue
            
            intersection = len(desc_a & desc_b)
            union = len(desc_a | desc_b)
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity >= similarity_threshold:
                potential_dups.append(PotentialDuplicate(
                    req_id_a=req_a.requirement_id,
                    req_id_b=req_b.requirement_id,
                    similarity=round(similarity, 3),
                    rule_type=req_a.rule_type.value,
                ))
    
    # Calculate dedup ratio
    # Each duplicate pair means one redundant requirement
    unique_count = len(requirements) - len(potential_dups)
    dedup_ratio = unique_count / len(requirements) if requirements else 1.0
    
    return dedup_ratio, potential_dups
