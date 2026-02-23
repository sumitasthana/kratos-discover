# Node 4: Requirement Atomizer Agent

**Status**: Complete

## Overview

The Requirement Atomizer Agent is the fourth node in the Agent1 pipeline. It extracts atomic, testable regulatory requirements from document chunks and GRC components. Each requirement is a single, verifiable obligation with confidence scoring and source grounding.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Rule Types](#rule-types)
- [Output Format](#output-format)
- [Confidence Scoring](#confidence-scoring)
- [Next Steps](#next-steps)

## Purpose

The Requirement Atomizer:
- Extracts atomic regulatory requirements from document chunks
- Links requirements to parent GRC components (policies, risks, controls)
- Assigns confidence scores based on grounding quality
- Validates requirements against type-specific attribute schemas
- Auto-repairs missing required fields when possible

## Key Features

- **Atomic Extraction**: Each requirement is a single, testable obligation
- **Type-Specific Attributes**: Different rule types have different required/optional fields
- **Confidence Calibration**: 4-tier confidence scoring (0.50-0.99)
- **Grounding Verification**: Requirements include verbatim source text
- **Schema Validation**: Pydantic validation with auto-repair
- **Batch Processing**: Chunks processed in batches for efficiency
- **Parent Linking**: Requirements linked to source GRC components

## Architecture

### Module Structure

```
src/agent1/nodes/atomizer/
  __init__.py
  node.py                    # Main orchestration
  batch_processor.py         # LLM batch processing
  response_parser.py         # JSON parsing
  schema_repair.py           # Auto-repair logic
  prompt_builder.py          # Prompt construction

src/agent1/models/
  requirements.py            # RegulatoryRequirement model

src/agent1/prompts/requirement_atomizer/
  v1.0.yaml                  # Prompt configuration
```

### Processing Flow

```
Input State -> Batch Chunks -> For each batch:
                                - Build prompt with schema guidance
                                - Call Claude
                                - Parse JSON response
                                - Validate requirements
                                - Auto-repair missing fields
                                - Score confidence
                                      |
                                      v
                              Aggregate Results:
                              - requirements[]
                              - extraction_metadata
                              - skipped_chunks[]
```

## Usage

### CLI Usage

```bash
# Run full pipeline including atomizer
python cli.py atomize --input "document.docx"

# Output includes requirements in JSON
```

### Programmatic API

```python
from agent1.nodes.atomizer import RequirementAtomizerNode

# Initialize atomizer
atomizer = RequirementAtomizerNode()

# Build state with chunks, schema_map, and grc_components
state = {
    "chunks": preprocessor_output.chunks,
    "schema_map": schema_map,
    "grc_components": grc_components,
    "extraction_iteration": 1,
}

# Run atomization
result = atomizer(state)

requirements = result.get("requirements", [])
extraction_metadata = result.get("extraction_metadata")

print(f"Extracted: {len(requirements)} requirements")
print(f"Avg confidence: {extraction_metadata.avg_confidence:.2%}")
```

## Configuration

### Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | claude-sonnet-4-20250514 | Claude model for extraction |
| `MAX_BATCH_CHARS` | 15000 | Maximum characters per batch |
| `MAX_RETRIES_PER_BATCH` | 3 | Retry attempts per batch |
| `RETRY_BACKOFF_BASE` | 2.0 | Exponential backoff base |
| `BATCH_FAILURE_THRESHOLD` | 0.5 | Max batch failure ratio before abort |

## Rule Types

The atomizer extracts requirements of the following types:

| Rule Type | Code | Description |
|-----------|------|-------------|
| `data_quality_threshold` | DQ | Data quality metrics and thresholds |
| `ownership_category` | OWN | Ownership classification requirements |
| `beneficial_ownership_threshold` | BOT | Beneficial ownership thresholds |
| `documentation_requirement` | DOC | Documentation requirements |
| `update_requirement` | UPD | Update/change requirements |
| `update_timeline` | TL | Timeline requirements |

### Type-Specific Attributes

Each rule type has required and optional attributes:

**data_quality_threshold**:
- Required: `metric`, `threshold_value`, `threshold_direction`
- Optional: `threshold_unit`, `consequence`

**ownership_category**:
- Required: `ownership_type`, `required_data_elements`
- Optional: `insurance_coverage`, `cardinality`

**documentation_requirement**:
- Required: `applies_to`, `requirement`
- Optional: `consequence`

**update_timeline**:
- Required: `applies_to`, `threshold_value`, `threshold_unit`
- Optional: `consequence`

## Output Format

### RegulatoryRequirement Model

```python
class RegulatoryRequirement(BaseModel):
    requirement_id: str       # R-{TYPE_CODE}-{HASH6}
    rule_type: RuleType       # Enum of rule types
    rule_description: str     # Plain-English testable statement
    grounded_in: str          # Verbatim source text
    confidence: float         # 0.50-0.99
    attributes: dict          # Type-specific fields
    metadata: RuleMetadata    # Source tracking
    parent_component_id: str  # Optional link to GRC component
```

### Example Output

```json
{
  "requirements": [
    {
      "requirement_id": "R-DQ-a1b2c3",
      "rule_type": "data_quality_threshold",
      "rule_description": "Customer account data must achieve 99% accuracy rate.",
      "grounded_in": "Data quality standards require 99% accuracy for all customer account records.",
      "confidence": 0.87,
      "attributes": {
        "metric": "accuracy",
        "threshold_value": 99,
        "threshold_direction": "minimum"
      },
      "metadata": {
        "source_chunk_id": "chunk_0042",
        "source_location": "Table 3, Row 5",
        "schema_version": "schema-a1b2c3",
        "prompt_version": "v1.0",
        "extraction_iteration": 1
      },
      "parent_component_id": "P-001"
    }
  ],
  "extraction_metadata": {
    "total_chunks_processed": 150,
    "total_requirements_extracted": 178,
    "avg_confidence": 0.72,
    "rule_type_distribution": {
      "data_quality_threshold": 45,
      "update_timeline": 38,
      "documentation_requirement": 32
    }
  }
}
```

### ExtractionMetadata

```python
class ExtractionMetadata(BaseModel):
    total_chunks_processed: int
    total_requirements_extracted: int
    chunks_with_zero_extractions: list[str]
    skipped_chunks: list[ChunkSkipRecord]
    avg_confidence: float
    rule_type_distribution: dict[str, int]
    extraction_iteration: int
    prompt_version: str
    model_used: str
    total_llm_calls: int
    total_input_tokens: int
    total_output_tokens: int
```

## Confidence Scoring

Requirements are assigned confidence scores in a 4-tier system:

| Tier | Range | Interpretation |
|------|-------|----------------|
| High | 0.90-0.99 | Exact match to source text |
| Good | 0.80-0.89 | Minor inference required |
| Moderate | 0.70-0.79 | Moderate inference |
| Low | 0.50-0.69 | Weak grounding, needs review |

Confidence is clamped to the 0.50-0.99 range. Values below 0.50 are raised to 0.50; values above 0.99 are capped at 0.99.

### Grounding Classification

Each requirement includes a grounding classification:
- **EXACT**: Direct quote from source
- **PARAPHRASE**: Rephrased but semantically equivalent
- **INFERENCE**: Derived from context

## Chunk Skip Tracking

Chunks that yield zero extractions are tracked with reasons:

| Skip Reason | Description |
|-------------|-------------|
| `no_extractable_content` | Chunk has no regulatory obligations |
| `parse_error` | LLM response parsing failed |
| `below_threshold` | All extractions below confidence threshold |
| `llm_error` | LLM call failed |
| `empty_response` | LLM returned empty/null response |

## Integration Points

### Input

Receives from Node 3.5 (GRC Extractor):
- `chunks`: List of ContentChunk objects
- `schema_map`: SchemaMap with discovered entities
- `grc_components`: Extracted GRC components
- `component_index`: Component lookup index

### Output

Provides to Node 5 (Eval):
- `requirements`: List of RegulatoryRequirement objects
- `extraction_metadata`: ExtractionMetadata with stats
- `prompt_versions`: Tracking of prompt versions used

## Next Steps

After atomization, the pipeline proceeds to:
1. **[Eval](Phase1-Eval.md)** - Quality assessment and failure classification

## Related Documentation

- [Architecture Overview](Architecture.md)
- [GRC Extractor](Phase1-GRC-Extractor.md)
- [Eval](Phase1-Eval.md)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for atomizer discussions.
