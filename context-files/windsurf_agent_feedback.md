# Windsurf Requirement Atomizer Agent — Output Feedback & Remediation Prompts

**Assessment Date:** 2026-02-15  
**Input:** National Bank Archer GRC export  
**Output:** 47 atomized requirements  
**Overall Quality:** Passable, but critical gaps block operationalization.

---

## EXECUTIVE SUMMARY

| Issue | Severity | Impact | Remediation |
|-------|----------|--------|-------------|
| **Confidence scores frozen at 0.60** | 🔴 Critical | 40/47 reqs unvalidated; gating impossible | Implement confidence scorer with features |
| **Schema heterogeneity** (5–13 attrs per type) | 🔴 Critical | Cannot enforce consistency; query hard | Lock canonical schemas; revalidate all reqs |
| **100% missing critical metadata** | 🔴 Critical | Untestable, unowned, unlinked to risk/systems | Add 8 required fields per control |
| **32/47 requirements inferred (not grounded)** | 🟠 High | Audit risk; unclear provenance | Require >85% grounding score; flag paraphrases |
| **Attribute variability within rule types** | 🟠 High | 21 DQ thresholds with 7 different attr combos | Enforce strict schema per type |
| **No exception thresholds defined** | 🟠 High | Unclear what constitutes breach/escalation | Add explicit exception tier logic |
| **No control objective or risk link** | 🟠 High | Cannot map to risk taxonomy; audit trail broken | Mandatory `control_objective` + `risk_addressed` |
| **28% vague action verbs** | 🟡 Medium | Ambiguous operationalization; test design hard | Replace generic verbs with specific actions |

---

## DETAILED FINDINGS

### 1. CONFIDENCE SCORE CRISIS (Critical)

#### Problem
- **40/47 requirements stuck at 0.60** (default?)
- **Only 1/47 reaches 0.92** (beneficial ownership threshold with exact quantification)
- **No variation within rule types** — all data_quality_thresholds = 0.60
- **Unclear scoring logic** — no rationale provided for why 0.92 ≠ 0.60

#### Root Cause Analysis
**Hypothesis A (Most Likely):** Confidence scorer is hardcoded default, not computed.
```python
# Current (broken)
confidence = 0.6  # Default for all non-beneficial_ownership_threshold

# Should be
confidence = score_grounding(description, grounded_text) + 
             score_completeness(attributes) + 
             score_specificity(threshold_value, units)
```

**Hypothesis B:** Scorer exists but only triggers for certain rule types.
- `beneficial_ownership_threshold` has explicit scoring (0.92).
- Others default to 0.60.

#### Evidence
1. **Identical scores within rule type:**
   - data_quality_threshold: 21/21 = 0.60
   - documentation_requirement: 8/8 = 0.60
   - update_timeline: 11/11 = 0.60

2. **Only exception:**
   - beneficial_ownership_threshold: 1/1 = 0.92 (explicit "25%" quantification)

3. **No confidence rationale** in output (e.g., no field explaining why this req got 0.60).

#### Impact
- **Cannot prioritize rework.** Which 10 requirements most need human review? Unknown.
- **Cannot gate controls.** Should we require confidence >0.75 to accept? Current score cannot support policy.
- **False confidence in output.** Users may trust low-quality extractions.

#### Remediation Prompt for Windsurf

```
TASK: Implement Confidence Scorer for Requirement Atomizer Agent

CURRENT STATE:
- 40/47 requirements at hardcoded 0.60 confidence
- Only 1/47 at 0.92 (beneficial_ownership_threshold)
- No scoring logic visible; no confidence rationale provided

REQUIRED OUTPUTS:
1. Confidence score: [0.0, 1.0] for each requirement
2. Confidence rationale: String explaining why score is X.Y
3. Feature breakdown: JSON listing component scores

SCORING FEATURES (explicit weights):
Feature                          | Weight | Logic
---------------------------------|--------|-------------------------------------------------------------
Grounding match (word overlap)   | 0.30   | >85%→+0.30, 60-85%→+0.20, <60%→+0.10
Completeness (required attrs)    | 0.20   | (actual_attrs / required_attrs) * 0.20
Quantification specificity       | 0.20   | Has threshold value (+0.10) + unit (+0.05) + 
                                 |        | exceptions (+0.05)
Schema compliance                | 0.15   | All attrs match canonical schema → +0.15
Coherence (grounded ≠ desc)      | 0.10   | No contradictions, clear paraphrase → +0.10
Domain-specific signals          | 0.05   | Regulatory keywords (FDIC, Part 370) → +0.05

FAILURE MODES TO DETECT:
- Paraphrase without grounding (score < 0.50)
- Incomplete attributes for rule type (score -= 0.15)
- Unquantified metrics in threshold requirement (score -= 0.20)
- Self-contradictory description ≠ grounded_in (flag red, score = 0.0)

CANONICAL REQUIREMENTS:
- Confidence scores must NOT be uniform within rule type (variance > 0.1)
- Minimum 1 explanation per requirement (30–50 chars)
- Score distribution: mean 0.70–0.80, stdev > 0.15

VALIDATION:
- Manually audit 10 sample requirements (2 per rule type)
- Compare agent score vs. human assessment
- If r < 0.8, retrain features or thresholds

OUTPUT SCHEMA:
{
  "requirement_id": "R-DQ-a9dbdd",
  "confidence": 0.65,
  "confidence_rationale": "Grounding match 85% (↑0.25), attributes complete (↑0.20), quantified threshold (↑0.20), but inference in description (↓0.10). Paraphrase quality good but not exact.",
  "confidence_features": {
    "grounding_match": 0.25,
    "completeness": 0.20,
    "quantification": 0.20,
    "schema_compliance": 0.10,
    "coherence": 0.10,
    "domain_signals": 0.00
  }
}
```

