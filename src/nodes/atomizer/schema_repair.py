"""Schema repair utilities for the Requirement Atomizer.

Handles auto-repair of common schema violations and inference of
missing fields like applicable_fields and data_source.
"""
from __future__ import annotations

from typing import Any

import structlog

from models.requirements import RegulatoryRequirement

logger = structlog.get_logger(__name__)


# Field inference patterns
FIELD_PATTERNS = {
    "account number": "account_number",
    "account_number": "account_number",
    "ssn": "ssn",
    "social security": "ssn",
    "tax id": "tax_id",
    "tin": "tax_id",
    "balance": "balance",
    "name": "account_holder_name",
    "address": "address",
    "email": "email",
    "phone": "phone_number",
    "date of birth": "date_of_birth",
    "dob": "date_of_birth",
    "ownership": "ownership_type",
    "beneficiary": "beneficiary_name",
    "signature": "signature",
}

# Data source inference patterns
SOURCE_PATTERNS = {
    "core banking": "core_banking_system",
    "cif": "customer_information_file",
    "deposit system": "deposit_system",
    "loan system": "loan_system",
    "account master": "account_master",
    "customer master": "customer_master",
    "signature card": "signature_card_system",
}

# Default data sources by rule type
TYPE_TO_SOURCE = {
    "data_quality_threshold": "core_banking_system.accounts",
    "ownership_category": "account_master.ownership",
    "beneficial_ownership_threshold": "customer_information_file.beneficial_owners",
    "documentation_requirement": "document_management_system",
    "update_requirement": "core_banking_system.accounts",
    "update_timeline": "core_banking_system.accounts",
}


