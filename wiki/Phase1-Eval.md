# Node 5: Eval Quality

**Status**: Complete

## Overview

The Eval node is the fifth and final node in the Agent1 pipeline. It performs comprehensive quality assessment of extracted requirements, detecting failure patterns, computing quality metrics, and classifying issues for downstream decision-making.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Quality Checks](#quality-checks)
- [Failure Classification](#failure-classification)
- [Output Format](#output-format)
- [Next Steps](#next-steps)

## Purpose

The Eval node:
- Analyzes coverage of chunks that yielded extractions
- Checks testability of extracted requirements
- Detects grounding issues and potential hallucinations
- Identifies duplicate requirements
- Validates schema compliance
- Classifies failure patterns and severity
- Computes overall quality score
- Generates actionable suggestions

## Key Features

- **Multi-Check Evaluation**: Six independent quality checks
- **Failure Classification**: Categorizes failure types with severity
- **Quality Scoring**: Computes overall quality score (0.0-1.0)
- **Enrichment Validation**: Self-validates Eval/Atomizer enrichments
- **Actionable Suggestions**: Generates improvement recommendations
- **Confidence Distribution**: Analyzes confidence score distribution

## Architecture

### Module Structure

```
src/agent1/eval/
  __init__.py
  eval_node.py               # Main eval orchestration
  classifier.py              # Failure classification logic
  models.py                  # EvalReport and issue models

src/agent1/eval/checks/
  coverage.py                # Chunk coverage analysis
  testability.py             # Testability checks
  grounding.py               # Grounding verification
  hallucination.py           # Hallucination detection
  deduplication.py           # Duplicate detection
  schema_compliance.py       # Schema validation
```

### Processing Flow

```
Input State -> Run Quality Checks:
                - Coverage analysis
                - Testability check
                - Grounding check
                - Hallucination detection
                - Deduplication check
                - Schema compliance
                      |
                      v
               Classify Failures:
               - Determine failure_type
               - Assign severity
               - Check if retryable
                      |
                      v
               Generate Report:
               - Compute quality score
               - Generate suggestions
               - Build EvalReport
```

## Usage

### Programmatic API

```python
from agent1.eval.eval_node import eval_quality

# Build state with requirements and metadata
state = {
    "requirements": requirements,
    "extraction_metadata": extraction_metadata,
    "chunks": chunks,
    "prompt_versions": prompt_versions,
}

# Run evaluation
result = eval_quality(state)
eval_report = result.get("eval_report")

print(f"Quality score: {eval_report['overall_quality_score']:.2%}")
print(f"Failure type: {eval_report['failure_type']}")
print(f"Severity: {eval_report['failure_severity']}")
```

### In Pipeline Context

The eval node is automatically called as part of the `atomize` command:

```bash
python cli.py atomize --input "document.docx"
```

## Quality Checks

### 1. Coverage Analysis

Analyzes what proportion of chunks yielded extractions:

```python
coverage_ratio = chunks_with_extractions / total_chunks
```

Low coverage may indicate:
- Document structure not matching expected patterns
- Chunks containing non-regulatory content
- Extraction prompt issues

### 2. Testability Check

Validates that requirements are testable:
- Checks for vague language ("appropriate", "reasonable")
- Verifies presence of measurable criteria
- Flags requirements without clear pass/fail conditions

### 3. Grounding Check

Verifies requirements are grounded in source text:
- Checks `grounded_in` field is non-empty
- Validates grounding text exists in source chunks
- Flags weak or missing grounding

### 4. Hallucination Detection

Identifies potential hallucinations:
- Requirements with no source evidence
- Fabricated numeric values
- Invented entity references

### 5. Deduplication Check

Detects duplicate or near-duplicate requirements:
- Semantic similarity analysis
- ID collision detection
- Flags potential duplicates for review

### 6. Schema Compliance

Validates requirements against type-specific schemas:
- Checks required attributes are present
- Validates attribute types
- Flags missing or invalid fields

## Failure Classification

The eval node classifies failures into types:

| Failure Type | Description |
|--------------|-------------|
| `none` | No significant issues |
| `coverage` | Low chunk coverage |
| `grounding` | Grounding issues detected |
| `hallucination` | Potential hallucinations |
| `schema` | Schema compliance failures |
| `testability` | Testability issues |
| `multi` | Multiple failure types |

### Severity Levels

| Severity | Description |
|----------|-------------|
| `low` | Minor issues, acceptable quality |
| `medium` | Notable issues, review recommended |
| `high` | Significant issues, quality concerns |
| `critical` | Major issues, results may be unreliable |

### Retryable Flag

The `is_retryable` flag indicates whether re-running extraction might help:
- `true`: Issues may be transient (LLM variability)
- `false`: Issues are structural (document format, prompt design)

## Output Format

### EvalReport Structure

```python
{
    "total_requirements": int,
    "total_chunks": int,
    "coverage_ratio": float,
    "avg_confidence": float,
    "confidence_distribution": {
        "0.90-0.99": int,
        "0.80-0.89": int,
        "0.70-0.79": int,
        "0.60-0.69": int,
        "0.50-0.59": int
    },
    "requirements_by_type": dict[str, int],
    "testability_issues": list[TestabilityIssue],
    "grounding_issues": list[GroundingIssue],
    "hallucination_flags": list[HallucinationFlag],
    "potential_duplicates": list[PotentialDuplicate],
    "schema_compliance_issues": list[SchemaComplianceIssue],
    "enrichment_validation_issues": list[dict],
    "failure_type": str,
    "failure_severity": str,
    "is_retryable": bool,
    "overall_quality_score": float,
    "suggestions": list[str]
}
```

### Example Output

```json
{
  "eval_report": {
    "total_requirements": 178,
    "total_chunks": 150,
    "coverage_ratio": 0.72,
    "avg_confidence": 0.68,
    "confidence_distribution": {
      "0.90-0.99": 12,
      "0.80-0.89": 35,
      "0.70-0.79": 48,
      "0.60-0.69": 52,
      "0.50-0.59": 31
    },
    "testability_issues": 15,
    "grounding_issues": 22,
    "hallucination_flags": 8,
    "potential_duplicates": 3,
    "schema_compliance_issues": 45,
    "failure_type": "multi",
    "failure_severity": "high",
    "is_retryable": false,
    "overall_quality_score": 0.58,
    "suggestions": [
      "Review grounding for 22 requirements with weak source evidence",
      "Address schema compliance issues in 45 requirements",
      "Consider refining extraction prompt for better testability"
    ]
  }
}
```

## Enrichment Validation

The eval node performs self-validation of enrichments added by Eval/Atomizer:

### Confidence Integrity Check
Validates that declared confidence matches computed features:
```python
if abs(declared_conf - expected_clamped) > 0.05:
    issues.append("confidence_integrity")
```

### Template Error Detection
Detects template errors like doubled words or empty placeholders.

### Enrichment Grounding Check
Validates that system mappings have supporting keywords if inferred.

## Integration Points

### Input

Receives from Node 4 (Atomizer):
- `requirements`: List of RegulatoryRequirement objects
- `extraction_metadata`: ExtractionMetadata with stats
- `chunks`: Original document chunks
- `prompt_versions`: Tracking of prompt versions

### Output

Provides to final output:
- `eval_report`: Comprehensive quality assessment
- Quality metrics for downstream decisions

## Quality Score Calculation

The overall quality score is computed as a weighted combination:

```python
quality_score = (
    coverage_weight * coverage_ratio +
    grounding_weight * grounding_score +
    schema_weight * schema_compliance_ratio +
    testability_weight * testability_score
)
```

Scores range from 0.0 (poor) to 1.0 (excellent).

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Atomizer Agent](Phase1-Atomizer-Agent.md)
- [Confidence Gate](Phase1-Confidence-Scorer.md)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for eval discussions.