---

### 2. ATTRIBUTE SCHEMA HETEROGENEITY (Critical)

#### Problem
Within single rule type, attributes vary wildly:

**data_quality_threshold (21 requirements):**
```
Sample 1:  {threshold_type, threshold_value, measurement_frequency}
Sample 2:  {threshold_value, threshold_unit, metric_type, applies_to}
Sample 3:  {threshold_value, threshold_unit, metric_type, applies_to}
...
Union: 7 different attributes across 21 instances
```

**update_timeline (11 requirements):**
```
Sample 1: {timeline_value, timeline_type, trigger_event}
Sample 2: {timeline_value, timeline_unit, trigger_event, coverage_requirement}
Sample 3: {priority_levels (list), timeline_unit, timeline_value, trigger_event}
...
Union: 13 different attributes
```

#### Root Cause
Agent extracts attributes dynamically from source text without enforcing schema. Result: Each requirement has different attribute set, even when rule type is identical.

#### Impact
1. **Cannot build queries:** "Find all data quality thresholds > 99%"
   - Some have `threshold_value` as string ("99.5%"), others as numeric (99.5).
   - Some have `applies_to`, others missing.
   - Query logic must handle 7 different schemas.

2. **Cannot generate tests:** Template-based test generation assumes fixed attributes.
   - DQ threshold template expects: `{metric_type, threshold_value, threshold_unit, measurement_frequency, exception_threshold}`.
   - Actual: 3–5 attributes, varying by requirement.
   - Result: Custom handling per requirement (unmaintainable).

3. **Audit trail fragile:** If you query "all 99.5% accuracy requirements", you miss those stored as "99.5" (numeric) or "99.5% completeness" (different metric_type).

#### Evidence
```
R-DQ-66a485 (accuracy): {threshold_value: 99.5, threshold_unit: "percent", 
                          metric_type: "accuracy", applies_to: "deposit account records"}

R-DQ-a9dbdd (completeness): {threshold_value: "100%", threshold_type: "completeness", 
                              measurement_frequency: "continuous"}

→ Same rule type, 0% attribute overlap in structure
```

#### Remediation Prompt for Windsurf

