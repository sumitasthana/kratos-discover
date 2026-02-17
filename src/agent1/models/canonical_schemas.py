"""Canonical attribute schemas for regulatory requirements."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    TIMELINESS = "timeliness"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    AVAILABILITY = "availability"


class ThresholdUnit(str, Enum):
    PERCENT = "percent"
    COUNT = "count"
    HOURS = "hours"
    DAYS = "days"
    DOLLARS = "dollars"
    MONTHS = "months"
    WEEKS = "weeks"
    YEARS = "years"


class MeasurementFrequency(str, Enum):
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ThresholdDirection(str, Enum):
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    EXACT = "exact"


CANONICAL_SCHEMAS: dict[str, dict] = {
    "data_quality_threshold": {
        "required": ["metric_type", "threshold_value", "threshold_unit", "applies_to"],
        "optional": ["threshold_direction", "measurement_frequency", "exception_threshold"],
        "enums": {"metric_type": MetricType, "threshold_unit": ThresholdUnit,
                  "threshold_direction": ThresholdDirection, "measurement_frequency": MeasurementFrequency},
    },
    "update_timeline": {
        "required": ["timeline_value", "timeline_unit", "trigger_event", "applies_to"],
        "optional": ["priority_levels"],
        "enums": {"timeline_unit": ThresholdUnit},
    },
    "documentation_requirement": {
        "required": ["document_type", "applies_to"],
        "optional": ["required_by", "validation_method", "approval_chain"],
        "enums": {},
    },
    "update_requirement": {
        "required": ["update_frequency", "responsible_party", "applies_to"],
        "optional": ["data_elements", "trigger_event"],
        "enums": {"update_frequency": MeasurementFrequency},
    },
    "beneficial_ownership_threshold": {
        "required": ["threshold_value", "threshold_unit", "applies_to"],
        "optional": ["identification_required", "threshold_direction"],
        "enums": {"threshold_unit": ThresholdUnit, "threshold_direction": ThresholdDirection},
    },
    "ownership_category": {
        "required": ["ownership_type", "scope"],
        "optional": ["responsibility", "required_data_elements", "insurance_coverage"],
        "enums": {},
    },
}

LEGACY_MAPPINGS = {
    "metric_type": ["metric", "threshold_type"],
    "timeline_value": ["threshold_value", "value"],
    "timeline_unit": ["threshold_unit", "unit"],
    "trigger_event": ["trigger", "applies_when"],
    "scope": ["applies_to"],
}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_attributes: dict[str, Any] = field(default_factory=dict)


def validate_canonical_schema(rule_type: str, attributes: dict[str, Any]) -> ValidationResult:
    schema = CANONICAL_SCHEMAS.get(rule_type)
    if not schema:
        return ValidationResult(is_valid=False, errors=[f"Unknown rule_type: {rule_type}"])
    
    errors, warnings, normalized = [], [], {}
    
    # Check required fields
    for field_name in schema["required"]:
        value = attributes.get(field_name)
        if value is None:
            for legacy in LEGACY_MAPPINGS.get(field_name, []):
                if legacy in attributes:
                    value = attributes[legacy]
                    break
        if value is None:
            errors.append(f"Missing: {field_name}")
        else:
            # Normalize enums
            if field_name in schema.get("enums", {}):
                enum_cls = schema["enums"][field_name]
                if isinstance(value, str):
                    try:
                        value = enum_cls(value.lower()).value
                    except ValueError:
                        warnings.append(f"{field_name}: '{value}' not in enum")
            normalized[field_name] = value
    
    # Copy optional fields
    for field_name in schema.get("optional", []):
        if field_name in attributes:
            normalized[field_name] = attributes[field_name]
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        normalized_attributes=normalized,
    )
