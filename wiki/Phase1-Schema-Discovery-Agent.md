# Node 2: Schema Discovery Agent

**Status**: Complete

## Overview

The Schema Discovery Agent is the second node in the Agent1 pipeline. It analyzes document chunks to automatically discover entity types, field schemas, and structural patterns within regulatory documents. The agent uses Claude to infer document structure from a stratified sample of chunks.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Stratified Sampling](#stratified-sampling)
- [Next Steps](#next-steps)

## Purpose

The Schema Discovery Agent:
- Analyzes document chunks to identify entity types (Policy, Risk, Control)
- Discovers field schemas for each entity type
- Assigns confidence scores to discovered fields
- Identifies structural patterns (table-based, prose-based, mixed)
- Generates a SchemaMap for downstream extraction

## Key Features

- **Stratified Sampling**: Ensures all entity types are represented in the sample sent to Claude
- **Entity Detection**: Identifies Policy, Risk, and Control entities from table structures
- **Field Discovery**: Infers field names, types, and required/optional status
- **Confidence Scoring**: Per-field confidence based on evidence strength
- **Schema Caching**: Caches discovered schemas to avoid redundant LLM calls
- **Deterministic Hashing**: Schema versions are hashed for reproducibility

## Architecture

### Module Structure

```
src/agent1/nodes/
  └── schema_discovery.py      # Main schema discovery logic

src/agent1/models/
  └── schema_map.py            # SchemaMap and Entity models

src/agent1/prompts/schema_discovery/
  └── v1.0.yaml                # Prompt configuration

src/agent1/cache/
  └── schema_cache.py          # Schema caching utilities
```

### Processing Flow

```
Input Chunks -> Stratified Sampling -> Build Prompt -> Call Claude
                                                          |
                                                          v
                                                    Parse Response
                                                          |
                                                          v
                                              Build SchemaMap with:
                                              - Entities and fields
                                              - Confidence scores
                                              - Structural pattern
                                              - Schema version hash
```

## Usage

### CLI Usage

```bash
# Run schema discovery only (Nodes 1-3)
python cli.py discover-schema --input "path/to/document.docx"

# With custom output
python cli.py discover-schema --input "document.docx" --output "schema.json"
```

### Programmatic API

```python
from agent1.nodes.preprocessor import parse_and_chunk
from agent1.nodes.schema_discovery import schema_discovery_agent

# Parse document
preprocessor_output = parse_and_chunk(
    file_path=Path("document.docx"),
    file_type="docx",
)

# Build state
state = {
    "file_path": str(preprocessor_output.file_path),
    "chunks": preprocessor_output.chunks,
    "prompt_versions": {},
    "errors": [],
}

# Run schema discovery
result = schema_discovery_agent(state)
schema_map = result.get("schema_map")

print(f"Entities: {len(schema_map.entities)}")
print(f"Avg confidence: {schema_map.avg_confidence:.2%}")
print(f"Pattern: {schema_map.structural_pattern}")
```

## Configuration

### Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `MAX_CHUNKS_PER_ENTITY_TYPE` | 3 | Max chunks sampled per entity type |
| `MAX_TOTAL_CHUNKS` | 15 | Maximum total chunks sent to Claude |
| `MAX_RETRIES` | 3 | Retry attempts on LLM failure |

### Prompt Configuration

Prompts are stored in `src/agent1/prompts/schema_discovery/v1.0.yaml` and include:
- System prompt with schema discovery instructions
- Output JSON schema specification
- Examples of expected entity structures

## Output Format

### SchemaMap Model

```python
class SchemaMap(BaseModel):
    entities: list[Entity]           # Discovered entity types
    structural_pattern: str          # "table_based", "prose_based", "mixed"
    document_format: str             # "docx", "pdf", etc.
    schema_version: str              # Deterministic hash of schema content
    avg_confidence: float            # Mean confidence across all fields
```

### Entity Model

```python
class Entity(BaseModel):
    name: str                        # e.g., "Policy", "Risk", "Control"
    fields: list[FieldSchema]        # Discovered fields
    record_count: int                # Estimated records in document
```

### FieldSchema Model

```python
class FieldSchema(BaseModel):
    name: str                        # Field name
    field_type: str                  # "string", "date", "list", etc.
    required: bool                   # Whether field is required
    confidence: float                # 0.0-1.0 confidence score
```

### Example Output

```json
{
  "schema_map": {
    "entities": [
      {
        "name": "Policy",
        "fields": [
          {"name": "component_id", "field_type": "string", "required": true, "confidence": 0.95},
          {"name": "component_title", "field_type": "string", "required": true, "confidence": 0.92},
          {"name": "policy_objective", "field_type": "string", "required": false, "confidence": 0.85}
        ],
        "record_count": 12
      },
      {
        "name": "Control",
        "fields": [
          {"name": "component_id", "field_type": "string", "required": true, "confidence": 0.94},
          {"name": "control_description", "field_type": "string", "required": true, "confidence": 0.91}
        ],
        "record_count": 45
      }
    ],
    "structural_pattern": "table_based",
    "document_format": "docx",
    "schema_version": "schema-a1b2c3d4e5f6",
    "avg_confidence": 0.89
  }
}
```

## Stratified Sampling

The schema discovery agent uses stratified sampling to ensure representative coverage:

1. **Group by Entity Type**: Chunks are grouped by their `record_type` annotation
2. **Prioritize Table Chunks**: Table chunks with complete records are preferred
3. **Sample Per Type**: Up to `MAX_CHUNKS_PER_ENTITY_TYPE` chunks per entity
4. **Include Unannotated**: Some unannotated chunks are included for discovery
5. **Cap Total**: Total sample capped at `MAX_TOTAL_CHUNKS`

This ensures that even if a document has 100+ chunks, the LLM receives a balanced sample representing all entity types.

## Integration Points

### Input

Receives from Node 1 (Preprocessor):
- `chunks`: List of ContentChunk objects with annotations
- `file_path`: Source document path

### Output

Provides to Node 3 (Confidence Gate):
- `schema_map`: SchemaMap with discovered entities and fields
- `prompt_versions`: Tracking of prompt versions used

## Next Steps

After schema discovery, the pipeline proceeds to:
1. **[Confidence Gate](Phase1-Confidence-Scorer.md)** - Validates schema confidence
2. **[GRC Extractor](Phase1-GRC-Extractor.md)** - Extracts components using discovered schema
3. **[Atomizer](Phase1-Atomizer-Agent.md)** - Extracts atomic requirements

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Parse and Chunk](Phase1-Parse-and-Chunk.md)
- [Confidence Gate](Phase1-Confidence-Scorer.md)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for schema discovery discussions.
