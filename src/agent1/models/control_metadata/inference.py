"""Inference functions for control metadata.

Contains all the infer_* functions that derive control metadata
from rule types, descriptions, and attributes.
"""
from __future__ import annotations

import re
from typing import Any

from agent1.models.control_metadata.templates import (
    AutomationStatus,
    RiskCategory,
    CONTROL_OBJECTIVE_TEMPLATES,
    RISK_MAPPING,
    OWNER_MAPPING,
    EVIDENCE_TYPES,
    SYSTEM_KEYWORDS,
    TEST_PROCEDURE_MATRIX,
    DEFAULT_TEST_PROCEDURE,
    TYPE_TO_CONTROL,
)


def infer_control_objective(rule_type: str, rule_description: str, attributes: dict) -> str:
    """Infer control objective from rule type and description.
    
    CF-4: Fixed template interpolation bug - removed redundant "data" after {applies_to}
    to prevent "relevant data data" when applies_to defaults to "relevant data".
    """
    template = CONTROL_OBJECTIVE_TEMPLATES.get(
        rule_type, "Ensure compliance with regulatory requirements."
    )
    applies_to = attributes.get("applies_to", "relevant records")
    
    # CF-4: Validate output doesn't have doubled words
    result = template.format(applies_to=applies_to)
    
    # Simple regex check for doubled words (e.g., "data data")
    doubled_word_pattern = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
    if doubled_word_pattern.search(result):
        # Log warning but don't fail - just clean up
        result = doubled_word_pattern.sub(r'\1', result)
    
    return result


def infer_risks(rule_type: str, rule_description: str) -> list[str]:
    """Infer risk categories from rule type and description."""
    desc_lower = rule_description.lower()
    risks = RISK_MAPPING.get(rule_type, [RiskCategory.REGULATORY_COMPLIANCE.value])
    
    if any(kw in desc_lower for kw in ["system", "availability", "uptime"]):
        if RiskCategory.SYSTEM_AVAILABILITY.value not in risks:
            risks = risks + [RiskCategory.SYSTEM_AVAILABILITY.value]
    
    if any(kw in desc_lower for kw in ["vendor", "third-party", "external"]):
        if RiskCategory.VENDOR_THIRD_PARTY.value not in risks:
            risks = risks + [RiskCategory.VENDOR_THIRD_PARTY.value]
    
    return risks[:3]  # Max 3 risks


def _infer_control_type(rule_type: str, rule_description: str) -> str:
    """Infer control type from rule type and description (CF-10)."""
    desc_lower = rule_description.lower()
    
    if any(kw in desc_lower for kw in ["system", "uptime", "availability", "sla"]):
        return "system_availability"
    if any(kw in desc_lower for kw in ["accuracy", "completeness", "quality", "valid"]):
        return "data_quality"
    if any(kw in desc_lower for kw in ["timeline", "within", "days", "hours"]):
        return "timeliness"
    if any(kw in desc_lower for kw in ["document", "record", "retain"]):
        return "documentation"
    if any(kw in desc_lower for kw in ["owner", "beneficial", "category"]):
        return "classification"
    
    return TYPE_TO_CONTROL.get(rule_type, "general")


def _infer_measurement_type(rule_type: str, attributes: dict) -> str:
    """Infer measurement type from rule type and attributes (CF-10)."""
    if attributes.get("threshold_value") or attributes.get("metric"):
        return "quantitative"
    if attributes.get("timeline_value"):
        return "timeline"
    if rule_type in ("documentation_requirement", "ownership_category"):
        return "qualitative"
    return "quantitative"


