# Node 3.5: GRC Component Extractor

**Status**: Complete

## Overview

The GRC Component Extractor is an intermediate node (Node 3.5) in the Agent1 pipeline that runs between the Confidence Gate and the Atomizer. It extracts Policy, Risk, and Control components from table chunks using the discovered schema, preparing structured GRC data for downstream requirement atomization.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Component Models](#component-models)
- [Next Steps](#next-steps)

## Purpose

The GRC Component Extractor:
- Extracts Policy, Risk, and Control components from Word table chunks
- Uses the discovered schema to guide extraction
- Validates extracted components against Pydantic models
- Builds cross-reference indexes between related components
- Provides structured GRC data for requirement atomization

## Key Features

- **Table-Focused Extraction**: Prioritizes table chunks with record_type annotations
- **Multi-Component Support**: Extracts policies, risks, and controls in a single pass
- **Schema-Guided**: Uses SchemaMap to understand expected fields
- **Relationship Tracking**: Builds cross-reference index between components
- **Validation**: Pydantic model validation with error tracking
- **Retry Logic**: Exponential backoff on LLM failures

## Architecture

### Module Structure

```
src/agent1/nodes/
  grc_extractor.py           # Main extractor node

src/agent1/models/
  grc_components.py          # Component Pydantic models

src/agent1/prompts/grc_extractor/
  v1.0.yaml                  # Prompt configuration
```

### Processing Flow

```
Input State -> Filter Table Chunks -> Group by Record Type
                                            |
                                            v
                                    For each record_type:
                                    - Build extraction prompt
                                    - Call Claude
                                    - Parse response
                                    - Validate components
                                            |
                                            v
                                    Aggregate Results:
                                    - policies[]
                                    - risks[]
                                    - controls[]
                                    - cross_reference_index
```

## Usage

### Programmatic API

```python
from agent1.nodes.grc_extractor import GRCComponentExtractorNode

# Initialize extractor
grc_extractor = GRCComponentExtractorNode()

# Build state with chunks and schema_map
state = {
    "chunks": preprocessor_output.chunks,
    "schema_map": schema_map,
}

# Run extraction
result = grc_extractor(state)

grc_components = result.get("grc_components")
component_index = result.get("component_index")

print(f"Policies: {len(grc_components.policies)}")
print(f"Risks: {len(grc_components.risks)}")
print(f"Controls: {len(grc_components.controls)}")
```

### In Pipeline Context

The GRC extractor is automatically called as part of the `atomize` command:

```bash
python cli.py atomize --input "document.docx"
```

## Configuration

### Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | claude-sonnet-4-20250514 | Claude model for extraction |
| `MAX_RETRIES` | 3 | Retry attempts on LLM failure |
| `RETRY_BACKOFF_BASE` | 2.0 | Base for exponential backoff |

### Prompt Configuration

Prompts are stored in `src/agent1/prompts/grc_extractor/v1.0.yaml` and include:
- System prompt with GRC extraction instructions
- Output JSON schema specification
- Field mapping guidance

## Output Format

### GRCComponentsResponse Model

```python
class GRCComponentsResponse(BaseModel):
    policies: List[PolicyComponent]
    risks: List[RiskComponent]
    controls: List[ControlComponent]
    cross_reference_index: dict[str, List[str]]
    extraction_summary: dict[str, Any]
```

### Example Output

```json
{
  "grc_components": {
    "policies": [
      {
        "component_type": "policy",
        "component_id": "P-001",
        "component_title": "Data Quality Policy",
        "policy_objective": "Ensure data accuracy...",
        "effective_date": "2024-01-01",
        "related_controls": ["C-001", "C-002"]
      }
    ],
    "risks": [
      {
        "component_type": "risk",
        "component_id": "R-001",
        "risk_description": "Data integrity risk...",
        "inherent_risk_rating": "High",
        "mitigation_controls": ["C-001"]
      }
    ],
    "controls": [
      {
        "component_type": "control",
        "component_id": "C-001",
        "control_description": "Daily data validation...",
        "control_type": "Detective",
        "operating_frequency": "Daily"
      }
    ],
    "cross_reference_index": {
      "P-001": ["C-001", "C-002"],
      "R-001": ["C-001"]
    }
  }
}
```

## Component Models

### PolicyComponent

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | str | Unique policy identifier (P-XXX) |
| `component_title` | str | Policy title |
| `component_owner` | str | Policy owner |
| `policy_objective` | str | Policy objective statement |
| `approval_authority` | str | Approval authority |
| `effective_date` | str | Effective date |
| `review_cycle` | str | Review frequency |
| `policy_statement` | str | Full policy statement |
| `scope` | str | Policy scope |
| `detailed_requirements` | Any | Requirements (string or list) |
| `roles_responsibilities` | Any | Roles and responsibilities |
| `related_regulations` | Any | Related regulations |
| `related_controls` | List[str] | Related control IDs |
| `related_risks` | List[str] | Related risk IDs |

### RiskComponent

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | str | Unique risk identifier (R-XXX) |
| `risk_description` | str | Risk description |
| `risk_owner` | str | Risk owner |
| `risk_category` | str | Risk category |
| `inherent_risk_rating` | str | Inherent risk rating |
| `residual_risk_rating` | str | Residual risk rating |
| `effective_date` | str | Effective date |
| `review_cycle` | str | Review frequency |
| `related_policies` | List[str] | Related policy IDs |
| `mitigation_controls` | List[str] | Mitigation control IDs |

### ControlComponent

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | str | Unique control identifier (C-XXX) |
| `control_description` | str | Control description |
| `control_owner` | str | Control owner |
| `control_type` | Any | Control type (string or dict) |
| `operating_frequency` | str | Operating frequency |
| `testing_frequency` | str | Testing frequency |
| `evidence` | Any | Evidence requirements |
| `effective_date` | str | Effective date |
| `review_cycle` | str | Review frequency |
| `related_policies` | List[str] | Related policy IDs |
| `related_risks` | List[str] | Related risk IDs |

## Date Handling

If a date field cannot be parsed, the extractor:
- Keeps the original string value
- Adds a validation error to the component's `validation_errors` list
- Does not null the field

This ensures no data loss while flagging parsing issues.

## Integration Points

### Input

Receives from Node 3 (Confidence Gate):
- `chunks`: List of ContentChunk objects
- `schema_map`: SchemaMap with discovered entities

### Output

Provides to Node 4 (Atomizer):
- `grc_components`: GRCComponentsResponse with extracted components
- `component_index`: Quick lookup index by component_id

## Next Steps

After GRC extraction, the pipeline proceeds to:
1. **[Atomizer](Phase1-Atomizer-Agent.md)** - Extracts atomic requirements from components
2. **[Eval](Phase1-Eval.md)** - Quality assessment

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Confidence Gate](Phase1-Confidence-Scorer.md)
- [Atomizer Agent](Phase1-Atomizer-Agent.md)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for GRC extractor discussions.
