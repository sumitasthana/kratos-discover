# Node 3: Confidence Gate

**Status**: Complete

## Overview

The Confidence Gate is the third node in the Agent1 pipeline. It evaluates the quality of the discovered schema and makes a structured decision about whether to proceed with extraction, require human review, or reject the document. The gate uses configurable thresholds loaded from YAML configuration.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Decision Logic](#decision-logic)
- [Output Format](#output-format)
- [Next Steps](#next-steps)

## Purpose

The Confidence Gate:
- Evaluates schema discovery confidence against configurable thresholds
- Makes structured decisions: accept, human_review, or reject
- Checks schema compliance and coverage metrics when available
- Provides detailed rationale for gate decisions
- Prevents low-quality extractions from proceeding

## Key Features

- **Structured Decisions**: Returns a GateDecision object with decision, score, and rationale
- **Configurable Thresholds**: Thresholds loaded from YAML config file
- **Document Format Awareness**: Different thresholds can be set per document format
- **Multi-Factor Evaluation**: Checks confidence, schema compliance, and coverage
- **Conditional Flags**: Identifies issues that warrant review but not rejection

## Architecture

### Module Structure

```
src/agent1/nodes/
  confidence_gate.py       # Gate logic and GateDecision model

src/agent1/config/
  gate_config.yaml         # Threshold configuration
```

### Processing Flow

```
SchemaMap -> Load Config -> Check Thresholds -> Evaluate Metrics
                                                      |
                                                      v
                                              Build GateDecision:
                                              - decision (accept/human_review/reject)
                                              - score
                                              - failing_checks
                                              - conditional_flags
                                              - rationale
```

## Usage

### Programmatic API

```python
from agent1.nodes.confidence_gate import check_confidence, GateDecision

# Build state with schema_map
state = {
    "schema_map": schema_map,
    "eval_report": eval_report,  # Optional, for additional checks
}

# Run confidence gate
gate_result: GateDecision = check_confidence(state)

print(f"Decision: {gate_result.decision}")
print(f"Score: {gate_result.score:.3f}")
print(f"Rationale: {gate_result.rationale}")

if gate_result.failing_checks:
    print(f"Failing checks: {gate_result.failing_checks}")
```

### In Pipeline Context

The confidence gate is automatically called as part of the `atomize` command:

```bash
python cli.py atomize --input "document.docx"
```

If the gate rejects the document, the pipeline exits with an error.

## Configuration

### Gate Config File

Configuration is stored in `src/agent1/config/gate_config.yaml`:

```yaml
thresholds:
  default:
    auto_accept: 0.85      # Above this: automatic accept
    human_review: 0.50     # Above this but below auto_accept: human review
    min_schema_compliance: 0.50  # Minimum schema compliance ratio
    min_coverage: 0.60     # Minimum chunk coverage ratio
  
  docx:
    auto_accept: 0.80
    human_review: 0.45
```

### Threshold Descriptions

| Threshold | Default | Description |
|-----------|---------|-------------|
| `auto_accept` | 0.85 | Confidence above this triggers automatic acceptance |
| `human_review` | 0.50 | Confidence above this but below auto_accept triggers review |
| `min_schema_compliance` | 0.50 | Minimum ratio of schema-compliant requirements |
| `min_coverage` | 0.60 | Minimum ratio of chunks that yielded extractions |

## Decision Logic

The gate evaluates multiple factors to determine the decision:

### 1. Schema Confidence Check

```
if avg_confidence < human_review:
    failing_checks.append("avg_confidence below minimum")
elif avg_confidence < auto_accept:
    conditional_flags.append("avg_confidence below auto_accept")
```

### 2. Schema Compliance Check (if eval_report available)

```
schema_ratio = 1.0 - (schema_issues / total_requirements)
if schema_ratio < min_schema_compliance:
    failing_checks.append("schema_compliance below threshold")
```

### 3. Coverage Check (if eval_report available)

```
if coverage_ratio < min_coverage:
    failing_checks.append("coverage below threshold")
```

### 4. Final Decision

| Condition | Decision |
|-----------|----------|
| Any failing_checks | reject |
| confidence >= auto_accept AND no conditional_flags | accept |
| confidence >= human_review | human_review |
| Otherwise | reject |

## Output Format

### GateDecision Model

```python
@dataclass
class GateDecision:
    decision: Literal["accept", "human_review", "reject"]
    score: float
    thresholds_applied: dict[str, float]
    failing_checks: list[str]
    conditional_flags: list[str]
    rationale: str
```

### Example Output

```json
{
  "decision": "human_review",
  "score": 0.72,
  "thresholds_applied": {
    "auto_accept": 0.85,
    "human_review": 0.50,
    "min_schema_compliance": 0.50,
    "min_coverage": 0.60
  },
  "failing_checks": [],
  "conditional_flags": [
    "avg_confidence=0.720 < 0.85"
  ],
  "rationale": "Needs review: avg_confidence=0.720 < 0.85"
}
```

### Decision Outcomes

| Decision | Pipeline Behavior |
|----------|-------------------|
| accept | Proceed to GRC Extractor and Atomizer |
| human_review | Proceed with warning logged |
| reject | Pipeline exits with error code 1 |

## Integration Points

### Input

Receives from Node 2 (Schema Discovery):
- `schema_map`: SchemaMap with avg_confidence
- `eval_report`: Optional evaluation metrics

### Output

Provides to downstream nodes:
- `gate_decision`: GateDecision object (serialized in output JSON)

## Next Steps

After the confidence gate:
1. **[GRC Extractor](Phase1-GRC-Extractor.md)** - Extracts Policy/Risk/Control components
2. **[Atomizer](Phase1-Atomizer-Agent.md)** - Extracts atomic requirements

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md)
- [Eval](Phase1-Eval.md)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for confidence gate discussions.