```
TASK: Enforce Canonical Control Schemas

CURRENT STATE:
- 21 data_quality_threshold requirements with 7 different attribute patterns
- 11 update_timeline requirements with 13 different attributes
- No schema validation; attributes extracted opportunistically

REQUIRED OUTPUTS:
1. Rewrite all 47 requirements to match canonical schemas (below)
2. Validate: 100% compliance with JSON Schema
3. Flag & fix: Any requirement not matching schema

CANONICAL SCHEMAS (STRICT):

---
data_quality_threshold:
{
  "rule_type": "data_quality_threshold",
  "metric_type": "ENUM[accuracy | completeness | timeliness | consistency | 
                       uniqueness | availability]",
  "threshold_value": "NUMBER (0–100 or 0–999999 depending on metric)",
  "threshold_unit": "ENUM[percent | count | hours | days | dollars]",
  "applies_to": "STRING (e.g., 'deposit account records', 'core system data')",
  "measurement_frequency": "ENUM[continuous | daily | weekly | monthly | quarterly | 
                                 annual]",
  "exception_threshold": "OPTIONAL NUMBER (% variance before escalation)",
  "applies_to_all_dq_thresholds": true
}

Example (CORRECT):
{
  "metric_type": "accuracy",
  "threshold_value": 99.5,
  "threshold_unit": "percent",
  "applies_to": "deposit account records",
  "measurement_frequency": "continuous",
  "exception_threshold": 0.5
}

---
update_timeline:
{
  "rule_type": "update_timeline",
  "timeline_value": "NUMBER",
  "timeline_unit": "ENUM[hours | days | weeks | months]",
  "trigger_event": "STRING (what event starts the clock)",
  "applies_to": "STRING",
  "priority_levels": "OPTIONAL ARRAY[{priority: STRING, days: NUMBER}]",
  "applies_to_all_timelines": true
}

Example (CORRECT):
{
  "timeline_value": 15,
  "timeline_unit": "days",
  "trigger_event": "critical data remediation issue identified",
  "applies_to": "all deposit account data exceptions",
  "priority_levels": [
    {"priority": "Critical", "days": 15},
    {"priority": "High", "days": 30},
    {"priority": "Medium", "days": 60}
  ]
}

---
documentation_requirement:
{
  "rule_type": "documentation_requirement",
  "document_type": "STRING (e.g., 'certification', 'validation_testing')",
  "required_by": "ENUM[account_opening | quarterly | annual | on_demand | 
                       other]",
  "validation_method": "STRING (e.g., 'senior management review', 'third-party audit')",
  "required_fields": "ARRAY[STRING] (mandatory content)",
  "approval_chain": "OPTIONAL STRING (e.g., 'CCO → Board Risk Committee')",
  "applies_to_all_docs": true
}

---
update_requirement:
{
  "rule_type": "update_requirement",
  "update_frequency": "ENUM[weekly | monthly | quarterly | annual]",
  "responsible_party": "STRING (role or title)",
  "data_elements": "ARRAY[STRING]",
  "applies_to_all_updates": true
}

---
beneficial_ownership_threshold:
{
  "rule_type": "beneficial_ownership_threshold",
  "threshold_value": "NUMBER (ownership % ≥ this triggers requirement)",
  "threshold_unit": "ENUM[percent]",
  "applies_to": "STRING (e.g., 'business accounts')",
  "identification_required": "BOOLEAN"
}

---
ownership_category:
{
  "rule_type": "ownership_category",
  "ownership_type": "STRING (e.g., 'sole proprietor', 'partnership', 'corporation')",
  "scope": "STRING (what accounts/products covered)",
  "responsibility": "STRING (who is accountable)"
}

---

VALIDATION RULES:
1. JSON Schema validation: All 47 requirements must validate without error
2. Enum enforcement: threshold_unit, measurement_frequency, etc. must be from approved list
3. Type enforcement: threshold_value must be NUMBER (not string "99.5%")
4. Required field checks: All mandatory fields present in all requirements

REMEDIATION STEPS:
1. For each requirement not matching canonical schema:
   a. Identify deviations (missing attrs, extra attrs, wrong type)
   b. Extract correct values from source document or rule_description
   c. Rewrite requirement to match schema exactly
   d. Re-validate

EXAMPLES OF FIXES:

BEFORE (Non-compliant):
{
  "requirement_id": "R-DQ-a9dbdd",
  "rule_type": "data_quality_threshold",
  "attributes": {
    "threshold_type": "completeness",
    "threshold_value": "100%",
    "measurement_frequency": "continuous"
  }
}

AFTER (Compliant):
{
  "requirement_id": "R-DQ-a9dbdd",
  "rule_type": "data_quality_threshold",
  "attributes": {
    "metric_type": "completeness",
    "threshold_value": 100,
    "threshold_unit": "percent",
    "applies_to": "mandatory customer data fields at account opening",
    "measurement_frequency": "continuous",
    "exception_threshold": 0  // No tolerance for missing mandatory fields
  }
}

---
BEFORE (Non-compliant):
{
  "requirement_id": "R-TL-aee32f",
  "rule_type": "update_timeline",
  "attributes": {
    "timeline_value": 48,
    "timeline_unit": "hours",
    "trigger_event": "TIN validation",
    "coverage_requirement": "99.8%"  // Wrong attr for this schema
  }
}

AFTER (Compliant):
{
  "requirement_id": "R-TL-aee32f",
  "rule_type": "update_timeline",
  "attributes": {
    "timeline_value": 48,
    "timeline_unit": "hours",
    "trigger_event": "account opening triggering TIN validation requirement",
    "applies_to": "all new accounts requiring tax ID validation"
  }
}

---

VALIDATION OUTPUT:
```json
{
  "validation_summary": {
    "total_requirements": 47,
    "passing_validation": 47,
    "failing_validation": 0,
    "errors": []
  },
  "requirement_validations": [
    {
      "requirement_id": "R-DQ-a9dbdd",
      "rule_type": "data_quality_threshold",
      "validation_status": "PASS",
      "missing_fields": [],
      "extra_fields": [],
      "type_errors": []
    },
    ...
  ]
}
```

DELIVERABLE:
1. Revalidated 47 requirements (JSON)
2. Schema validation report (PASS/FAIL per requirement)
3. Mapping: Requirement ID → Canonical schema + any corrections made
```

---

### 3. 100% MISSING CRITICAL METADATA (Critical)

#### Problem
**8 essential fields missing from ALL 47 requirements:**

| Field | Purpose | Status | Example |
|-------|---------|--------|---------|
| `test_procedure` | How do you actually test this? | ❌ MISSING 47/47 | "Quarterly sample 500 accounts, verify ownership category matches legal docs" |
| `control_objective` | What business outcome does this achieve? | ❌ MISSING 47/47 | "Ensure FDIC deposit insurance recordkeeping accuracy" |
| `risk_addressed` | Which enterprise risk(s)? | ❌ MISSING 47/47 | "Data integrity risk", "Regulatory compliance risk" |
| `control_owner` | Who is accountable? (specific role/person) | ⚠️ PARTIAL | Some mention "Compliance Manager" but not tied to org structure |
| `automated` | Automated or manual? Hybrid? | ❌ MISSING 47/47 | Is "TIN validation via IRS" automated? Yes. Is "ownership sampling" automated? No. |
| `evidence_type` | What artifacts prove compliance? | ❌ MISSING 47/47 | "Reconciliation report signed by VP Finance" |
| `system_mapping` | Which systems implement this? | ❌ MISSING 47/47 | "account_opening_system", "core_banking_platform" |
| `exception_threshold` | What % failure = breach? | ❌ MISSING 47/47 | "If DQ < 99.5%, escalate to VP Compliance" |