def infer_test_procedure(
    rule_type: str,
    rule_description: str,
    attributes: dict,
) -> str:
    """Generate test procedure based on control_type × measurement_type matrix (CF-10)."""
    applies_to = attributes.get("applies_to", "relevant records")
    threshold = attributes.get("threshold_value", attributes.get("timeline_value", ""))
    unit = attributes.get("threshold_unit", attributes.get("timeline_unit", ""))
    
    # CF-10: Determine control_type and measurement_type
    control_type = _infer_control_type(rule_type, rule_description)
    measurement_type = _infer_measurement_type(rule_type, attributes)
    
    # Look up in matrix
    template = TEST_PROCEDURE_MATRIX.get((control_type, measurement_type))
    
    # Fallback to closest match
    if not template:
        for (ct, mt), tmpl in TEST_PROCEDURE_MATRIX.items():
            if ct == control_type:
                template = tmpl
                break
    
    # Final fallback
    if not template:
        template = DEFAULT_TEST_PROCEDURE
    
    return template.format(applies_to=applies_to, threshold=threshold, unit=unit)


def infer_control_owner(rule_type: str, attributes: dict) -> str:
    """Infer control owner from rule type and attributes."""
    responsible = attributes.get("responsible_party", "")
    if responsible:
        return responsible
    
    return OWNER_MAPPING.get(rule_type, "Chief Compliance Officer")


def infer_automation_status(rule_type: str, rule_description: str) -> str:
    """Infer automation status from rule description."""
    desc_lower = rule_description.lower()
    
    auto_keywords = ["system", "automated", "real-time", "api", "validation service"]
    manual_keywords = ["sampling", "review", "manual", "quarterly", "annual"]
    
    auto_score = sum(1 for kw in auto_keywords if kw in desc_lower)
    manual_score = sum(1 for kw in manual_keywords if kw in desc_lower)
    
    if auto_score > manual_score:
        return AutomationStatus.AUTOMATED.value
    elif manual_score > auto_score:
        return AutomationStatus.MANUAL.value
    else:
        return AutomationStatus.HYBRID.value


def infer_evidence_types(rule_type: str) -> list[str]:
    """Get evidence types for rule type."""
    return EVIDENCE_TYPES.get(rule_type, ["Compliance documentation"])


def infer_systems(rule_type: str, rule_description: str) -> tuple[list[str], str, list[str]]:
    """Infer system mapping from rule description.
    
    Returns: (systems, source, matched_keywords)
    - systems: List of inferred system names
    - source: "keyword_inferred" | "default_template"
    - matched_keywords: Keywords that triggered the inference (CF-13)
    """
    desc_lower = rule_description.lower()
    systems = []
    matched_keywords = []
    
    for system, keywords in SYSTEM_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                systems.append(system)
                matched_keywords.append(kw)
                break  # Only add system once
    
    if systems:
        return systems[:3], "keyword_inferred", matched_keywords
    else:
        return ["core_banking_platform"], "default_template", []


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            clean = value.replace("%", "").strip()
            return float(clean)
        except ValueError:
            return default
    return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            clean = value.replace("%", "").strip()
            return int(float(clean))
        except ValueError:
            return default
    return default


def infer_exception_threshold(
    rule_type: str,
    attributes: dict,
) -> dict[str, Any]:
    """Generate exception threshold tiers."""
    threshold = _safe_float(attributes.get("threshold_value", 99), 99.0)
    unit = attributes.get("threshold_unit", "percent")
    
    if rule_type == "data_quality_threshold" and unit in ("percent", "%"):
        return {
            "tier_1_critical": {
                "condition": f"< {threshold - 1}%",
                "action": "Halt processing; escalate to VP Compliance",
                "sla_remediation": "15 days",
            },
            "tier_2_high": {
                "condition": f"{threshold - 1}% - {threshold - 0.5}%",
                "action": "Escalate to Manager; prepare remediation plan",
                "sla_remediation": "30 days",
            },
            "tier_3_medium": {
                "condition": f"{threshold - 0.5}% - {threshold}%",
                "action": "Log exception; monitor closely",
                "sla_remediation": "60 days",
            },
        }
    elif rule_type == "update_timeline":
        timeline = _safe_int(attributes.get("timeline_value", 30), 30)
        return {
            "breach": {
                "condition": f"Update not completed within {timeline} {unit}",
                "action": "Escalate to control owner; initiate remediation",
                "sla_remediation": f"{timeline // 2} {unit}",
            },
        }
    
    return {}
