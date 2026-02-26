"""Shared model definitions for the Kratos Discover Agent.

This module contains canonical definitions for enums and type codes
used by the Agent1 pipeline for requirement extraction.

Usage:
    from models.shared import RuleType, RuleCategory, RULE_TYPE_CODES
"""
from __future__ import annotations

from enum import Enum


class RuleCategory(str, Enum):
    """Category of extracted rule/component."""
    RULE = "rule"
    CONTROL = "control"
    RISK = "risk"


class RuleType(str, Enum):
    """Types of regulatory requirements that can be extracted.
    
    - DATA_QUALITY_THRESHOLD: Quantitative standard with measurable metric
    - ENUMERATION_CONSTRAINT: Field must contain one of a fixed set of values
    - REFERENTIAL_INTEGRITY: Record in one file must have matching record in another
    - OWNERSHIP_CATEGORY: Account ownership classification
    - BENEFICIAL_OWNERSHIP_THRESHOLD: Numeric trigger for beneficial owners
    - DOCUMENTATION_REQUIREMENT: Required documents/records
    - UPDATE_REQUIREMENT: Event-triggered record updates
    - UPDATE_TIMELINE: Time-bound deadlines/SLAs
    - CONTROL_REQUIREMENT: Control-specific requirements
    - RISK_STATEMENT: Risk-related statements
    """
    DATA_QUALITY_THRESHOLD = "data_quality_threshold"
    ENUMERATION_CONSTRAINT = "enumeration_constraint"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    OWNERSHIP_CATEGORY = "ownership_category"
    BENEFICIAL_OWNERSHIP_THRESHOLD = "beneficial_ownership_threshold"
    DOCUMENTATION_REQUIREMENT = "documentation_requirement"
    UPDATE_REQUIREMENT = "update_requirement"
    UPDATE_TIMELINE = "update_timeline"
    CONTROL_REQUIREMENT = "control_requirement"
    RISK_STATEMENT = "risk_statement"


# Type code mapping for requirement ID generation
RULE_TYPE_CODES: dict[RuleType, str] = {
    RuleType.DATA_QUALITY_THRESHOLD: "DQ",
    RuleType.ENUMERATION_CONSTRAINT: "EC",
    RuleType.REFERENTIAL_INTEGRITY: "RI",
    RuleType.OWNERSHIP_CATEGORY: "OWN",
    RuleType.BENEFICIAL_OWNERSHIP_THRESHOLD: "BO",
    RuleType.DOCUMENTATION_REQUIREMENT: "DOC",
    RuleType.UPDATE_REQUIREMENT: "UPD",
    RuleType.UPDATE_TIMELINE: "TL",
    RuleType.CONTROL_REQUIREMENT: "CTL",
    RuleType.RISK_STATEMENT: "RSK",
}


# Core rule types for requirement extraction
CORE_RULE_TYPES = {
    RuleType.DATA_QUALITY_THRESHOLD,
    RuleType.OWNERSHIP_CATEGORY,
    RuleType.BENEFICIAL_OWNERSHIP_THRESHOLD,
    RuleType.DOCUMENTATION_REQUIREMENT,
    RuleType.UPDATE_REQUIREMENT,
    RuleType.UPDATE_TIMELINE,
}