#### Root Cause
Atomizer Agent designed to extract **requirements** from GRC document, not **operationalize** them into testable controls. GRC source document may not contain:
- Step-by-step test procedures.
- Explicit risk mappings.
- System architecture details.
- Exception escalation rules.

Result: Agent correctly extracted what's in the source, but output is incomplete for audit/control operations.

#### Impact

**For Auditor:**
- Cannot design test from requirement alone. Must improvise test design.
- No evidence definition. Does "reconciliation workpaper" suffice? Unclear.

**For Compliance Officer:**
- Cannot assign control owner. "Finance" is a department, not a person.
- Cannot monitor. No exception thresholds means: "Is 99.4% accuracy OK? Maybe. Call the CRO."

**For Test Automation:**
- Cannot write test generator. Template-based generators need procedure steps.
- Cannot integrate with systems. No system mapping = manual lookups.

#### Evidence
```json
// Typical requirement output
{
  "requirement_id": "R-DQ-66a485",
  "rule_description": "Deposit account records must maintain 99.5% accuracy standards.",
  "attributes": {
    "threshold_value": 99.5,
    "threshold_unit": "percent",
    "metric_type": "accuracy",
    "applies_to": "deposit account records"
  }
  // Missing everything below:
  // "test_procedure": null,
  // "control_objective": null,
  // "risk_addressed": null,
  // "control_owner": null,
  // "automated": null,
  // "evidence_type": null,
  // "system_mapping": null,
  // "exception_threshold": null
}
```

#### Remediation Prompt for Windsurf

