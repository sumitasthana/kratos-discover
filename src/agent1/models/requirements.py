"""Regulatory requirement models for the Atomizer Agent."""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Import canonical RuleType from shared module
from shared.models import RuleType, RULE_TYPE_CODES


class ChunkSkipReason(str, Enum):
    """Reason why a chunk yielded zero extractions (CF-3)."""
    NO_EXTRACTABLE_CONTENT = "no_extractable_content"  # Chunk has no regulatory obligations
    PARSE_ERROR = "parse_error"  # LLM response parsing failed
    BELOW_THRESHOLD = "below_threshold"  # All extractions below confidence threshold
    LLM_ERROR = "llm_error"  # LLM call failed
    EMPTY_RESPONSE = "empty_response"  # LLM returned empty/null response


# Attribute schemas for validation
RULE_ATTRIBUTE_SCHEMAS: dict[str, dict[str, dict]] = {
    "data_quality_threshold": {
        "required": {
            "metric": str,
            "threshold_value": (int, float),
            "threshold_direction": str,
        },
        "optional": {
            "threshold_unit": str,
            "consequence": str,
        },
    },
    "ownership_category": {
        "required": {
            "ownership_type": str,
            "required_data_elements": list,
        },
        "optional": {
            "insurance_coverage": str,
            "cardinality": str,
        },
    },
    "beneficial_ownership_threshold": {
        "required": {
            "threshold_value": (int, float),
            "threshold_unit": str,
        },
        "optional": {
            "applies_to": str,
            "requirement": str,
            "threshold_direction": str,
        },
    },
    "documentation_requirement": {
        "required": {
            "applies_to": str,
            "requirement": str,
        },
        "optional": {
            "consequence": str,
        },
    },
    "update_requirement": {
        "required": {
            "applies_when": str,
            "requirement": str,
        },
        "optional": {
            "applies_to": str,
            "consequence": str,
        },
    },
    "update_timeline": {
        "required": {
            "applies_to": str,
            "threshold_value": (int, float),
            "threshold_unit": str,
        },
        "optional": {
            "consequence": str,
        },
    },
}


class RuleMetadata(BaseModel):
    """Metadata about the extraction source and context."""
    source_chunk_id: str
    source_location: str
    schema_version: str
    prompt_version: str
    extraction_iteration: int


class RegulatoryRequirement(BaseModel):
    """One atomic, testable regulatory obligation."""
    requirement_id: str = Field(
        description="Deterministic ID: R-{RULE_TYPE_CODE}-{HASH6}. "
        "HASH6 = first 6 chars of SHA256(rule_description + grounded_in)."
    )
    rule_type: RuleType
    rule_description: str = Field(
        description="Plain-English statement of the obligation. One sentence. "
        "Must be testable — a QA analyst should be able to verify pass/fail."
    )
    grounded_in: str = Field(
        description="Verbatim text span from the source chunk that supports this requirement. "
        "Must be copy-pasteable back to the document."
    )
    confidence: float = Field(
        ge=0.50, le=0.99,
        description="4-tier calibration: 0.90-0.99 exact match, 0.80-0.89 minor inference, "
        "0.70-0.79 moderate inference, 0.50-0.69 weak grounding."
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific fields. Keys and required/optional status depend on rule_type."
    )
    metadata: RuleMetadata

    @staticmethod
    def generate_requirement_id(rule_type: RuleType, rule_description: str, grounded_in: str) -> str:
        """Generate deterministic requirement ID from content."""
        type_code = RULE_TYPE_CODES.get(rule_type, "UNK")
        content = f"{rule_description}|{grounded_in}"
        hash_hex = hashlib.sha256(content.encode()).hexdigest()[:6]
        return f"R-{type_code}-{hash_hex}"

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        """Clamp confidence to valid range."""
        if v < 0.50:
            return 0.50
        if v > 0.99:
            return 0.99
        return v


class ChunkSkipRecord(BaseModel):
    """Record of a skipped chunk with reason (CF-3)."""
    chunk_id: str
    skip_reason: ChunkSkipReason
    detail: str = ""  # Optional additional context


class ExtractionMetadata(BaseModel):
    """Stats about the extraction run."""
    total_chunks_processed: int
    total_requirements_extracted: int
    chunks_with_zero_extractions: list[str] = Field(default_factory=list)  # Legacy: just IDs
    skipped_chunks: list[ChunkSkipRecord] = Field(default_factory=list)  # CF-3: With reasons
    avg_confidence: float = 0.0
    rule_type_distribution: dict[str, int] = Field(default_factory=dict)
    extraction_iteration: int
    prompt_version: str
    model_used: str
    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


def validate_requirement_attributes(
    requirement: RegulatoryRequirement,
) -> tuple[bool, list[str]]:
    """
    Validate requirement attributes against the schema for its rule_type.
    Returns (is_valid, list_of_missing_required_fields).
    """
    rule_type_str = requirement.rule_type.value
    schema = RULE_ATTRIBUTE_SCHEMAS.get(rule_type_str)
    
    if not schema:
        return False, [f"Unknown rule_type: {rule_type_str}"]
    
    missing_required: list[str] = []
    required_attrs = schema.get("required", {})
    
    for attr_name, expected_type in required_attrs.items():
        if attr_name not in requirement.attributes:
            missing_required.append(attr_name)
        else:
            value = requirement.attributes[attr_name]
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    missing_required.append(f"{attr_name} (wrong type)")
            elif not isinstance(value, expected_type):
                missing_required.append(f"{attr_name} (wrong type)")
    
    return len(missing_required) == 0, missing_required
