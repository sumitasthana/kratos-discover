# Phase 1 Component: Parse and Chunk

**Status**: ✅ Complete

## Overview

The Parse and Chunk component (also known as Agent1) is a deterministic preprocessor that serves as the first node in the Kratos-Discover pipeline. It parses supported document formats and breaks them into clean, bounded text chunks for downstream processing.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Supported Formats](#supported-formats)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Next Steps](#next-steps)

## Purpose

The Parse and Chunk component transforms unstructured documents into structured, processable chunks that can be consumed by downstream agents like the Schema Discovery Agent. It operates deterministically—the same input file always produces the same chunk IDs and structure.

## Key Features

- **Deterministic Parsing**: Same input produces identical output on every run
- **No LLM Dependency**: Pure algorithmic processing for consistency and speed
- **Structure Preservation**: Maintains document hierarchy (headings, lists, tables)
- **Table Detection**: Recognizes and preserves table data as structured rows and columns
- **Configurable Chunking**: Adjustable chunk size limits for optimal downstream processing
- **Whitespace Normalization**: Light cleanup without losing content integrity

## Supported Formats

### Currently Supported
- **.docx** - Microsoft Word documents (full support)

### Planned/Placeholder
- **.xlsx** - Excel spreadsheets (raises `NotImplementedError`)
- **.csv** - CSV files (raises `NotImplementedError`)

## Architecture

### Module Structure

```
src/agent1/
  ├── __init__.py
  ├── exceptions.py          # Custom exception classes
  ├── models/
  │   ├── __init__.py
  │   ├── input.py           # Input data models
  │   └── chunks.py          # Output chunk models
  ├── nodes/
  │   ├── __init__.py
  │   └── preprocessor.py    # Main parsing orchestrator
  ├── parsers/
  │   ├── __init__.py
  │   ├── docx_parser.py     # DOCX parser implementation
  │   ├── xlsx_parser.py     # Placeholder
  │   └── csv_parser.py      # Placeholder
  └── utils/
      ├── __init__.py
      └── chunking.py        # Chunking utilities
```

### Processing Flow

```
Input Document → Format Detection → Parser Selection → Structure Extraction
                                                      ↓
                                              Chunk Generation
                                                      ↓
                                          Whitespace Normalization
                                                      ↓
                                            Output Chunks
```

## Usage

### Programmatic API

```python
from pathlib import Path
from src.agent1.nodes.preprocessor import parse_and_chunk

# Process a DOCX document
output = parse_and_chunk(
    file_path=Path("data/FDIC_370_GRC_Library_National_Bank.docx"),
    file_type="docx",
    max_chunk_chars=3000,    # Maximum characters per chunk
    min_chunk_chars=50,      # Minimum characters per chunk
)

# Access results
print(f"Total chunks: {output.total_chunks}")
print(f"Document stats: {output.document_stats}")

# Iterate through chunks
for chunk in output.chunks:
    print(f"Type: {chunk.chunk_type}, ID: {chunk.chunk_id}")
    print(f"Content: {chunk.content[:100]}...")
```

### Integration Example

```python
# Example of using parse_and_chunk as first node in a LangGraph pipeline
from langgraph.graph import StateGraph
from src.agent1.nodes.preprocessor import parse_and_chunk

def build_pipeline():
    workflow = StateGraph(PipelineState)
    
    # Add parse and chunk as first node
    workflow.add_node("parse_chunk", lambda state: {
        **state,
        "chunks": parse_and_chunk(
            file_path=state["document_path"],
            file_type=state["file_type"]
        ).chunks
    })
    
    # Add subsequent nodes
    workflow.add_node("schema_discovery", schema_discovery_node)
    # ... more nodes
    
    # Define edges
    workflow.set_entry_point("parse_chunk")
    workflow.add_edge("parse_chunk", "schema_discovery")
    # ... more edges
    
    return workflow.compile()
```

## Configuration

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `Path` | Required | Path to input document |
| `file_type` | `str` | Required | Document format: "docx", "xlsx", "csv" |
| `max_chunk_chars` | `int` | `3000` | Maximum characters per chunk |
| `min_chunk_chars` | `int` | `50` | Minimum characters per chunk |

### Chunking Strategy

- Chunks respect logical document boundaries (sections, paragraphs)
- Large sections are split at natural breakpoints
- Tables are kept intact within single chunks when possible
- Headings are included with their associated content

## Output Format

### Chunk Model

```python
class Chunk:
    chunk_id: str           # Unique, deterministic identifier
    chunk_type: str         # "heading", "prose", "list", "table"
    content: str            # Raw text content
    table_data: List[List]  # Structured table (if chunk_type="table")
    metadata: Dict          # Additional metadata
```

### Output Container

```python
class ParsedOutput:
    total_chunks: int
    document_stats: Dict
    chunks: List[Chunk]
```

### Example Output

```json
{
  "total_chunks": 42,
  "document_stats": {
    "headings": 8,
    "prose_blocks": 25,
    "lists": 6,
    "tables": 3,
    "total_characters": 45230
  },
  "chunks": [
    {
      "chunk_id": "chunk_0001",
      "chunk_type": "heading",
      "content": "Section 1: Introduction",
      "table_data": null,
      "metadata": {}
    },
    {
      "chunk_id": "chunk_0002",
      "chunk_type": "prose",
      "content": "This document outlines...",
      "table_data": null,
      "metadata": {}
    }
  ]
}
```

## Logging

The Parse and Chunk component uses `structlog` for structured logging. Key events include:

- `parse_started` - Document parsing initiated
- `parse_completed` - Parsing finished with statistics
- `empty_chunk_skipped` - Chunks below minimum size threshold
- `chunk_parse_failed` - Non-fatal parsing errors for specific blocks

## Testing

```bash
# Run Parse and Chunk tests
pytest tests/test_agent1_preprocessor.py

# Run with coverage
pytest tests/test_agent1_preprocessor.py --cov=src.agent1 --cov-report=html
```

Tests generate `.docx` fixtures at runtime to avoid committing binary test files.

## Next Steps

After chunks are generated by this component, they flow to:

1. **[Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md)** - Analyzes chunks to discover data schemas
2. **[Confidence Scorer](Phase1-Confidence-Scorer.md)** - Assigns confidence scores to extracted data

## Related Documentation

- [Architecture Overview](Architecture.md#core-components)
- [Development Guide](Development-Guide.md)
- [API Reference](API-Reference.md)

---

**Questions or Issues?** [Report an issue](https://github.com/sumitasthana/kratos-discover/issues) or see [Troubleshooting](Troubleshooting.md).
