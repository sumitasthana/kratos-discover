"""Control operationalization metadata for regulatory requirements.

Implements the 8 critical metadata fields specified in windsurf_agent_feedback.md:
1. control_objective - Business outcome this achieves
2. risk_addressed - Enterprise risk(s) mitigated
3. test_procedure - Step-by-step test instructions
4. control_owner - Accountable role/title
5. automated - Automation status (true/false/hybrid)
6. evidence_type - Artifacts proving compliance
7. system_mapping - Systems implementing the control
8. exception_threshold - Escalation rules for breaches
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AutomationStatus(str, Enum):
    """Control automation status."""
    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"


class RiskCategory(str, Enum):
    """Enterprise risk taxonomy."""
    DATA_INTEGRITY = "R001_data_integrity"
    REGULATORY_COMPLIANCE = "R002_regulatory_compliance"
    OPERATIONAL = "R003_operational"
    SYSTEM_AVAILABILITY = "R004_system_availability"
    VENDOR_THIRD_PARTY = "R005_vendor_third_party"
    CHANGE_MANAGEMENT = "R006_change_management"


# Canonical control owners by domain
CANONICAL_OWNERS = {
    "compliance": "Chief Compliance Officer",
    "finance": "VP Finance Operations",
    "technology": "Chief Technology Officer",
    "risk": "VP Risk Management",
    "audit": "Director, Internal Audit",
    "operations": "VP Operations",
    "data": "Manager, Data Governance",
}

# Canonical systems
CANONICAL_SYSTEMS = [
    "account_opening_system",
    "core_banking_platform",
    "deposit_insurance_file_system",
    "compliance_reporting_system",
    "general_ledger",
    "tax_id_validation_service",
    "external_data_provider",
    "change_control_system",
    "business_intelligence_platform",
]

# Evidence types by control category
EVIDENCE_TYPES = {
    "data_quality_threshold": [
        "Reconciliation report (signed, dated)",
        "System data quality report",
        "Exception log with resolution",
    ],
    "update_timeline": [
        "Remediation tracking log",
        "SLA compliance report",
        "Escalation email chain",
    ],
    "documentation_requirement": [
        "Signed certification document",
        "Audit trail/approval log",
        "Document retention record",
    ],
    "update_requirement": [
        "Update completion log",
        "System change record",
        "Approval workflow evidence",
    ],
    "beneficial_ownership_threshold": [
        "Beneficial owner identification form",
        "CIP/KYC documentation",
        "Verification confirmation",
    ],
    "ownership_category": [
        "Account classification report",
        "Ownership verification documentation",
        "Sampling workpaper",
    ],
}


@dataclass
class ControlMetadata:
    """Operationalization metadata for a regulatory requirement."""
    control_objective: str = ""
    risk_addressed: list[str] = field(default_factory=list)
    test_procedure: str = ""
    control_owner: str = ""
    automated: str = "manual"  # automated, manual, hybrid
    evidence_type: list[str] = field(default_factory=list)
    system_mapping: list[str] = field(default_factory=list)
    exception_threshold: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "control_objective": self.control_objective,
            "risk_addressed": self.risk_addressed,
            "test_procedure": self.test_procedure,
            "control_owner": self.control_owner,
            "automated": self.automated,
            "evidence_type": self.evidence_type,
            "system_mapping": self.system_mapping,
            "exception_threshold": self.exception_threshold,
        }
    
    def is_complete(self) -> bool:
        """Check if all required metadata fields are populated."""
        return bool(
            self.control_objective and
            self.risk_addressed and
            self.test_procedure and
            self.control_owner and
            self.automated and
            self.evidence_type
        )


@dataclass
class ExceptionTier:
    """Exception escalation tier."""
    condition: str
    action: str
    sla_remediation: str = ""


def infer_control_objective(rule_type: str, rule_description: str, attributes: dict) -> str:
    """Infer control objective from rule type and description."""
    objectives = {
        "data_quality_threshold": (
            "Ensure {applies_to} data meets quality standards to support "
            "FDIC deposit insurance calculations and regulatory compliance."
        ),
        "update_timeline": (
            "Ensure timely remediation of {applies_to} issues within regulatory "
            "timeframes to maintain compliance and data integrity."
        ),
        "documentation_requirement": (
            "Maintain required documentation for {applies_to} to support "
            "regulatory examination and audit requirements."
        ),
        "update_requirement": (
            "Ensure {applies_to} data is updated per regulatory requirements "
            "to maintain accurate recordkeeping."
        ),
        "beneficial_ownership_threshold": (
            "Identify and verify beneficial owners meeting ownership thresholds "
            "to comply with CIP/KYC and FDIC Part 370 requirements."
        ),
        "ownership_category": (
            "Accurately classify account ownership categories to ensure "
            "correct FDIC deposit insurance coverage determination."
        ),
    }
    
    template = objectives.get(rule_type, "Ensure compliance with regulatory requirements.")
    applies_to = attributes.get("applies_to", "relevant data")
    return template.format(applies_to=applies_to)


def infer_risks(rule_type: str, rule_description: str) -> list[str]:
    """Infer risk categories from rule type and description."""
    risk_mapping = {
        "data_quality_threshold": [
            RiskCategory.DATA_INTEGRITY.value,
            RiskCategory.REGULATORY_COMPLIANCE.value,
        ],
        "update_timeline": [
            RiskCategory.OPERATIONAL.value,
            RiskCategory.REGULATORY_COMPLIANCE.value,
        ],
        "documentation_requirement": [
            RiskCategory.REGULATORY_COMPLIANCE.value,
            RiskCategory.OPERATIONAL.value,
        ],
        "update_requirement": [
            RiskCategory.DATA_INTEGRITY.value,
            RiskCategory.REGULATORY_COMPLIANCE.value,
        ],
        "beneficial_ownership_threshold": [
            RiskCategory.REGULATORY_COMPLIANCE.value,
            RiskCategory.DATA_INTEGRITY.value,
        ],
        "ownership_category": [
            RiskCategory.DATA_INTEGRITY.value,
            RiskCategory.REGULATORY_COMPLIANCE.value,
        ],
    }
    
    # Check for system-related keywords
    desc_lower = rule_description.lower()
    risks = risk_mapping.get(rule_type, [RiskCategory.REGULATORY_COMPLIANCE.value])
    
    if any(kw in desc_lower for kw in ["system", "availability", "uptime"]):
        if RiskCategory.SYSTEM_AVAILABILITY.value not in risks:
            risks = risks + [RiskCategory.SYSTEM_AVAILABILITY.value]
    
    if any(kw in desc_lower for kw in ["vendor", "third-party", "external"]):
        if RiskCategory.VENDOR_THIRD_PARTY.value not in risks:
            risks = risks + [RiskCategory.VENDOR_THIRD_PARTY.value]
    
    return risks[:3]  # Max 3 risks


def infer_test_procedure(
    rule_type: str,
    rule_description: str,
    attributes: dict,
) -> str:
    """Generate test procedure based on rule type and attributes."""
    applies_to = attributes.get("applies_to", "relevant records")
    threshold = attributes.get("threshold_value", attributes.get("timeline_value", ""))
    unit = attributes.get("threshold_unit", attributes.get("timeline_unit", ""))
    
    procedures = {
        "data_quality_threshold": f"""1. Extract population: All {applies_to} as of test date.