```
TASK: Enrich Requirements with Control Operationalization Metadata

CURRENT STATE:
- 47 requirements extracted from GRC document
- Only rule description + threshold attributes populated
- 8 critical control fields null/missing
- Output untestable, unowned, unlinked to systems

REQUIRED OUTPUTS:
1. All 47 requirements enriched with 8 metadata fields
2. Test procedure: Specific, testable steps (not generic)
3. Risk mapping: Link to risk taxonomy (provided separately)
4. System mapping: Link to banking systems
5. Exception rules: Clear escalation thresholds

---

ENRICHMENT RULES BY FIELD:

1. control_objective (REQUIRED)
   Type: STRING (50–150 chars)
   How to derive:
   - Read rule_description + attributes
   - Restate as business outcome
   - Link to FDIC Part 370 intent (deposit insurance recordkeeping)
   
   Examples:
   Rule: "Deposit account records must maintain 99.5% accuracy standards."
   → Objective: "Ensure deposit records reflect actual customer balances to support 
                 FDIC insurance calculations and regulatory compliance."
   
   Rule: "Account opening system must require completion of all mandatory customer 
          data fields before account activation."
   → Objective: "Prevent incomplete customer identification, ensuring CIP/KYC compliance 
                 and accurate deposit insurance coverage determination."
   
   Rule: "Quarterly sampling of 500 accounts across ownership types to verify correct 
          ownership category assignment."
   → Objective: "Validate that account ownership categories are accurately assigned 
                 per FDIC rules, protecting insurance coverage determinations."

2. risk_addressed (REQUIRED)
   Type: ARRAY[STRING] (risk IDs from canonical risk taxonomy)
   Taxonomy (use as reference):
   - R001: Data Integrity Risk
   - R002: Regulatory Compliance Risk
   - R003: Operational Risk
   - R004: System Availability Risk
   - R005: Vendor/Third-Party Risk
   - R006: Change Management Risk
   
   How to map:
   - Read rule_description
   - Identify which risk(s) would manifest if control failed
   - Select 1–3 from taxonomy
   
   Examples:
   Rule: "99.5% accuracy standards" → [R001, R002] (Data integrity + regulatory)
   Rule: "Account opening completeness" → [R002, R001] (Regulatory + data integrity)
   Rule: "System availability 99.9%" → [R004, R002] (System availability + regulatory)
   Rule: "Third-party data 98% accuracy" → [R005, R001] (Vendor + data integrity)

3. test_procedure (REQUIRED)
   Type: STRING (procedural steps, not template)
   How to write:
   - Use rule_description + attributes to infer test steps
   - Include: Sample, method, acceptance criteria, evidence
   - Be specific (not "verify accuracy" but "compare 100-record sample...")
   - Format: Numbered steps, clear roles, timelines
   
   Examples:
   
   Rule: "Deposit account records must maintain 99.5% accuracy standards."
   Procedure:
   "1. Extract population: All deposit account records as of end-of-month.
    2. Sample methodology: Random sample of 100 accounts (95% confidence, 5% error).
    3. Verification: For each account, compare:
       - Customer-facing statement balance
       - Core system balance (GL)
       - FDIC deposit insurance file data
    4. Acceptance: Errors ≤ 0.5% (≤1 account in 100-account sample).
    5. Escalation: If errors > 0.5%, halt further account origination; escalate to VP Compliance.
    6. Evidence: Reconciliation workpaper (sample selection, balances, exceptions, signed approval)."
   
   Rule: "Account opening system must require completion of all mandatory customer 
          data fields before account activation."
   Procedure:
   "1. System review: Inspect account_opening_system code/configuration.
    2. Test method: Attempt to open account with missing fields (one missing at a time):
       - Missing first name
       - Missing SSN/EIN
       - Missing address
       - Missing beneficial owner info (if business account)
    3. Expected result: System rejects each attempt, displays error message.
    4. Frequency: Quarterly (or after any system change affecting account opening).
    5. Evidence: Test log (date, user, field tested, system response, screenshot).
    6. Owner: QA/Testing team or Compliance."
   
   Rule: "Quarterly sampling of 500 accounts across ownership types to verify correct 
          ownership category assignment."
   Procedure:
   "1. Population: All deposit accounts opened in previous 12 months.
    2. Sample: Stratified random sample of 500 accounts, distributed across:
       - Sole proprietor (min 100)
       - Partnership (min 100)
       - Corporation (min 100)
       - Trust/Estate (min 100)
       - Other (remaining 0–100)
    3. Verification: For each sampled account, compare:
       - Account ownership category recorded in core system
       - Legal ownership documentation on file (account agreement, articles of incorporation, etc.)
       - CIP documentation (beneficial owners if applicable)
    4. Acceptance: 99%+ match rate (500 - 5 = 495 correct).
    5. Escalation: If match < 99%, initiate remediation process (reassign categories, 
                    notify customers if coverage affected).
    6. Evidence: Sampling workpaper (random selection log, account details, category 
                 match matrix, exceptions, Compliance Manager signature)."

4. control_owner (REQUIRED)
   Type: STRING (specific role, not department)
   How to derive:
   - Read attributes.responsible_party (if present)
   - Map to organization structure (roles, not names)
   - Use canonical role list (below)
   
   Canonical Roles (examples):
   - "Chief Compliance Officer" (CCO)
   - "VP Compliance Operations"
   - "Manager, Deposit Compliance"
   - "VP Risk Management"
   - "Chief Technology Officer" (for system-related controls)
   - "VP Finance Operations"
   - "Director, Internal Audit"
   
   Examples:
   Rule: "Finance must reconcile aggregate deposit balances monthly."
   → Owner: "VP Finance Operations"
   
   Rule: "Quarterly sampling of ownership categories."
   → Owner: "Manager, Deposit Compliance" (or "Compliance Manager" if more specific role unknown)
   
   Rule: "Annual file generation testing."
   → Owner: "Chief Technology Officer" (joint with CCO if stated)

5. automated (REQUIRED)
   Type: ENUM[true | false | "hybrid"]
   How to determine:
   - Read rule_description
   - Identify: Can system do this without human intervention?
   - true: Automated entirely (system runs; no human needed except monitoring)
   - false: Manual (human performs all steps)
   - "hybrid": Automated with manual review (e.g., system flags exceptions; human reviews)
   
   Examples:
   Rule: "TIN validation through IRS TIN Matching Program"
   → automated: true (API call to IRS; system processes response)
   
   Rule: "Account opening system must require mandatory fields"
   → automated: true (system enforces; cannot open account without fields)
   
   Rule: "Quarterly sampling of 500 accounts to verify ownership"
   → automated: false (human must select sample, review docs, match categories)
   
   Rule: "Data quality metrics must maintain 98% threshold with alerts"
   → automated: "hybrid" (system calculates metrics & alerts; human investigates exceptions)

6. evidence_type (REQUIRED)
   Type: ARRAY[STRING] (artifact types that prove control effectiveness)
   Canonical artifact types:
   - "Reconciliation report" (signed, dated)
   - "System test log" (screenshots, configuration dump)
   - "Sampling workpaper" (population, sample selection, results, exceptions)
   - "System report" (data export, validation report)
   - "Audit trail/log" (system-generated event log)
   - "Approval email" (CCO/CFO sign-off)
   - "Third-party report" (vendor SLA proof)
   - "Configuration snapshot" (system settings as-of-date)
   - "User access log" (who ran test, when)
   
   How to identify:
   - Infer from test_procedure (what docs does procedure produce?)
   - Ensure audit reviewable (not ephemeral)
   
   Examples:
   Rule: "Deposit accuracy 99.5%"
   → Evidence: ["Reconciliation report (sample of 100 accounts)", 
               "Signed approval from VP Finance",
               "System audit trail (GL posting log)"]
   
   Rule: "Account opening mandatory fields"
   → Evidence: ["System test log (screenshots of failed attempts)",
               "Configuration export (account opening workflow)",
               "QA sign-off email"]

7. system_mapping (REQUIRED)
   Type: ARRAY[STRING] (system/application names)
   How to identify:
   - Read rule_description
   - Extract system names (e.g., "account_opening_system", "core_banking_platform")
   - Use standardized system naming (provided separately)
   
   Canonical Systems (examples):
   - "account_opening_system"
   - "core_banking_platform" (or "core_banking_system")
   - "deposit_insurance_file_system"
   - "compliance_reporting_system"
   - "general_ledger" (or "GL")
   - "tax_id_validation_service"
   - "external_data_provider" (if third-party)
   - "change_control_system"
   - "business_intelligence_platform"
   
   Examples:
   Rule: "Account opening system must require mandatory fields"
   → Systems: ["account_opening_system"]
   
   Rule: "Finance reconciles deposit balances between core and GL"
   → Systems: ["core_banking_platform", "general_ledger"]
   
   Rule: "TIN validation via IRS"
   → Systems: ["account_opening_system", "tax_id_validation_service"]

8. exception_threshold (REQUIRED for quantified rules)
   Type: OBJECT or STRING
   How to define:
   - If rule has threshold (e.g., "99.5% accuracy"), define exception tiers
   - Escalation rule: When < threshold, what happens?
   
   Examples:
   
   Rule: "99.5% accuracy"
   Exception threshold:
   {
     "tier_1_critical": {
       "condition": "accuracy < 99.0%",
       "action": "Halt account origination; escalate to VP Compliance",
       "sla_remediation": "15 days"
     },
     "tier_2_high": {
       "condition": "accuracy 99.0-99.4%",
       "action": "Escalate to Manager Compliance; prepare remediation plan",
       "sla_remediation": "30 days"
     },
     "tier_3_medium": {
       "condition": "accuracy 99.4-99.5%",
       "action": "Log as exception; monitor closely; escalate if persists 2 quarters",
       "sla_remediation": "60 days"
     }
   }
   
   Rule: "System availability 99.9%"
   Exception threshold:
   {
     "condition": "availability < 99.9%",
     "action": "Alert CTO; activate incident response",
     "sla_remediation": "4 hours" (per RTO target)
   }

---

VALIDATION:
- All 47 requirements must have all 8 fields populated
- test_procedure must be specific (minimum 5 steps, not generic)
- evidence_type must be audit-able (not "good record-keeping")
- exception_threshold must be quantifiable or clearly escalation rule

OUTPUT SCHEMA:
```json
{
  "requirement_id": "R-DQ-66a485",
  "rule_type": "data_quality_threshold",
  "rule_description": "Deposit account records must maintain 99.5% accuracy standards.",
  "control_objective": "Ensure deposit records reflect actual customer balances to support FDIC insurance calculations and regulatory compliance.",
  "risk_addressed": ["R001_data_integrity", "R002_regulatory_compliance"],
  "control_owner": "VP Finance Operations",
  "automated": false,
  "test_procedure": "1. Extract population... [full procedural steps] ...",
  "evidence_type": [
    "Reconciliation report (sample of 100 accounts)",
    "Signed approval from VP Finance",
    "System audit trail"
  ],
  "system_mapping": ["core_banking_platform", "general_ledger"],
  "exception_threshold": {
    "tier_1_critical": {...},
    "tier_2_high": {...},
    "tier_3_medium": {...}
  }
}
```

DELIVERABLE:
1. All 47 requirements enriched with 8 metadata fields (JSON)
2. Test procedures (human-readable, testable)
3. System mapping reference (system name → control count)
4. Evidence type checklist (by control type)
```

