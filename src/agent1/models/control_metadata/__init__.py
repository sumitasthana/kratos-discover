"""Control metadata package for regulatory requirements.

This package contains control operationalization metadata:
- models.py: ControlMetadata and ExceptionTier dataclasses
- templates.py: Static template dictionaries and enums
- inference.py: All infer_* functions

Usage:
    from agent1.models.control_metadata import (
        ControlMetadata,
        enrich_requirement_metadata,
    )
"""
from agent1.models.control_metadata.models import (
    ControlMetadata,
    ExceptionTier,
)
from agent1.models.control_metadata.templates import (
    AutomationStatus,
    RiskCategory,
    CANONICAL_OWNERS,
    CANONICAL_SYSTEMS,
    EVIDENCE_TYPES,
)
from agent1.models.control_metadata.inference import (
    infer_control_objective,
    infer_risks,
    infer_test_procedure,
    infer_control_owner,
    infer_automation_status,
    infer_evidence_types,
    infer_systems,
    infer_exception_threshold,
)


def enrich_requirement_metadata(
    rule_type: str,
    rule_description: str,
    attributes: dict,
) -> ControlMetadata:
    """Generate complete control metadata for a requirement.
    
    This function infers all 8 metadata fields based on the rule type,
    description, and attributes.
    
    Source tracking (CF-12, CF-13):
    - evidence_type_source: Always "default_template" (template-assigned)
    - system_mapping_source: "keyword_inferred" or "default_template"
    - system_mapping_keywords: Keywords that triggered system inference
    """
    # CF-13: Get systems with source tracking
    systems, system_source, system_keywords = infer_systems(rule_type, rule_description)
    
    return ControlMetadata(
        control_objective=infer_control_objective(rule_type, rule_description, attributes),
        risk_addressed=infer_risks(rule_type, rule_description),
        test_procedure=infer_test_procedure(rule_type, rule_description, attributes),
        control_owner=infer_control_owner(rule_type, attributes),
        automated=infer_automation_status(rule_type, rule_description),
        evidence_type=infer_evidence_types(rule_type),
        evidence_type_source="default_template",  # CF-12: Always template-assigned
        system_mapping=systems,
        system_mapping_source=system_source,  # CF-13: keyword_inferred or default_template
        system_mapping_keywords=system_keywords,  # CF-13: Grounding evidence
        exception_threshold=infer_exception_threshold(rule_type, attributes),
    )


__all__ = [
    # Models
    "ControlMetadata",
    "ExceptionTier",
    # Enums
    "AutomationStatus",
    "RiskCategory",
    # Constants
    "CANONICAL_OWNERS",
    "CANONICAL_SYSTEMS",
    "EVIDENCE_TYPES",
    # Main function
    "enrich_requirement_metadata",
    # Inference functions
    "infer_control_objective",
    "infer_risks",
    "infer_test_procedure",
    "infer_control_owner",
    "infer_automation_status",
    "infer_evidence_types",
    "infer_systems",
    "infer_exception_threshold",
]
