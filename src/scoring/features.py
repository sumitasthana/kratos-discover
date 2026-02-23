"""Feature computation utilities for confidence scoring.

Contains functions for computing individual feature scores
that contribute to the overall confidence score.
"""
from __future__ import annotations

import re
from typing import Any

from models.requirements import RegulatoryRequirement, RULE_ATTRIBUTE_SCHEMAS
from models.canonical_schemas import validate_canonical_schema, CANONICAL_SCHEMAS


# Quantification patterns
NUMERIC_PATTERN = re.compile(r"\d+\.?\d*\s*%?")
THRESHOLD_KEYWORDS = {"threshold", "minimum", "maximum", "at least", "no more than", "within"}
UNIT_KEYWORDS = {"percent", "%", "days", "hours", "months", "years", "dollars", "$"}


def compute_completeness(requirement: RegulatoryRequirement) -> float:
    """Compute attribute completeness score (0.20 weight).
    
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
            if isinstance(expected_type, tuple):
                if isinstance(value, expected_type):
                    present_count += 1
            elif isinstance(value, expected_type):
                present_count += 1
    
    ratio = present_count / len(required_attrs)
    return round(0.20 * ratio, 3)


def compute_quantification(requirement: RegulatoryRequirement) -> float:
    """Compute quantification specificity score (0.20 weight).
    
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


def compute_schema_compliance(requirement: RegulatoryRequirement) -> float:
    """Compute schema compliance score (0.15 weight).
    
    Uses canonical schema validation for strict compliance checking.
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
    
    for attr_name, expected_type in required_attrs.items():
        if attr_name not in requirement.attributes:
            return 0.0
        
        value = requirement.attributes[attr_name]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                return 0.0
        elif not isinstance(value, expected_type):
            return 0.0
    
    return 0.15
