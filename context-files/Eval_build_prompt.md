# Build Prompt: Eval Node

## Overview

The **Eval node** runs *immediately after* the Atomizer Agent and *before* the Router decision. Its purpose is to:

1. Compute quality metrics on extracted requirements
2. Detect failure patterns (coverage gaps, deduplication issues, non-testable obligations)
3. Classify failure type and severity → signal Router decision
4. Return diagnostic JSON that Router consumes to decide: **Pass | Retry | Fail**

---

## Inputs (from `Phase1State`)

```python
{
  "requirements": list[RegulatoryRequirement],          # From Atomizer
  "chunks": list[ContentChunk],                         # From Parser
  "schema_map": SchemaMap,                              # From Schema Discovery
  "extraction_metadata": ExtractionMetadata,            # From Atomizer
  "extraction_iteration": int,                          # 1, 2, 3...
  "prompt_versions": dict[str, str],                    # e.g., {"atomizer": "v1.0_retry"}
  "gate_decision": Literal["accept", "review", "reject"]  # From Confidence Gate
}
```

---

## Output Model

```python
class EvalReport(BaseModel):
    """Diagnostic output from Eval node."""
    
    # Counts & coverage
    total_chunks: int
    chunks_processed: int
    chunks_with_zero_extractions: list[str]
    coverage_ratio: float  # chunks_processed / total_chunks
    
    # Requirement metrics
    total_requirements: int
    requirements_by_type: dict[str, int]  # { "data_quality_threshold": 5, ... }
    avg_confidence: float
    
    # Quality checks (testability, grounding, hallucination)
    testability_issues: list[dict]  # [{"req_id": "...", "issue": "...", "severity": "high|med|low"}]
    grounding_issues: list[dict]    # [{"req_id": "...", "issue": "...", "severity": ...}]
    hallucination_flags: list[dict] # [{"req_id": "...", "inference_level": "...", "flag": "..."}]
    
    # Deduplication metrics
    unique_requirement_count: int
    potential_duplicates: list[tuple[str, str, float]]  # (req_id_a, req_id_b, similarity_score)
    dedup_ratio: float  # unique / total
    
    # Schema completeness
    schema_entities: int
    schema_coverage: dict[str, int]  # How many requirements per schema entity
    
    # Pass/Fail decision signals
    failure_type: Literal["none", "coverage", "testability", "grounding", "dedup", "multi"]
    failure_severity: Literal["low", "medium", "high", "critical"]
    is_retryable: bool
    
    # Actionable feedback
    remediation_suggestions: list[str]
    
    # Metadata
    eval_timestamp: str
    extraction_iteration: int
    prompt_version: str
```

---

## Implementation Checklist

### 1. Coverage Analysis

**Objective**: Detect chunks with zero extractions; signal if coverage is too low.

```python
def _analyze_coverage(chunks: list[ContentChunk], 
                      requirements: list[RegulatoryRequirement]) -> tuple[int, int, list[str], float]:
    """
    Return: (total_chunks, chunks_processed, chunks_with_zero, coverage_ratio)
    """
    chunks_with_zero = []
    chunks_with_extractions = set()
    
    for req in requirements:
        # Requirements have source_chunk_id or source_location
        chunks_with_extractions.add(req.source_chunk_id)
    
    for chunk in chunks:
        if chunk.id not in chunks_with_extractions:
            chunks_with_zero.append(chunk.id)
    
    coverage_ratio = len(chunks_with_extractions) / len(chunks) if chunks else 0.0
    
    return len(chunks), len(chunks_with_extractions), chunks_with_zero, coverage_ratio
```

**Thresholds** (configurable, default):
- `coverage_ratio >= 0.80` → OK
- `coverage_ratio 0.60–0.80` → WARNING
- `coverage_ratio < 0.60` → FAILURE (retryable on iteration 1)

---

### 2. Testability Check

**Objective**: Flag requirements that are NOT testable (e.g., definitions, commentary, vague obligations).

A requirement is **testable** if:
- It has a clear **pass/fail condition** (quantitative or boolean)
- It specifies **what**, **when**, **by whom**, or **how much**
- It is **not a definition or background statement**

