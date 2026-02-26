"""Regulatory requirement models for the Atomizer Agent."""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Import canonical RuleType from shared module
from models.shared import RuleType, RULE_TYPE_CODES


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
            "threshold_direction": str,
        },
        "optional": {
            "threshold_value": (int, float),
            "threshold_unit": str,
            "consequence": str,
        },
    },
    "enumeration_constraint": {
        "required": {
            "field_name": str,
            "permitted_values": list,
        },
        "optional": {
            "null_permitted": bool,
            "consequence": str,
        },
    },
    "referential_integrity": {
        "required": {
            "source_field": str,
            "target_file": str,
        },
        "optional": {
            "cardinality": str,
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
            "threshold_unit": str,
        },
        "optional": {
            "threshold_value": (int, float),
            "timeline": str,
            "consequence": str,
        },
    },
    "control_requirement": {
        "required": {
            "control_type": str,
        },
        "optional": {
            "control_mechanism": str,
            "applicable_fields": list,
            "data_source": str,
            "regulatory_basis": str,
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
    parent_component_id: str | None = Field(
        default=None,
        description="Component ID (P-001, C-001, R-001) from which this requirement was extracted."
    )

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

    def to_output_dict(self) -> dict[str, Any]:
        """
        Serialize requirement for output JSON, excluding debug internals and normalizing structure.
        
        Removes:
        - Debug fields: _original_description, _actionable_description, _verb_replacements
        - Schema validation: _schema_validation, _grounding_classification
        - Grounding evidence sub-fields: description_words, grounded_words, intersection, matched_phrases, phrase_count
        - Control metadata source fields: evidence_type_source, system_mapping_source, system_mapping_keywords
        - Metadata fields: extraction_iteration, prompt_version, schema_version
        - parent_component_id
        
        Transforms:
        - grounded_in → grounding object with jaccard_score and conditional source_text
        - Promotes fields from _control_metadata to top level
        - Suppresses system_mapping when source is default_template
        - Renames exception_threshold → exception_thresholds
        - Omits null/empty values
        """
        output = {
            "requirement_id": self.requirement_id,
            "rule_type": self.rule_type.value,
            "rule_description": self.rule_description,
            "confidence": round(self.confidence, 2),
        }

        # Build grounding object
        grounding: dict[str, Any] = {}
        if "_grounding_evidence" in self.attributes:
            evidence = self.attributes["_grounding_evidence"]
            if isinstance(evidence, dict) and "jaccard_score" in evidence:
                grounding["jaccard_score"] = evidence["jaccard_score"]
        
        # Include source_text only if different from rule_description
        if self.grounded_in and self.grounded_in != self.rule_description:
            grounding["source_text"] = self.grounded_in
        
        if grounding:
            output["grounding"] = grounding

        # Add confidence features (diagnostic but non-redundant)
        if "_confidence_features" in self.attributes:
            output["confidence_features"] = self.attributes["_confidence_features"]

        # Add confidence rationale
        if "_confidence_rationale" in self.attributes:
            output["confidence_rationale"] = self.attributes["_confidence_rationale"]

        # Promote fields from _control_metadata to top level
        if "_control_metadata" in self.attributes:
            metadata = self.attributes["_control_metadata"]
            if isinstance(metadata, dict):
                # control_objective
                if "control_objective" in metadata and metadata["control_objective"]:
                    output["control_objective"] = metadata["control_objective"]
                
                # risk_addressed
                if "risk_addressed" in metadata and metadata["risk_addressed"]:
                    output["risk_addressed"] = metadata["risk_addressed"]
                
                # control_owner
                if "control_owner" in metadata and metadata["control_owner"]:
                    output["control_owner"] = metadata["control_owner"]
                
                # test_procedure
                if "test_procedure" in metadata and metadata["test_procedure"]:
                    output["test_procedure"] = metadata["test_procedure"]
                
                # evidence_type
                if "evidence_type" in metadata and metadata["evidence_type"]:
                    output["evidence_type"] = metadata["evidence_type"]
                
                # system_mapping (suppress if source is default_template)
                if "system_mapping" in metadata and metadata["system_mapping"]:
                    if metadata.get("system_mapping_source") != "default_template":
                        output["system_mapping"] = metadata["system_mapping"]
                
                # exception_threshold → exception_thresholds
                if "exception_threshold" in metadata and metadata["exception_threshold"]:
                    output["exception_thresholds"] = metadata["exception_threshold"]
                
                # automated → automation_level
                if "automated" in metadata and metadata["automated"]:
                    output["automation_level"] = metadata["automated"]

        # Add other attributes (excluding debug/internal fields)
        excluded_keys = {
            "_original_description",
            "_actionable_description",
            "_verb_replacements",
            "_schema_validation",
            "_grounding_classification",
            "_grounding_evidence",
            "_control_metadata",
            "_confidence_features",
            "_confidence_rationale",
            "_fragment_warning",
            "_fragment_reason",
        }
        
        for key, value in self.attributes.items():
            if key not in excluded_keys and value is not None and value != {} and value != []:
                output[key] = value

        # Add metadata (excluding extraction_iteration, prompt_version, schema_version)
        metadata_output = {
            "source_chunk_id": self.metadata.source_chunk_id,
            "source_location": self.metadata.source_location,
        }
        output["metadata"] = metadata_output

        return output


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
    inference_rejected_count: int = 0  # Count of requirements rejected due to INFERENCE grounding


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
