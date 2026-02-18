"""Shared model definitions used across rule_agent and agent1.

This module contains canonical definitions for enums and type codes
that were previously duplicated between rule_agent.py and agent1/models/requirements.py.

Usage:
    from shared.models import RuleType, RuleCategory, RULE_TYPE_CODES
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
    
    Core types (used by agent1):
    - DATA_QUALITY_THRESHOLD: Quantitative standard with measurable metric
    - OWNERSHIP_CATEGORY: Account ownership classification
    - BENEFICIAL_OWNERSHIP_THRESHOLD: Numeric trigger for beneficial owners
    - DOCUMENTATION_REQUIREMENT: Required documents/records
    - UPDATE_REQUIREMENT: Event-triggered record updates
    - UPDATE_TIMELINE: Time-bound deadlines/SLAs
    
    Extended types (used by rule_agent GRC mode):
    - CONTROL_REQUIREMENT: Control-specific requirements
    - RISK_STATEMENT: Risk-related statements
    """
    # Core types (agent1)
    DATA_QUALITY_THRESHOLD = "data_quality_threshold"
    OWNERSHIP_CATEGORY = "ownership_category"
    BENEFICIAL_OWNERSHIP_THRESHOLD = "beneficial_ownership_threshold"
    DOCUMENTATION_REQUIREMENT = "documentation_requirement"
    UPDATE_REQUIREMENT = "update_requirement"
    UPDATE_TIMELINE = "update_timeline"
    
    # Extended types (rule_agent GRC mode)
    CONTROL_REQUIREMENT = "control_requirement"
    RISK_STATEMENT = "risk_statement"


# Type code mapping for requirement ID generation
RULE_TYPE_CODES: dict[RuleType, str] = {
    RuleType.DATA_QUALITY_THRESHOLD: "DQ",
    RuleType.OWNERSHIP_CATEGORY: "OWN",
    RuleType.BENEFICIAL_OWNERSHIP_THRESHOLD: "BO",
    RuleType.DOCUMENTATION_REQUIREMENT: "DOC",
    RuleType.UPDATE_REQUIREMENT: "UPD",
    RuleType.UPDATE_TIMELINE: "TL",
    RuleType.CONTROL_REQUIREMENT: "CTL",
    RuleType.RISK_STATEMENT: "RSK",
}


# Core rule types used by agent1 (excludes GRC-specific types)
CORE_RULE_TYPES = {
    RuleType.DATA_QUALITY_THRESHOLD,
    RuleType.OWNERSHIP_CATEGORY,
    RuleType.BENEFICIAL_OWNERSHIP_THRESHOLD,
    RuleType.DOCUMENTATION_REQUIREMENT,
    RuleType.UPDATE_REQUIREMENT,
    RuleType.UPDATE_TIMELINE,
}