---

### 4. GROUNDING QUALITY: 32/47 INFERRED, NOT GROUNDED (High)

#### Problem
**Only 1/47 requirement is grounded exactly in source.** Remaining 46 are paraphrased or inferred:

- **Perfect match (>85% word overlap): 1/47 (2%)**
- **Paraphrase (60–85% overlap): 14/47 (30%)**
- **Inference (<60% overlap): 32/47 (68%)**

#### Root Cause
Agent paraphrases or interprets source text rather than preserving original language. This is standard in summarization but creates audit risk:
- "If I paraphrase, who validates the interpretation is correct?"
- "Is this requirement actually in the source, or did the agent add it?"

#### Impact
**Audit Risk:** Regulators may challenge: "Where in the Archer document does it say deposit records must be 99.5% accurate?" If only paraphrased, proof is weaker.

**Traceability:** Cannot pinpoint source sentence without manual re-reading.

#### Evidence
```
Requirement: "Deposit account records must maintain 99.5% accuracy standards."
Grounded in: "National Banking Corporation shall maintain deposit account 
              records meeting 99.5% accuracy standards"

Word overlap: {Deposit, account, records, maintain, 99.5%, accuracy, standards}
              ≈ 100% match! But classified as <60% in analysis?

⚠️ Analysis likely incorrect. Recheck grounding logic.
```

#### Remediation Prompt for Windsurf

