"""Feature-based confidence scorer for regulatory requirements.

Implements the scoring logic specified in windsurf_agent_feedback.md:
- Grounding match (word overlap): 0.30 weight
- Completeness (required attrs): 0.20 weight
- Quantification specificity: 0.20 weight
- Schema compliance: 0.15 weight
- Coherence (grounded ≠ desc): 0.10 weight
- Domain-specific signals: 0.05 weight
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from agent1.models.requirements import (
    RegulatoryRequirement,
    RuleType,
    RULE_ATTRIBUTE_SCHEMAS,
)
from agent1.models.canonical_schemas import (
    validate_canonical_schema,
    CANONICAL_SCHEMAS,
)


@dataclass
class ConfidenceFeatures:
    """Breakdown of confidence score components."""
    grounding_match: float = 0.0
    completeness: float = 0.0
    quantification: float = 0.0
    schema_compliance: float = 0.0
    coherence: float = 0.0
    domain_signals: float = 0.0
    
    @property
    def total(self) -> float:
        """Sum of all feature scores, capped at 0.99."""
        raw = (
            self.grounding_match +
            self.completeness +
            self.quantification +
            self.schema_compliance +
            self.coherence +
            self.domain_signals
        )
        return min(0.99, max(0.50, raw))
    
    def to_dict(self) -> dict[str, float]:
        return {
            "grounding_match": round(self.grounding_match, 3),
            "completeness": round(self.completeness, 3),
            "quantification": round(self.quantification, 3),
            "schema_compliance": round(self.schema_compliance, 3),
            "coherence": round(self.coherence, 3),
            "domain_signals": round(self.domain_signals, 3),
        }


@dataclass
class ConfidenceResult:
    """Full confidence scoring result with rationale."""
    score: float
    features: ConfidenceFeatures
    rationale: str
    grounding_classification: str  # EXACT, PARAPHRASE, INFERENCE
    grounding_evidence: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": round(self.score, 2),
            "confidence_features": self.features.to_dict(),
            "confidence_rationale": self.rationale,
            "grounding_classification": self.grounding_classification,
            "grounding_evidence": self.grounding_evidence,
        }


# Domain-specific keywords that boost confidence
DOMAIN_KEYWORDS = {
    "fdic", "part 370", "deposit insurance", "insured deposit",
    "beneficial owner", "ownership category", "account holder",
    "recordkeeping", "compliance", "regulatory", "examination",
    "cip", "kyc", "bsa", "aml", "tin", "ssn", "ein",
}

# Quantification patterns
NUMERIC_PATTERN = re.compile(r"\d+\.?\d*\s*%?")
THRESHOLD_KEYWORDS = {"threshold", "minimum", "maximum", "at least", "no more than", "within"}
UNIT_KEYWORDS = {"percent", "%", "days", "hours", "months", "years", "dollars", "$"}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase words, removing punctuation."""
    words = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return set(words)


def _find_contiguous_phrases(source: str, target: str, min_words: int = 3) -> list[str]:
    """Find contiguous phrases from source that appear in target."""
    source_words = source.lower().split()
    target_lower = target.lower()
    
    phrases = []
    for i in range(len(source_words)):
        for length in range(min_words, min(len(source_words) - i + 1, 8)):
            phrase = " ".join(source_words[i:i + length])
            if phrase in target_lower:
                # Check it's not a subset of an already found phrase
                is_subset = any(phrase in p for p in phrases)
                if not is_subset:
                    # Remove any phrases that are subsets of this one
                    phrases = [p for p in phrases if p not in phrase]
                    phrases.append(phrase)
    
    return phrases


def _compute_grounding_match(description: str, grounded_in: str) -> tuple[float, dict]:
    """
    Compute grounding match score (0.30 weight).
    
    Returns (score, evidence_dict).
    """
    desc_words = _tokenize(description)
    grounded_words = _tokenize(grounded_in)
    
    if not desc_words or not grounded_words:
        return 0.0, {"error": "empty text"}
    
    intersection = desc_words & grounded_words
    union = desc_words | grounded_words
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Find contiguous phrase matches
    phrases = _find_contiguous_phrases(grounded_in, description)
    
    # Score calculation
    # Jaccard contributes up to 0.15
    jaccard_contribution = 0.15 * jaccard
    
    # Phrase matches contribute up to 0.15
    phrase_contribution = min(0.15, 0.05 * len(phrases))
    
    score = jaccard_contribution + phrase_contribution
    
    evidence = {
        "description_words": len(desc_words),
        "grounded_words": len(grounded_words),
        "intersection": len(intersection),
        "jaccard_score": round(jaccard, 3),
        "matched_phrases": phrases,
        "phrase_count": len(phrases),
    }
    
    return round(score, 3), evidence