2. Sample methodology: Random sample of 100 records (95% confidence, 5% error).
3. Verification: For each record, validate data quality against source.
4. Acceptance: Errors must be within {threshold}{unit} threshold.
5. Escalation: If threshold exceeded, escalate to control owner.
6. Evidence: Data quality report with sample details and exceptions.""",

        "update_timeline": f"""1. Identify trigger events for {applies_to}.
2. Extract all items requiring update within test period.
3. Verify each item was updated within {threshold} {unit} of trigger.
4. Document any timeline breaches with root cause.
5. Escalation: Report breaches to control owner.
6. Evidence: Timeline compliance report with dates and exceptions.""",

        "documentation_requirement": f"""1. Identify all {applies_to} requiring documentation.
2. Sample 50 records for documentation completeness review.
3. Verify required documents are present and properly signed.
4. Check document retention compliance.
5. Evidence: Documentation checklist with sample results.""",

        "update_requirement": f"""1. Identify all {applies_to} subject to update requirement.
2. Verify updates were performed per required frequency.
3. Validate update accuracy against source data.
4. Document any update failures or delays.
5. Evidence: Update log with completion timestamps.""",

        "beneficial_ownership_threshold": f"""1. Extract all accounts meeting beneficial ownership criteria.
2. Verify beneficial owner identification for each account.
3. Confirm ownership percentage calculations are accurate.
4. Validate CIP/KYC documentation is complete.
5. Evidence: Beneficial ownership verification report.""",

        "ownership_category": f"""1. Extract sample of 500 accounts across ownership types.
