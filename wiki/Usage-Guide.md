# Usage Guide

Learn how to use Kratos-Discover for extracting regulatory requirements and GRC components from documents.

## Table of Contents

- [Command-Line Interface](#command-line-interface)
- [CLI Commands](#cli-commands)
- [Basic Examples](#basic-examples)
- [Advanced Usage](#advanced-usage)
- [Programmatic API](#programmatic-api)
- [Output Formats](#output-formats)

## Command-Line Interface

The primary way to interact with Kratos-Discover is through the CLI tool `cli.py`.

### Basic Syntax

```bash
python cli.py <command> --input <path> [OPTIONS]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `preprocess` | Parse DOCX into deterministic chunks (Node 1 only) |
| `discover-schema` | Run schema discovery (Nodes 1-3) |
| `atomize` | Run full pipeline (Nodes 1-5) |

### Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Path to input document (.docx) | Required |
| `--output` | Output filename | Auto-generated with timestamp |
| `--output-dir` | Output directory | `outputs/` |
| `--log-level` | Logging level: DEBUG, INFO, WARNING, ERROR | `INFO` |
| `--dotenv` | Path to .env file | `.env` |

## CLI Commands

### 1. Preprocess Command

Parses a DOCX document into deterministic chunks without calling any LLM.

```bash
python cli.py preprocess --input "document.docx"
```

**Additional Options**:
- `--max-chunk-chars`: Maximum characters per chunk (default: 3000)
- `--min-chunk-chars`: Minimum characters per chunk (default: 50)

**Output**: JSON file with chunks and document statistics.

### 2. Discover-Schema Command

Runs preprocessing, schema discovery, and confidence gate (Nodes 1-3).

```bash
python cli.py discover-schema --input "document.docx"
```

**Additional Options**:
- `--max-chunks`: Maximum chunks to send to Claude (default: 10)

**Output**: JSON file with schema_map, gate_decision, and preprocessor_stats.

### 3. Atomize Command (Full Pipeline)

Runs the complete pipeline: preprocess, schema discovery, confidence gate, GRC extraction, atomization, and evaluation.

```bash
python cli.py atomize --input "document.docx"
```

**Output**: JSON file with:
- `requirements`: Extracted regulatory requirements
- `extraction_metadata`: Processing statistics
- `grc_components`: Policies, risks, and controls
- `eval_report`: Quality assessment
- `schema_map`: Discovered schema
- `gate_decision`: Confidence gate result

## Basic Examples

### Example 1: Full Pipeline Extraction

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run full pipeline
python cli.py atomize --input "C:\path\to\FDIC_370_document.docx"
```

**Expected Output**:
```
INFO:cli:[plan] Requirement Atomizer Pipeline (Nodes 1-5)
INFO:cli:[node1] preprocess chunks=150
INFO:cli:[node2] schema_discovery entities=3 avg_confidence=85.00%
INFO:cli:[node3] confidence_gate decision=human_review score=0.850
INFO:cli:[node3.5] grc_extractor policies=12 risks=8 controls=45
INFO:cli:[node4] atomizer extracted=178 requirements avg_confidence=68.50%
INFO:cli:[node5] eval_quality failure_type=multi severity=high quality_score=58.00%
INFO:cli:[output] wrote=outputs\requirements_document_20260222_183000_abc123.json
```

### Example 2: Schema Discovery Only

```bash
python cli.py discover-schema --input "document.docx" --output "schema.json"
```

### Example 3: Preprocessing Only

```bash
python cli.py preprocess --input "document.docx" --max-chunk-chars 5000
```

### Example 4: Custom Output Directory

```bash
python cli.py atomize --input "document.docx" --output-dir "./results/2026-02"
```

### Example 5: Debug Logging

```bash
python cli.py atomize --input "document.docx" --log-level DEBUG
```

## Advanced Usage

### Verbose Logging

For detailed execution logs:

```bash
python cli.py atomize --log-level DEBUG --input "document.docx"
```

### Processing Multiple Documents

Use a PowerShell loop to process multiple files:

```powershell
Get-ChildItem -Path "data\*.docx" | ForEach-Object {
    Write-Host "Processing $($_.Name)..."
    python cli.py atomize --input $_.FullName --output-dir "results\"
}
```

Or in bash:

```bash
for file in data/*.docx; do
  echo "Processing $file..."
  python cli.py atomize --input "$file" --output-dir results/
done
```

### Combining with Other Tools

#### Export Requirements to CSV

```bash
# Extract requirements
python cli.py atomize --input "document.docx" --output "output.json"

# Convert to CSV using jq
cat output.json | jq -r '.requirements[] | [.requirement_id, .rule_type, .rule_description, .confidence] | @csv' > requirements.csv
```

## Programmatic API

For integration into Python applications:

### Full Pipeline

```python
from pathlib import Path
from agent1.nodes.preprocessor import parse_and_chunk
from agent1.nodes.schema_discovery import schema_discovery_agent
from agent1.nodes.confidence_gate import check_confidence
from agent1.nodes.grc_extractor import GRCComponentExtractorNode
from agent1.nodes.atomizer import RequirementAtomizerNode
from agent1.eval.eval_node import eval_quality

# Node 1: Parse document
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
    "extraction_iteration": 1,
}

# Node 2: Schema discovery
schema_result = schema_discovery_agent(state)
state["schema_map"] = schema_result["schema_map"]

# Node 3: Confidence gate
gate_result = check_confidence(state)
print(f"Gate decision: {gate_result.decision}")

# Node 3.5: GRC extraction
grc_extractor = GRCComponentExtractorNode()
grc_result = grc_extractor(state)
state["grc_components"] = grc_result["grc_components"]

# Node 4: Atomization
atomizer = RequirementAtomizerNode()
atomizer_result = atomizer(state)
requirements = atomizer_result["requirements"]

# Node 5: Evaluation
state["requirements"] = requirements
eval_result = eval_quality(state)

print(f"Extracted: {len(requirements)} requirements")
print(f"Quality score: {eval_result['eval_report']['overall_quality_score']:.2%}")
```

### Individual Node Usage

```python
# Just preprocessing
from agent1.nodes.preprocessor import parse_and_chunk

output = parse_and_chunk(
    file_path=Path("document.docx"),
    file_type="docx",
    max_chunk_chars=3000,
    min_chunk_chars=50,
)

print(f"Chunks: {len(output.chunks)}")
print(f"Stats: {output.document_stats}")
```

## Output Formats

### Full Pipeline Output Schema

```json
{
  "requirements": [
    {
      "requirement_id": "R-DQ-a1b2c3",
      "rule_type": "data_quality_threshold",
      "rule_description": "Customer data must achieve 99% accuracy.",
      "grounded_in": "Data quality standards require 99% accuracy...",
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
    "avg_confidence": 0.72
  },
  "grc_components": {
    "policies": [...],
    "risks": [...],
    "controls": [...]
  },
  "eval_report": {
    "overall_quality_score": 0.58,
    "failure_type": "multi",
    "failure_severity": "high"
  },
  "schema_map": {...},
  "gate_decision": {...}
}
```

### GRC Components Schema

```json
{
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
      "inherent_risk_rating": "High"
    }
  ],
  "controls": [
    {
      "component_type": "control",
      "component_id": "C-001",
      "control_description": "Daily data validation...",
      "control_type": "Detective"
    }
  ]
}
```

## Best Practices

1. **Start Small**: Test with a small document first to validate your setup
2. **Check Gate Decision**: Review confidence gate results before trusting extractions
3. **Monitor Quality Score**: Low quality scores indicate extraction issues
4. **Review Grounding**: Requirements with low confidence may have weak source evidence
5. **Validate Schema Compliance**: Check eval_report for schema compliance issues

## Performance Tips

- **Batch Processing**: The atomizer processes chunks in batches automatically
- **Chunk Size**: Adjust max_chunk_chars for optimal LLM context usage
- **Log Level**: Use INFO for production, DEBUG for troubleshooting

## Next Steps

- Learn about [Configuration](Configuration.md) options
- Explore the [API Reference](API-Reference.md) for detailed API documentation
- Review [Troubleshooting](Troubleshooting.md) for common issues

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) on GitHub.