def _compute_completeness(requirement: RegulatoryRequirement) -> float:
    """
    Compute attribute completeness score (0.20 weight).
    
    Score = (actual_required_attrs / total_required_attrs) * 0.20
    """
    rule_type_str = requirement.rule_type.value
    schema = RULE_ATTRIBUTE_SCHEMAS.get(rule_type_str)
    
    if not schema:
        return 0.0
    
    required_attrs = schema.get("required", {})
    if not required_attrs:
        return 0.20  # No required attrs = full score
    
    present_count = 0
    for attr_name, expected_type in required_attrs.items():
        if attr_name in requirement.attributes:
            value = requirement.attributes[attr_name]
            # Check type
            if isinstance(expected_type, tuple):
                if isinstance(value, expected_type):
                    present_count += 1
            elif isinstance(value, expected_type):
                present_count += 1
    
    ratio = present_count / len(required_attrs)
    return round(0.20 * ratio, 3)


def _compute_quantification(requirement: RegulatoryRequirement) -> float:
    """
    Compute quantification specificity score (0.20 weight).
    
    - Has threshold value: +0.10
    - Has unit: +0.05
    - Has exception threshold: +0.05
    """
    score = 0.0
    attrs = requirement.attributes
    desc = requirement.rule_description.lower()
    
    # Check for numeric threshold value
    has_threshold = False
    for key in ["threshold_value", "threshold"]:
        if key in attrs:
            val = attrs[key]
            if isinstance(val, (int, float)):
                has_threshold = True
                break
    
    # Also check description for numbers
    if not has_threshold and NUMERIC_PATTERN.search(desc):
        has_threshold = True
    
    if has_threshold:
        score += 0.10
    
    # Check for unit
    has_unit = False
    for key in ["threshold_unit", "unit", "threshold_direction"]:
        if key in attrs and attrs[key]:
            has_unit = True
            break
    
    # Check description for unit keywords
    if not has_unit:
        for unit in UNIT_KEYWORDS:
            if unit in desc:
                has_unit = True
                break
    
    if has_unit:
        score += 0.05
    
    # Check for exception threshold or consequence
    has_exception = False
    for key in ["exception_threshold", "consequence", "escalation"]:
        if key in attrs and attrs[key]:
            has_exception = True
            break
    
    if has_exception:
        score += 0.05
    
    return round(score, 3)


def _compute_schema_compliance(requirement: RegulatoryRequirement) -> float:
    """
    Compute schema compliance score (0.15 weight).
    
    Uses canonical schema validation for strict compliance checking.
    All required attrs present and correct type = 0.15
    """
    rule_type_str = requirement.rule_type.value
    
    # Use canonical schema validation if available
    if rule_type_str in CANONICAL_SCHEMAS:
        result = validate_canonical_schema(rule_type_str, requirement.attributes)
        if result.is_valid:
            return 0.15
        elif len(result.errors) <= 1:
            return 0.08  # Partial compliance
        else:
            return 0.0
    
    # Fallback to legacy schema
    schema = RULE_ATTRIBUTE_SCHEMAS.get(rule_type_str)
    if not schema:
        return 0.0
    
    required_attrs = schema.get("required", {})
    if not required_attrs:
        return 0.15  # No schema = full compliance
    
    # Check all required attrs
    for attr_name, expected_type in required_attrs.items():
        if attr_name not in requirement.attributes:
            return 0.0  # Missing required attr
        
        value = requirement.attributes[attr_name]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                return 0.0  # Wrong type
        elif not isinstance(value, expected_type):
            return 0.0  # Wrong type
    
    return 0.15


def _compute_coherence(description: str, grounded_in: str) -> float:
    """
    Compute coherence score (0.10 weight).
    
    Check for contradictions between description and grounded text.
    """
    desc_lower = description.lower()
    grounded_lower = grounded_in.lower()
    
    # Check for negation contradictions
    negation_pairs = [
        ("must not", "must"),
        ("shall not", "shall"),
        ("cannot", "can"),
        ("prohibited", "required"),
        ("never", "always"),
    ]
    
    for neg, pos in negation_pairs:
        # If one has negation and other has positive, it's a contradiction
        if neg in desc_lower and pos in grounded_lower and neg not in grounded_lower:
            return 0.0
        if neg in grounded_lower and pos in desc_lower and neg not in desc_lower:
            return 0.0
    
    # Check for numeric contradictions
    desc_nums = set(NUMERIC_PATTERN.findall(desc_lower))
    grounded_nums = set(NUMERIC_PATTERN.findall(grounded_lower))
    
    if desc_nums and grounded_nums:
        # If both have numbers but they don't overlap, potential issue
        if not (desc_nums & grounded_nums):
            return 0.05  # Partial score - different numbers might be paraphrase
    
    return 0.10


