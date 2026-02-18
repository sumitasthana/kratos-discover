"""Shared models and utilities used across the codebase.

This package contains canonical definitions that are shared between
rule_agent.py and agent1/ to avoid duplication.
"""
from shared.models import (
    RuleType,
    RuleCategory,
    RULE_TYPE_CODES,
)

__all__ = [
    "RuleType",
    "RuleCategory",
    "RULE_TYPE_CODES",
]
