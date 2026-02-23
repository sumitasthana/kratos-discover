"""Schema compliance check for Eval node.

Integrates with canonical_schemas for validation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.requirements import RegulatoryRequirement

from eval.models import SchemaComplianceIssue
from models.canonical_schemas import validate_canonical_schema, CANONICAL_SCHEMAS


def check_schema_compliance(requirement: "RegulatoryRequirement") -> SchemaComplianceIssue | None:
    """
    Check if requirement attributes comply with canonical schema.
    
    Uses canonical_schemas.validate_canonical_schema() for validation.
    Returns SchemaComplianceIssue if problems found, None if compliant.
    """
    rule_type = requirement.rule_type.value
    attrs = requirement.attributes
    
    # Filter out internal attributes (prefixed with _)
    public_attrs = {k: v for k, v in attrs.items() if not k.startswith("_")}
    
    # Check if we have a canonical schema for this rule type
    if rule_type not in CANONICAL_SCHEMAS:
        return None  # No schema to validate against
    
    # Validate against canonical schema
    result = validate_canonical_schema(rule_type, public_attrs)
    
    if result.is_valid:
        return None
    
    # Parse errors into missing and invalid fields
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    
    for error in result.errors:
        if error.startswith("Missing:"):
            field = error.replace("Missing:", "").strip()
            missing_fields.append(field)
        else:
            invalid_fields.append(error)
    
    # Add warnings as invalid fields (less severe)
    for warning in result.warnings:
        if warning not in invalid_fields:
            invalid_fields.append(warning)
    
    # Determine severity
    if len(missing_fields) >= 2:
        severity = "high"
    elif len(missing_fields) == 1:
        severity = "medium"
    else:
        severity = "low"
    
    return SchemaComplianceIssue(
        req_id=requirement.requirement_id,
        rule_type=rule_type,
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
        severity=severity,
    )