```python
def _check_testability(requirement: RegulatoryRequirement) -> tuple[bool, dict]:
    """
    Return: (is_testable, issue_dict or {})
    """
    issues = []
    
    # Red flags
    if requirement.rule_type == "unknown":
        issues.append("rule_type not mapped")
    
    # data_quality_threshold must have threshold_value
    if requirement.rule_type == "data_quality_threshold":
        if not requirement.attributes.get("threshold_value"):
            issues.append("missing threshold_value (cannot test)")
        if not requirement.attributes.get("metric"):
            issues.append("missing metric definition")
    
    # documentation_requirement must specify WHAT and BY WHEN
    if requirement.rule_type == "documentation_requirement":
        if not requirement.attributes.get("documentation_type"):
            issues.append("missing documentation_type")
        if not requirement.attributes.get("applies_when"):
            issues.append("missing trigger condition (applies_when)")
    
    # update_timeline must have threshold_value (days, hours, etc.)
    if requirement.rule_type == "update_timeline":
        if not requirement.attributes.get("threshold_value"):
            issues.append("missing timeline value")
    
    # Check description is not purely definitional
    desc_lower = (requirement.rule_description or "").lower()
    if desc_lower.startswith("a") and " means " in desc_lower:
        issues.append("appears to be a definition, not an obligation")
    
    is_testable = len(issues) == 0
    return is_testable, {"issues": issues, "severity": "high" if len(issues) > 1 else "medium"}
```

---

### 3. Grounding Check

**Objective**: Verify each requirement cites source text; flag missing/weak citations.

```python
def _check_grounding(requirement: RegulatoryRequirement) -> tuple[bool, dict]:
    """
    Return: (is_grounded, issue_dict or {})
    """
    issues = []
    
    # Must have grounded_in field
    if not requirement.grounded_in or not requirement.grounded_in.strip():
        issues.append("missing grounded_in citation")
    
    # Confidence below 0.70 on non-retry pass is suspicious
    if requirement.extraction_iteration == 1 and requirement.confidence < 0.70:
        issues.append(f"low confidence (0.{int(requirement.confidence*100)}) on first iteration")
    
    # Very low confidence on retry is problematic
    if requirement.extraction_iteration >= 2 and requirement.confidence < 0.75:
        issues.append(f"low confidence ({requirement.confidence}) on retry iteration {requirement.extraction_iteration}")
    
    is_grounded = len(issues) == 0
    return is_grounded, {"issues": issues, "severity": "high" if "low confidence" in str(issues) else "medium"}
```

---

### 4. Hallucination Detection

**Objective**: Flag inferred or fabricated obligations (confidence tier-based).

Rules of thumb:
- **0.90–0.99**: Direct quote; safe
- **0.80–0.89**: Minor inference; acceptable on iter 1, risky on iter 2+
- **0.70–0.79**: Moderate inference; flag on retry pass
- **<0.70**: Never accept on retry; reject on iter 1

```python
def _check_hallucination(requirement: RegulatoryRequirement) -> tuple[list[str], str]:
    """
    Return: (hallucination_flags, risk_level)
    """
    flags = []
    risk = "low"
    
    confidence = requirement.confidence
    iteration = requirement.extraction_iteration
    
    if iteration == 1:
        if confidence < 0.70:
            flags.append(f"Confidence {confidence} below safe threshold on first pass")
            risk = "high"
        elif confidence < 0.80:
            flags.append(f"Moderate inference ({confidence}); recommend human review")
            risk = "medium"
    
    if iteration >= 2:
        if confidence < 0.75:
            flags.append(f"Retry pass: confidence {confidence} still below retry threshold (0.75)")
            risk = "critical"
        elif confidence < 0.85:
            flags.append(f"Retry pass: moderate inference ({confidence}); borderline")
            risk = "high"
    
    return flags, risk
```

---

### 5. Deduplication Analysis

**Objective**: Detect near-duplicate requirements (same obligation expressed differently).

