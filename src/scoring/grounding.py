"""Grounding analysis utilities for confidence scoring.

Contains functions for analyzing the relationship between
rule_description and grounded_in text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Domain-specific keywords that boost confidence
DOMAIN_KEYWORDS = {
    "fdic", "part 370", "deposit insurance", "insured deposit",
    "beneficial owner", "ownership category", "account holder",
    "recordkeeping", "compliance", "regulatory", "examination",
    "cip", "kyc", "bsa", "aml", "tin", "ssn", "ein",
}

# Quantification patterns
NUMERIC_PATTERN = re.compile(r"\d+\.?\d*\s*%?")


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase words, removing punctuation."""
    words = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return set(words)


def find_contiguous_phrases(source: str, target: str, min_words: int = 3) -> list[str]:
    """Find contiguous phrases from source that appear in target."""
    source_words = source.lower().split()
    target_lower = target.lower()
    
    phrases = []
    for i in range(len(source_words)):
        for length in range(min_words, min(len(source_words) - i + 1, 8)):
            phrase = " ".join(source_words[i:i + length])
            if phrase in target_lower:
                is_subset = any(phrase in p for p in phrases)
                if not is_subset:
                    phrases = [p for p in phrases if p not in phrase]
                    phrases.append(phrase)
    
    return phrases


def compute_grounding_match(description: str, grounded_in: str) -> tuple[float, dict]:
    """Compute grounding match score (0.30 weight).
    
    Returns (score, evidence_dict).
    """
    desc_words = tokenize(description)
    grounded_words = tokenize(grounded_in)
    
    if not desc_words or not grounded_words:
        return 0.0, {"error": "empty text"}
    
    intersection = desc_words & grounded_words
    union = desc_words | grounded_words
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Find contiguous phrase matches
    phrases = find_contiguous_phrases(grounded_in, description)
    
    # Score calculation
    jaccard_contribution = 0.15 * jaccard
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


def compute_coherence(description: str, grounded_in: str) -> float:
    """Compute coherence score (0.10 weight).
    
    Check for contradictions between description and grounded text.
    """
    desc_lower = description.lower()
    grounded_lower = grounded_in.lower()
    
    negation_pairs = [
        ("must not", "must"),
        ("shall not", "shall"),
        ("cannot", "can"),
        ("prohibited", "required"),
        ("never", "always"),
    ]
    
    for neg, pos in negation_pairs:
        if neg in desc_lower and pos in grounded_lower and neg not in grounded_lower:
            return 0.0
        if neg in grounded_lower and pos in desc_lower and neg not in desc_lower:
            return 0.0
    
    desc_nums = set(NUMERIC_PATTERN.findall(desc_lower))
    grounded_nums = set(NUMERIC_PATTERN.findall(grounded_lower))
    
    if desc_nums and grounded_nums:
        if not (desc_nums & grounded_nums):
            return 0.05
    
    return 0.10


def compute_domain_signals(description: str, grounded_in: str) -> float:
    """Compute domain-specific signals score (0.05 weight).
    
    Presence of regulatory keywords boosts confidence.
    """
    text = f"{description} {grounded_in}".lower()
    
    found_keywords = sum(1 for kw in DOMAIN_KEYWORDS if kw in text)
    
    if found_keywords >= 3:
        return 0.05
    elif found_keywords >= 1:
        return 0.03
    return 0.0


@dataclass
class GroundingClassification:
    """Result of grounding classification."""
    classification: str  # EXACT, PARAPHRASE, INFERENCE
    requires_manual_review: bool
    jaccard_score: float


def classify_grounding(
    grounding_match_score: float,
    jaccard_score: float,
) -> GroundingClassification:
    """Classify grounding quality based on score.
    
    Classifications:
    - EXACT: grounding_match >= 0.25
    - PARAPHRASE: grounding_match 0.15-0.25
    - INFERENCE: grounding_match < 0.15
    
    Manual review required if INFERENCE + jaccard < 0.30 (CF-11)
    """
    if grounding_match_score >= 0.25:
        return GroundingClassification("EXACT", False, jaccard_score)
    elif grounding_match_score >= 0.15:
        return GroundingClassification("PARAPHRASE", False, jaccard_score)
    else:
        requires_review = jaccard_score < 0.30
        return GroundingClassification("INFERENCE", requires_review, jaccard_score)