def _compute_domain_signals(requirement: RegulatoryRequirement) -> float:
    """
    Compute domain-specific signals score (0.05 weight).
    
    Presence of regulatory keywords boosts confidence.
    """
    text = f"{requirement.rule_description} {requirement.grounded_in}".lower()
    
    found_keywords = sum(1 for kw in DOMAIN_KEYWORDS if kw in text)
    
    if found_keywords >= 3:
        return 0.05
    elif found_keywords >= 1:
        return 0.03
    return 0.0


def _classify_grounding(grounding_score: float, features: ConfidenceFeatures) -> str:
    """
    Classify grounding quality based on score.
    
    - EXACT: >0.85 total or grounding_match >= 0.25
    - PARAPHRASE: 0.60-0.85 or grounding_match 0.15-0.25
    - INFERENCE: <0.60 or grounding_match < 0.15
    """
    if features.grounding_match >= 0.25:
        return "EXACT"
    elif features.grounding_match >= 0.15:
        return "PARAPHRASE"
    else:
        return "INFERENCE"


def _build_rationale(features: ConfidenceFeatures, grounding_evidence: dict) -> str:
    """Build human-readable rationale for the confidence score."""
    parts = []
    
    # Grounding
    jaccard = grounding_evidence.get("jaccard_score", 0)
    phrase_count = grounding_evidence.get("phrase_count", 0)
    if features.grounding_match >= 0.25:
        parts.append(f"Strong grounding ({jaccard:.0%} word overlap, {phrase_count} phrase matches)")
    elif features.grounding_match >= 0.15:
        parts.append(f"Moderate grounding ({jaccard:.0%} word overlap)")
    else:
        parts.append(f"Weak grounding ({jaccard:.0%} word overlap)")
    
    # Completeness
    if features.completeness >= 0.18:
        parts.append("attributes complete")
    elif features.completeness >= 0.10:
        parts.append("some attributes missing")
    else:
        parts.append("many attributes missing")
    
    # Quantification
    if features.quantification >= 0.15:
        parts.append("well-quantified")
    elif features.quantification >= 0.10:
        parts.append("partially quantified")
    elif features.quantification > 0:
        parts.append("minimal quantification")
    
    # Schema compliance
    if features.schema_compliance >= 0.15:
        parts.append("schema-compliant")
    else:
        parts.append("schema violations")
    
    # Coherence
    if features.coherence < 0.10:
        parts.append("potential contradictions")
    
    # Domain signals
    if features.domain_signals >= 0.05:
        parts.append("regulatory keywords present")
    
    return "; ".join(parts) + "."


def score_requirement(requirement: RegulatoryRequirement) -> ConfidenceResult:
    """
    Compute feature-based confidence score for a requirement.
    
    Returns ConfidenceResult with score, features breakdown, rationale,
    and grounding classification.
    """
    # Compute each feature
    grounding_score, grounding_evidence = _compute_grounding_match(
        requirement.rule_description,
        requirement.grounded_in
    )
    
    features = ConfidenceFeatures(
        grounding_match=grounding_score,
        completeness=_compute_completeness(requirement),
        quantification=_compute_quantification(requirement),
        schema_compliance=_compute_schema_compliance(requirement),
        coherence=_compute_coherence(
            requirement.rule_description,
            requirement.grounded_in
        ),
        domain_signals=_compute_domain_signals(requirement),
    )
    
    # Classify grounding
    classification = _classify_grounding(features.total, features)
    
    # Apply penalty for INFERENCE classification
    final_score = features.total
    if classification == "INFERENCE":
        final_score = min(final_score, 0.59)  # Cap at weak grounding tier
    
    # Build rationale
    rationale = _build_rationale(features, grounding_evidence)
    
    return ConfidenceResult(
        score=round(final_score, 2),
        features=features,
        rationale=rationale,
        grounding_classification=classification,
        grounding_evidence=grounding_evidence,
    )


def rescore_requirements(
    requirements: list[RegulatoryRequirement],
) -> list[tuple[RegulatoryRequirement, ConfidenceResult]]:
    """
    Rescore a list of requirements with feature-based confidence.
    
    Returns list of (requirement, confidence_result) tuples.
    The requirement's confidence field is updated in-place.
    """
    results = []
    for req in requirements:
        result = score_requirement(req)
        # Update the requirement's confidence
        req.confidence = result.score
        results.append((req, result))
    return results