```python
def _check_deduplication(requirements: list[RegulatoryRequirement]) -> tuple[float, list[tuple[str, str, float]]]:
    """
    Return: (dedup_ratio, potential_duplicates)
    
    Uses simple cosine similarity on rule descriptions + attributes.
    """
    potential_dups = []
    
    for i, req_a in enumerate(requirements):
        for req_b in requirements[i+1:]:
            # Quick checks
            if req_a.rule_type != req_b.rule_type:
                continue
            
            # Simple similarity: shared words in description
            desc_a = set((req_a.rule_description or "").lower().split())
            desc_b = set((req_b.rule_description or "").lower().split())
            
            if len(desc_a) == 0 or len(desc_b) == 0:
                continue
            
            intersection = len(desc_a & desc_b)
            union = len(desc_a | desc_b)
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity >= 0.75:  # High overlap
                potential_dups.append((req_a.id, req_b.id, similarity))
    
    unique_count = len(requirements) - len(potential_dups)
    dedup_ratio = unique_count / len(requirements) if requirements else 0.0
    
    return dedup_ratio, potential_dups
```

---

### 6. Failure Type Classification

**Objective**: Classify what went wrong; signal Router whether retry is worthwhile.

```python
def _classify_failure(report: dict) -> tuple[str, str, bool]:
    """
    Return: (failure_type, severity, is_retryable)
    
    failure_type: "none", "coverage", "testability", "grounding", "dedup", "multi"
    severity: "low", "medium", "high", "critical"
    is_retryable: bool (iteration < 2 AND failure is coverage/dedup)
    """
    
    failure_type = "none"
    severity = "low"
    is_retryable = False
    
    iteration = report.get("extraction_iteration", 1)
    
    # Coverage issue
    if report.get("coverage_ratio", 0.0) < 0.60:
        failure_type = "coverage"
        severity = "high"
        is_retryable = (iteration < 2)
    
    # Testability issues
    testability_count = len(report.get("testability_issues", []))
    if testability_count > 5:
        failure_type = "testability"
        severity = "high"
        is_retryable = False  # Prompt issue; retry unlikely to help
    
    # Grounding issues (moderate concern)
    grounding_count = len(report.get("grounding_issues", []))
    if grounding_count > 3:
        if failure_type == "none":
            failure_type = "grounding"
            severity = "medium"
        else:
            failure_type = "multi"
            severity = "high"
    
    # Dedup issues (content repetition)
    dedup_ratio = report.get("dedup_ratio", 1.0)
    if dedup_ratio < 0.70:
        if failure_type == "none":
            failure_type = "dedup"
            severity = "medium"
            is_retryable = (iteration < 2)
        else:
            failure_type = "multi"
            severity = "high"
    
    # Critical: too many hallucination flags
    hallucination_count = len(report.get("hallucination_flags", []))
    if hallucination_count > 5:
        severity = "critical"
        is_retryable = False
    
    return failure_type, severity, is_retryable
```

---

### 7. Remediation Suggestions

**Objective**: Provide actionable feedback for Router/human reviewer.

```python
def _generate_suggestions(failure_type: str, 
                         coverage_ratio: float,
                         dedup_ratio: float,
                         testability_issues: list,
                         grounding_issues: list) -> list[str]:
    """Return list of human-readable remediation steps."""
    
    suggestions = []
    
    if failure_type == "coverage" and coverage_ratio < 0.60:
        suggestions.append(
            f"Coverage ratio {coverage_ratio:.1%} too low. Retry with broader rule extraction "
            f"(relax confidence threshold or expand rule_type scope)."
        )
    
    if len(testability_issues) > 0:
        suggestions.append(
            f"Testability issues found ({len(testability_issues)}). Review rule descriptions; "
            f"ensure each has measurable pass/fail condition. Require threshold_value for data_quality rules."
        )
    
    if len(grounding_issues) > 0:
        suggestions.append(
            f"Grounding issues ({len(grounding_issues)}). Verify grounded_in cites source text; "
            f"ensure confidence scores reflect actual inference level."
        )
    
    if dedup_ratio < 0.70:
        suggestions.append(
            f"Deduplication ratio {dedup_ratio:.1%} suggests content repetition. "
            f"Review potential duplicates; merge or remove lower-confidence variants."
        )
    
    if len(suggestions) == 0:
        suggestions.append("All checks passed. Requirements ready for downstream processing.")
    
    return suggestions
```