class SchemaRepairer:
    """Repairs schema violations in extracted requirements."""

    def attempt_repair(
        self, req: RegulatoryRequirement, missing_fields: list[str]
    ) -> tuple[RegulatoryRequirement, bool]:
        """Attempt auto-repair of common schema violations.
        
        Returns: (repaired_requirement, repair_was_applied)
        """
        repair_applied = False
        attrs = req.attributes.copy()
        rule_type = req.rule_type.value
        desc_lower = req.rule_description.lower()
        
        for field in missing_fields:
            repaired = self._repair_field(field, desc_lower, attrs, req)
            if repaired:
                repair_applied = True
        
        # CF-5: Infer applicable_fields if not present
        if "applicable_fields" not in attrs or attrs.get("applicable_fields") is None:
            inferred_fields = self._infer_applicable_fields(desc_lower)
            if inferred_fields:
                attrs["applicable_fields"] = inferred_fields
                attrs["_applicable_fields_source"] = "inferred"
                repair_applied = True
        
        # CF-6: Infer data_source if not present
        if "data_source" not in attrs or attrs.get("data_source") is None:
            inferred_source = self._infer_data_source(desc_lower, rule_type)
            if inferred_source:
                attrs["data_source"] = inferred_source
                attrs["_data_source_source"] = "inferred"
                repair_applied = True
        
        if repair_applied:
            req.attributes = attrs
        
        return req, repair_applied

    def _repair_field(
        self,
        field: str,
        desc_lower: str,
        attrs: dict[str, Any],
        req: RegulatoryRequirement,
    ) -> bool:
        """Attempt to repair a single missing field. Returns True if repaired."""
        # Skip type errors - can't auto-repair those
        if "(wrong type)" in field:
            return False
        
        if field == "applies_to":
            if "account" in desc_lower:
                attrs["applies_to"] = "accounts"
            elif "record" in desc_lower:
                attrs["applies_to"] = "records"
            elif "document" in desc_lower:
                attrs["applies_to"] = "documents"
            elif "transaction" in desc_lower:
                attrs["applies_to"] = "transactions"
            else:
                attrs["applies_to"] = "relevant data"
            return True
            
        elif field == "threshold_direction":
            if any(kw in desc_lower for kw in ["at least", "minimum", "greater", "exceed"]):
                attrs["threshold_direction"] = "gte"
            elif any(kw in desc_lower for kw in ["at most", "maximum", "less", "under", "within"]):
                attrs["threshold_direction"] = "lte"
            else:
                attrs["threshold_direction"] = "eq"
            return True
            
        elif field == "threshold_unit":
            if "%" in desc_lower or "percent" in desc_lower:
                attrs["threshold_unit"] = "%"
            elif "day" in desc_lower:
                attrs["threshold_unit"] = "days"
            elif "hour" in desc_lower:
                attrs["threshold_unit"] = "hours"
            elif "record" in desc_lower:
                attrs["threshold_unit"] = "records"
            else:
                attrs["threshold_unit"] = "units"
            return True
            
        elif field == "metric":
            if "accuracy" in desc_lower:
                attrs["metric"] = "accuracy_rate"
            elif "completeness" in desc_lower:
                attrs["metric"] = "completeness_rate"
            elif "error" in desc_lower:
                attrs["metric"] = "error_rate"
            elif "compliance" in desc_lower:
                attrs["metric"] = "compliance_rate"
            else:
                attrs["metric"] = "quality_score"
            return True
            
        elif field == "requirement":
            attrs["requirement"] = req.rule_description
            return True
            
        elif field == "ownership_type":
            if "individual" in desc_lower:
                attrs["ownership_type"] = "individual"
            elif "joint" in desc_lower:
                attrs["ownership_type"] = "joint"
            elif "trust" in desc_lower:
                attrs["ownership_type"] = "trust"
            elif "corporate" in desc_lower or "business" in desc_lower:
                attrs["ownership_type"] = "corporate"
            else:
                attrs["ownership_type"] = "other"
            return True
            
        elif field == "required_data_elements":
            attrs["required_data_elements"] = []
            return True
            
        elif field == "applies_when":
            if "change" in desc_lower:
                attrs["applies_when"] = "on_change"
            elif "new" in desc_lower or "open" in desc_lower:
                attrs["applies_when"] = "on_creation"
            elif "close" in desc_lower:
                attrs["applies_when"] = "on_closure"
            else:
                attrs["applies_when"] = "on_trigger"
            return True
        
        elif field == "control_mechanism":
            # Infer control mechanism from description
            if "unique" in desc_lower or "index" in desc_lower or "constraint" in desc_lower:
                attrs["control_mechanism"] = "database_constraint"
            elif "validation" in desc_lower or "check" in desc_lower:
                attrs["control_mechanism"] = "validation_rule"
            elif "audit" in desc_lower or "log" in desc_lower:
                attrs["control_mechanism"] = "audit_trail"
            elif "encrypt" in desc_lower:
                attrs["control_mechanism"] = "encryption"
            elif "access" in desc_lower or "permission" in desc_lower:
                attrs["control_mechanism"] = "access_control"
            elif "reconcil" in desc_lower:
                attrs["control_mechanism"] = "reconciliation"
            elif "monitor" in desc_lower or "alert" in desc_lower:
                attrs["control_mechanism"] = "monitoring"
            else:
                attrs["control_mechanism"] = "system_control"
            return True
        
        elif field == "threshold_value":
            # FIX C: Coerce timeline string to numeric threshold_value
            # Check if there's a timeline string like "24 hours"
            timeline = attrs.get("timeline", "")
            if timeline:
                numeric_val = self._extract_numeric_from_string(timeline)
                if numeric_val is not None:
                    attrs["threshold_value"] = numeric_val
                    return True
            # Try to extract from description
            numeric_val = self._extract_numeric_from_string(desc_lower)
            if numeric_val is not None:
                attrs["threshold_value"] = numeric_val
                return True
            return False
        
        elif field == "control_type":
            # Infer control type from description
            if any(kw in desc_lower for kw in ["prevent", "block", "restrict", "enforce", "require"]):
                attrs["control_type"] = "Preventive"
            elif any(kw in desc_lower for kw in ["detect", "monitor", "audit", "alert", "identify", "flag"]):
                attrs["control_type"] = "Detective"
            elif any(kw in desc_lower for kw in ["correct", "fix", "remediat", "restore", "recover"]):
                attrs["control_type"] = "Corrective"
            else:
                attrs["control_type"] = "Preventive"  # Default
            return True
        
        return False
    
    def _extract_numeric_from_string(self, text: str) -> int | float | None:
        """Extract numeric value from a string like '24 hours' or 'within 30 days'."""
        import re
        # Match patterns like "24", "24.5", "24 hours", "within 30 days"
        match = re.search(r'(\d+\.?\d*)\s*(?:hours?|days?|months?|years?|%|percent)?', text.lower())
        if match:
            val_str = match.group(1)
            try:
                if '.' in val_str:
                    return float(val_str)
                return int(val_str)
            except ValueError:
                pass
        return None

    def _infer_applicable_fields(self, desc_lower: str) -> list[str] | None:
        """Infer applicable fields from description keywords."""
        found_fields = []
        for pattern, field_name in FIELD_PATTERNS.items():
            if pattern in desc_lower and field_name not in found_fields:
                found_fields.append(field_name)
        
        return found_fields if found_fields else None

    def _infer_data_source(self, desc_lower: str, rule_type: str) -> str | None:
        """Infer data source from description and rule type."""
        # Check for explicit system references
        for pattern, source in SOURCE_PATTERNS.items():
            if pattern in desc_lower:
                return source
        
        # Default based on rule type
        return TYPE_TO_SOURCE.get(rule_type)
