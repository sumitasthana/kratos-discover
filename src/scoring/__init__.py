"""Scoring modules for the Atomizer Agent.

This package contains:
- confidence_scorer.py: Main scoring orchestration
- grounding.py: Grounding analysis utilities
- features.py: Feature computation functions
- verb_replacer.py: Vague verb replacement
"""
from scoring.confidence_scorer import (
    ConfidenceFeatures,
    ConfidenceResult,
    score_requirement,
    rescore_requirements,
)
from scoring.grounding import (
    GroundingClassification,
    classify_grounding,
    compute_grounding_match,
    compute_coherence,
    compute_domain_signals,
)
from scoring.features import (
    compute_completeness,
    compute_quantification,
    compute_schema_compliance,
)

__all__ = [
    # Main scorer
    "ConfidenceFeatures",
    "ConfidenceResult",
    "score_requirement",
    "rescore_requirements",
    # Grounding
    "GroundingClassification",
    "classify_grounding",
    "compute_grounding_match",
    "compute_coherence",
    "compute_domain_signals",
    # Features
    "compute_completeness",
    "compute_quantification",
    "compute_schema_compliance",
]