---

## Node Implementation Pattern

```python
def eval_quality(state: Phase1State) -> Phase1State:
    """LangGraph node: Eval quality and prepare Router decision."""
    
    requirements = state.get("requirements", [])
    chunks = state.get("chunks", [])
    extraction_metadata = state.get("extraction_metadata")
    extraction_iteration = state.get("extraction_iteration", 1)
    prompt_versions = state.get("prompt_versions", {})
    
    # Run all checks
    total_chunks, chunks_processed, chunks_with_zero, coverage_ratio = _analyze_coverage(chunks, requirements)
    
    testability_issues = []
    for req in requirements:
        is_testable, issue = _check_testability(req)
        if not is_testable:
            testability_issues.append({"req_id": req.id, **issue})
    
    grounding_issues = []
    for req in requirements:
        is_grounded, issue = _check_grounding(req)
        if not is_grounded:
            grounding_issues.append({"req_id": req.id, **issue})
    
    hallucination_flags = []
    for req in requirements:
        flags, risk = _check_hallucination(req)
        if flags:
            hallucination_flags.append({"req_id": req.id, "flags": flags, "risk": risk})
    
    dedup_ratio, potential_dups = _check_deduplication(requirements)
    
    schema_coverage = {}
    if state.get("schema_map"):
        for entity in state["schema_map"].entities:
            count = sum(1 for r in requirements if entity.name in str(r.attributes))
            schema_coverage[entity.name] = count
    
    failure_type, failure_severity, is_retryable = _classify_failure({
        "extraction_iteration": extraction_iteration,
        "coverage_ratio": coverage_ratio,
        "testability_issues": testability_issues,
        "grounding_issues": grounding_issues,
        "hallucination_flags": hallucination_flags,
        "dedup_ratio": dedup_ratio,
    })
    
    suggestions = _generate_suggestions(
        failure_type, coverage_ratio, dedup_ratio, testability_issues, grounding_issues
    )
    
    report = EvalReport(
        total_chunks=total_chunks,
        chunks_processed=chunks_processed,
        chunks_with_zero_extractions=chunks_with_zero,
        coverage_ratio=coverage_ratio,
        total_requirements=len(requirements),
        requirements_by_type={rt: sum(1 for r in requirements if r.rule_type == rt) for rt in set(r.rule_type for r in requirements)},
        avg_confidence=extraction_metadata.avg_confidence if extraction_metadata else 0.0,
        testability_issues=testability_issues,
        grounding_issues=grounding_issues,
        hallucination_flags=hallucination_flags,
        unique_requirement_count=len(requirements) - len(potential_dups),
        potential_duplicates=potential_dups,
        dedup_ratio=dedup_ratio,
        schema_entities=len(state.get("schema_map").entities) if state.get("schema_map") else 0,
        schema_coverage=schema_coverage,
        failure_type=failure_type,
        failure_severity=failure_severity,
        is_retryable=is_retryable,
        remediation_suggestions=suggestions,
        eval_timestamp=datetime.utcnow().isoformat(),
        extraction_iteration=extraction_iteration,
        prompt_version=prompt_versions.get("atomizer", "unknown"),
    )
    
    state["eval_report"] = report.model_dump()
    return state
```

---

## Testing Strategy

1. **Unit tests**: Each check function (coverage, testability, grounding, dedup) with synthetic requirements
2. **Integration tests**: Full eval_quality() on real Atomizer output
3. **Threshold validation**: Confirm failure classification against known pass/fail scenarios
4. **Regression**: Eval output stability across prompt version changes

---

## Configuration (Optional YAML)

```yaml
eval:
  thresholds:
    coverage:
      min_ratio: 0.60          # Below = failure
      warning_ratio: 0.80
    testability:
      max_issues: 5            # Beyond = failure
    grounding:
      max_issues: 3
    deduplication:
      min_ratio: 0.70          # Below = warning
    hallucination:
      max_flags: 5             # Beyond = critical
      confidence_tiers:
        iter1_min: 0.70
        iter2_min: 0.75
        iter3_min: 0.80
```