```
TASK: Implement Grounding Validator for Requirement Atomizer

CURRENT STATE:
- 32/47 requirements classified as "inferred" (<60% word overlap)
- Grounding classification logic unclear or overly harsh
- No grounding score provided per requirement
- Cannot identify which extractions need human review

REQUIRED OUTPUTS:
1. Grounding score: [0.0, 1.0] per requirement (word overlap + semantic match)
2. Grounding classification: EXACT | PARAPHRASE | INFERENCE
3. Grounding evidence: List of matched/unmatched phrases
4. Flag paraphrases as distinct from exact extractions

---

GROUNDING SCORING:

Feature                          | Weight | Logic
---------------------------------|--------|-------------------------------------------------------------
Lexical overlap (word-level)     | 0.40   | Jaccard similarity(description_words, grounded_words)
Phrase overlap (multi-word)      | 0.30   | Contiguous phrase match in source (≥3 consecutive words)
Semantic consistency             | 0.20   | No contradictions; paraphrase is semantically equivalent
Source text proximity            | 0.10   | If exact phrase found in source → +0.10

GROUNDING CLASSIFICATION:

Score        | Classification | Action
-------------|------------------|--------------------------------------------------
> 0.85       | EXACT            | Original language preserved; high confidence
0.60 - 0.85  | PARAPHRASE       | Rephrased but meaning intact; medium confidence
< 0.60       | INFERENCE        | Interpreted/constructed; low confidence; flag red

IMPLEMENTATION:

For each requirement:
1. Extract requirement_id, rule_description, grounded_in, source_chunk_id
2. Compute word overlap:
   description_words = set(rule_description.lower().split())
   source_words = set(grounded_in.lower().split())
   jaccard = len(description_words & source_words) / len(description_words | source_words)
   → Contributes 0.40 * jaccard to score

3. Find contiguous phrases (3+ consecutive words) from grounded_in in description
   → Each phrase match contributes 0.30 / num_phrases
   
4. Check for semantic contradictions (e.g., "must NOT" vs "must")
   → If contradiction, subtract 0.20
   
5. If source text hash matches, add 0.10

6. Final score = sum of contributions, capped at 1.0

EXAMPLE:

Requirement ID: R-DQ-66a485
Description: "Deposit account records must maintain 99.5% accuracy standards."
Grounded in: "National Banking Corporation shall maintain deposit account records 
              meeting 99.5% accuracy standards"

Analysis:
- Word overlap:
  description: {deposit, account, records, must, maintain, 99.5%, accuracy, standards}
  grounded:    {national, banking, corporation, shall, maintain, deposit, account, 
                records, meeting, 99.5%, accuracy, standards}
  intersection: {deposit, account, records, maintain, 99.5%, accuracy, standards} = 7
  union:        {all 19 unique words} = 19
  jaccard = 7/19 = 0.368 → 0.40 * 0.368 = 0.147

- Phrase overlap (≥3 consecutive words):
  Found: "deposit account records" (exact)
  Found: "99.5% accuracy standards" (exact)
  2 exact phrases → 0.30 / 2 = 0.15 per phrase → 0.30 total

- Semantic check: "must maintain" vs "shall maintain" (synonymous) → no contradiction

- Source match: grounded_in present in source_chunk → +0.10

- TOTAL SCORE = 0.147 + 0.30 + 0.10 = 0.547

- CLASSIFICATION: PARAPHRASE (0.60 > score > 0.60 is false, so borderline)

⚠️ INTERPRETATION: Agent changed "National Banking Corporation shall" to imperative 
   "Deposit account records must". Synonymous rephrasing. Score: PARAPHRASE.

---

HANDLING INFERENCE (<0.60):

If score < 0.60:
1. Flag as INFERENCE in output
2. Provide explanation: "Requirement interpreted from [source phrase 1] + 
                        [source phrase 2] + context"
3. Do NOT prevent extraction, but mark confidence -0.2

Example (hypothetical inference):
Description: "Critical system redundancy must be maintained with 99.9% uptime SLA."
Grounded in: "Systems supporting Part 370 compliance must maintain availability 
              above 99.9%."

Analysis:
- Mention of "critical system" not in source → inference
- "Redundancy" inferred from "maintain availability" context
- "SLA" not explicit in source; inferred requirement type
- Score = 0.45 (multiple inferences)
- Classification: INFERENCE
- Action: Flag red; require human validation before acceptance

---

OUTPUT SCHEMA:

```json
{
  "requirement_id": "R-DQ-66a485",
  "rule_description": "Deposit account records must maintain 99.5% accuracy standards.",
  "grounded_in": "National Banking Corporation shall maintain deposit account records meeting 99.5% accuracy standards",
  "grounding_score": 0.59,
  "grounding_classification": "PARAPHRASE",
  "grounding_evidence": {
    "word_overlap": {
      "description_words": 8,
      "grounded_words": 12,
      "intersection": 7,
      "jaccard_score": 0.368,
      "contribution": 0.147
    },
    "phrase_overlap": {
      "matched_phrases": [
        "deposit account records",
        "99.5% accuracy standards"
      ],
      "phrase_count": 2,
      "contribution": 0.30
    },
    "semantic_consistency": {
      "description_intent": "Requirement to maintain accuracy",
      "grounded_intent": "Requirement to maintain accuracy",
      "consistent": true,
      "contribution": 0.20
    },
    "source_match": {
      "found_in_chunk": true,
      "contribution": 0.10
    }
  },
  "grounding_notes": "Agent paraphrased 'National Banking Corporation shall' → 'Deposit account records must'. Meaning preserved. Phrases 'deposit account records' and '99.5% accuracy standards' found verbatim in source.",
  "recommended_action": "ACCEPT (paraphrase acceptable with confidence penalty)"
}
```

---

VALIDATION:

1. Manually audit 15 sample requirements (3 per classification):
   - 5 EXACT (verify score > 0.85)
   - 5 PARAPHRASE (verify score 0.60–0.85)
   - 5 INFERENCE (verify score < 0.60)

2. Compare agent classification vs. manual assessment
   - If accuracy < 80%, retrain thresholds

3. No requirement should be EXACT if paraphrased
   (if agent says EXACT, verify it really is)

---

REMEDIATION:

For INFERENCE-classified requirements:
- Option 1: Reject; require human extraction from source
- Option 2: Accept but flag in output; apply confidence penalty (-0.2)
- Option 3: Provide agent with source text directly; re-extract with grounding requirement

DELIVERABLE:

1. All 47 requirements with grounding_score + grounding_classification
2. Grounding validation report (distribution: EXACT, PARAPHRASE, INFERENCE)
3. Flag all INFERENCE requirements for manual review
```

