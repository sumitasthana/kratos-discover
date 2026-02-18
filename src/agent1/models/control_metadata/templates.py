"""Template dictionaries for control metadata inference.

Contains all the static template mappings used by inference functions.
"""
from __future__ import annotations

from enum import Enum


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

# Control objective templates
CONTROL_OBJECTIVE_TEMPLATES = {
    "data_quality_threshold": (
        "Ensure {applies_to} meets quality standards to support "
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
        "Ensure {applies_to} is updated per regulatory requirements "
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

# Risk mapping by rule type
RISK_MAPPING = {
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

# Control owner mapping
OWNER_MAPPING = {
    "data_quality_threshold": "Manager, Data Governance",
    "update_timeline": "VP Compliance Operations",
    "documentation_requirement": "Manager, Deposit Compliance",
    "update_requirement": "VP Operations",
    "beneficial_ownership_threshold": "Chief Compliance Officer",
    "ownership_category": "Manager, Deposit Compliance",
}

# System keyword mapping
SYSTEM_KEYWORDS = {
    "account_opening_system": ["account opening", "new account", "onboarding"],
    "core_banking_platform": ["core system", "deposit", "balance", "account record"],
    "deposit_insurance_file_system": ["fdic", "deposit insurance", "part 370"],
    "compliance_reporting_system": ["compliance", "reporting", "regulatory"],
    "general_ledger": ["gl", "ledger", "reconcil"],
    "tax_id_validation_service": ["tin", "ssn", "ein", "tax id"],
}

# CF-10: Test procedure templates by control_type × measurement_type
TEST_PROCEDURE_MATRIX: dict[tuple[str, str], str] = {
    # Data quality controls
    ("data_quality", "quantitative"): """1. Extract population: All {applies_to} as of test date.
2. Sample methodology: Stratified sample based on risk tier (high-risk: 100%, medium: 50 records, low: 25 records).
3. Verification: For each record, validate against authoritative source.
4. Acceptance: Error rate must be within {threshold}{unit} threshold.
5. Escalation: If threshold exceeded, escalate to control owner within 24 hours.
6. Evidence: Data quality report with sample details, error breakdown, and exceptions.""",

    ("data_quality", "qualitative"): """1. Identify all {applies_to} requiring quality review.
2. Sample 50 records using risk-based selection.
3. Review each record against quality criteria checklist.
4. Document deficiencies with severity classification.
5. Evidence: Quality review workpaper with findings summary.""",

    # Timeliness controls
    ("timeliness", "timeline"): """1. Identify trigger events for {applies_to} within test period.
2. Extract all items with trigger dates and completion dates.
3. Calculate elapsed time for each item.
4. Verify completion within {threshold} {unit} of trigger.
5. Document breaches with root cause analysis.
6. Evidence: Timeline compliance report with dates, durations, and exceptions.""",

    ("timeliness", "quantitative"): """1. Extract all {applies_to} with update requirements.
2. Calculate update frequency compliance rate.
3. Verify rate meets {threshold}{unit} threshold.
4. Document any frequency violations.
5. Evidence: Update frequency analysis with compliance metrics.""",

    # Documentation controls
    ("documentation", "qualitative"): """1. Identify all {applies_to} requiring documentation.
2. Sample 50 records for documentation completeness review.
3. Verify required documents are present, properly signed, and dated.
4. Check document retention compliance against policy.
5. Evidence: Documentation checklist with sample results and gaps identified.""",

    # Classification controls
    ("classification", "qualitative"): """1. Extract sample of 100 {applies_to} across classification types.
2. Verify classification matches supporting documentation.
3. Confirm downstream calculations (e.g., insurance coverage) are correct.
4. Document any misclassifications with impact assessment.
5. Evidence: Classification verification workpaper with accuracy rate.""",

    ("classification", "quantitative"): """1. Extract all {applies_to} meeting threshold criteria ({threshold}{unit}).
2. Verify identification and documentation for each.
3. Confirm percentage/amount calculations are accurate.
4. Validate supporting CIP/KYC documentation is complete.
5. Evidence: Threshold verification report with compliance rate.""",

    # System availability controls
    ("system_availability", "quantitative"): """1. Extract system availability metrics for test period.
2. Calculate uptime percentage against {threshold}{unit} SLA.
3. Review incident logs for any outages or degradations.
4. Verify incident response met escalation requirements.
5. Evidence: System availability report with uptime metrics and incident summary.""",

    ("system_availability", "timeline"): """1. Identify system events requiring response within {threshold} {unit}.
2. Extract event timestamps and resolution timestamps.
3. Calculate response/resolution times for each event.
4. Document any SLA breaches with root cause.
5. Evidence: Incident response timeline report.""",
}

# Default test procedure fallback
DEFAULT_TEST_PROCEDURE = """1. Review {applies_to} against requirement criteria.
2. Sample records using risk-based methodology.
3. Verify compliance with documented standards.
4. Document any exceptions or deficiencies.
5. Evidence: Compliance verification workpaper."""

# Control type inference mapping
TYPE_TO_CONTROL = {
    "data_quality_threshold": "data_quality",
    "update_timeline": "timeliness",
    "documentation_requirement": "documentation",
    "update_requirement": "timeliness",
    "beneficial_ownership_threshold": "classification",
    "ownership_category": "classification",
}