2. Verify ownership category matches legal documentation.
3. Confirm FDIC insurance coverage is correctly calculated.
4. Document any misclassifications.
5. Evidence: Ownership classification sampling workpaper.""",
    }
    
    return procedures.get(rule_type, "1. Review requirement.\n2. Verify compliance.\n3. Document results.")


def infer_control_owner(rule_type: str, attributes: dict) -> str:
    """Infer control owner from rule type and attributes."""
    # Check for explicit responsible party
    responsible = attributes.get("responsible_party", "")
    if responsible:
        return responsible
    
    owner_mapping = {
        "data_quality_threshold": "Manager, Data Governance",
        "update_timeline": "VP Compliance Operations",
        "documentation_requirement": "Manager, Deposit Compliance",
        "update_requirement": "VP Operations",
        "beneficial_ownership_threshold": "Chief Compliance Officer",
        "ownership_category": "Manager, Deposit Compliance",
    }
    
    return owner_mapping.get(rule_type, "Chief Compliance Officer")


def infer_automation_status(rule_type: str, rule_description: str) -> str:
    """Infer automation status from rule description."""
    desc_lower = rule_description.lower()
    
    # Keywords suggesting automation
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


def infer_systems(rule_type: str, rule_description: str) -> list[str]:
    """Infer system mapping from rule description."""
    desc_lower = rule_description.lower()
    systems = []
    
    system_keywords = {
        "account_opening_system": ["account opening", "new account", "onboarding"],
        "core_banking_platform": ["core system", "deposit", "balance", "account record"],
        "deposit_insurance_file_system": ["fdic", "deposit insurance", "part 370"],
        "compliance_reporting_system": ["compliance", "reporting", "regulatory"],
        "general_ledger": ["gl", "ledger", "reconcil"],
        "tax_id_validation_service": ["tin", "ssn", "ein", "tax id"],
    }
    
    for system, keywords in system_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            systems.append(system)
    
    if not systems:
        systems = ["core_banking_platform"]
    
    return systems[:3]


def infer_exception_threshold(
    rule_type: str,
    attributes: dict,
) -> dict[str, Any]:
    """Generate exception threshold tiers."""
    threshold = attributes.get("threshold_value", 99)
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
        timeline = attributes.get("timeline_value", 30)
        return {
            "breach": {
                "condition": f"Update not completed within {timeline} {unit}",
                "action": "Escalate to control owner; initiate remediation",
                "sla_remediation": f"{timeline // 2} {unit}",
            },
        }
    
    return {}


def enrich_requirement_metadata(
    rule_type: str,
    rule_description: str,
    attributes: dict,
) -> ControlMetadata:
    """
    Generate complete control metadata for a requirement.
    
    This function infers all 8 metadata fields based on the rule type,
    description, and attributes.
    """
    return ControlMetadata(
        control_objective=infer_control_objective(rule_type, rule_description, attributes),
        risk_addressed=infer_risks(rule_type, rule_description),
        test_procedure=infer_test_procedure(rule_type, rule_description, attributes),
        control_owner=infer_control_owner(rule_type, attributes),
        automated=infer_automation_status(rule_type, rule_description),
        evidence_type=infer_evidence_types(rule_type),
        system_mapping=infer_systems(rule_type, rule_description),
        exception_threshold=infer_exception_threshold(rule_type, attributes),
    )