---

### 5. VAGUE ACTION VERBS (28%) (Medium)

#### Problem
13/47 requirements use generic, hard-to-operationalize verbs:

```
"ensure", "verify", "validate", "review", "maintain", "confirm"
```

These are **outcome-focused** but **not actionable.** Example:

```
✗ VAGUE:  "Compliance must ensure data quality is maintained."
✓ SPECIFIC: "Compliance must reconcile deposit balances between core system 
             and GL monthly; investigate variances > $10,000."
```

#### Impact
- **Ambiguous test design:** "How do I test that something is 'ensured'?"
- **Operational confusion:** "What exactly do I do to 'maintain' accuracy?"
- **Unverifiable:** No clear evidence of completion.

#### Remediation
Replace generic verbs with specific actions:

| Vague | Specific |
|-------|----------|
| Ensure | Reconcile, Verify, Calculate, Compare |
| Verify | Sample, Audit, Compare line-by-line, Validate |
| Validate | Test, Reconcile, Confirm against source |
| Review | Audit, Sample, Spot-check, Sign-off |
| Maintain | Monitor, Track, Report, Reconcile |
| Confirm | Sample, Audit, Reconcile, Get written sign-off |

**Remediation Prompt:**

```
TASK: Replace Vague Verbs with Actionable Language

AFFECTED REQUIREMENTS: 13/47

FOR EACH VAGUE REQUIREMENT:
1. Identify vague verb: "ensure", "verify", "validate", "review", "maintain", "confirm"
2. Infer intended action from context (threshold, frequency, owner)
3. Replace with specific action verb + object

VAGUE VERB MAPPING:

"ensure [X] is maintained" 
→ "Monitor [X] [frequency]; escalate if [threshold]"

"verify [X] accuracy"
→ "Sample [N] records; compare to [source]; flag if > [tolerance] errors"

"validate [X] is correct"
→ "Reconcile [X] to [source]; investigate variances > [amount]"

"review [X]"
→ "Audit [N] transactions; sign-off if [criteria] met"

"confirm [X] is accurate"
→ "Reconcile [X] to [source]; get written approval from [role]"

EXAMPLE:

BEFORE (Vague):
Rule description: "Compliance must ensure data quality is maintained at 98% threshold."
Attributes: {threshold: 98%, frequency: daily}

AFTER (Specific):
Rule description: "Compliance must monitor data quality metrics daily; if any metric 
                   falls below 98%, escalate to VP Compliance within 4 hours and 
                   initiate remediation."
Attributes: {threshold: 98%, frequency: daily, escalation_time: "4 hours", 
              escalation_to: "VP Compliance"}

DELIVERABLE:
Rewrite 13 vague requirements with specific action verbs
```

---

## SUMMARY TABLE: WINDSURF IMPROVEMENTS PRIORITIZED

| Priority | Issue | Severity | Effort | Payload |
|----------|-------|----------|--------|---------|
| 1 | Confidence scorer | 🔴 CRITICAL | 3–5 days | Enables gating; validates 40/47 reqs |
| 2 | Schema enforcement | 🔴 CRITICAL | 4–6 days | Ensures consistency; unblocks querying |
| 3 | Metadata enrichment | 🔴 CRITICAL | 5–7 days | Operationalizes all 47 reqs; audit-ready |
| 4 | Grounding validator | 🟠 HIGH | 3–4 days | Improves traceability; flags inference |
| 5 | Vague verb replacement | 🟡 MEDIUM | 2–3 days | Clarifies 13 requirements |

---

## DELIVERY CHECKLIST

- [ ] Confidence scorer: Implemented, tested, producing rationale
- [ ] Schema validator: All 47 requirements pass JSON Schema validation
- [ ] Metadata enrichment: All 8 fields populated for all 47 requirements
- [ ] Grounding validator: Scoring + classification + evidence provided
- [ ] Vague verb replacement: 13 requirements rewritten with specific verbs
- [ ] Manual audit: Sample 10–15 requirements; compare agent output vs. human assessment
- [ ] Regression testing: Verify no requirement degrades in confidence during updates

---

## ESTIMATED TIMELINE

| Phase | Task | Effort | Deliverable |
|-------|------|--------|-------------|
| Week 1 | Confidence + Schema | 6–8 days | 47 reqs with confidence scores + schema compliance |
| Week 2 | Metadata enrichment | 5–7 days | 47 reqs with test procedures, ownership, evidence |
| Week 2–3 | Grounding validator | 3–4 days | Grounding scores + classification |
| Week 3 | Polish + testing | 2–3 days | Manual validation + vague verb replacement |

**Total:** 3–4 weeks to production-ready controls.

