# Usage Guide

Learn how to use Kratos-Discover for extracting rules and GRC components from regulatory documents.

## Table of Contents

- [Command-Line Interface](#command-line-interface)
- [Extraction Modes](#extraction-modes)
- [Basic Examples](#basic-examples)
- [Advanced Usage](#advanced-usage)
- [Programmatic API](#programmatic-api)
- [Output Formats](#output-formats)

## Command-Line Interface

The primary way to interact with Kratos-Discover is through the CLI tool `cli.py`.

### Basic Syntax

```bash
python cli.py [OPTIONS]
```

### Required Arguments

At minimum, you need to specify:
- `--provider`: LLM provider (`openai` or `anthropic`)
- `--input`: Path to your input document (or set via `FDIC_370_PATH` env var)

### Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--provider` | LLM provider: `openai` or `anthropic` | Value from `LLM_PROVIDER` env var |
| `--input` | Path to input document | Value from `FDIC_370_PATH` env var |
| `--output` | Output filename | Auto-generated with timestamp |
| `--output-dir` | Output directory | `outputs/` |
| `--mode` | Extraction mode: `rules` or `grc_components` | `rules` |
| `--debug` | Enable debug mode | `false` |
| `--dump-debug` | Dump intermediate artifacts | `false` |
| `--prompt-version` | Override prompt version | Active version from registry |
| `--log-level` | Logging level: DEBUG, INFO, WARNING, ERROR | `INFO` |

## Extraction Modes

Kratos-Discover supports two extraction modes:

### 1. Rules Mode (Default)

Extracts regulatory rules with detailed attributes.

```bash
python cli.py --mode rules --provider openai --input data/document.docx
```

**Output Structure**:
```json
{
  "rule_id": "RULE_001",
  "category": "rule",
  "rule_type": "data_quality_threshold",
  "rule_description": "Customer data must be verified within 24 hours",
  "grounded_in": "Section 2.3, paragraph 1",
  "confidence": 0.95,
  "attributes": {},
  "metadata": {}
}
```

### 2. GRC Components Mode

Extracts policies, risks, and controls separately.

```bash
python cli.py --mode grc_components --provider openai --input data/document.docx
```

**Output Structure**:
```json
{
  "policies": [...],
  "risks": [...],
  "controls": [...]
}
```

## Basic Examples

### Example 1: Extract Rules with OpenAI

```bash
python cli.py \
  --provider openai \
  --input data/FDIC_370_GRC_Library_National_Bank.docx \
  --output my_rules.json
```

**Expected Output**:
```
2025-01-15 10:30:45 INFO Starting rule extraction pipeline...
2025-01-15 10:30:46 INFO Segmentation complete: 15 sections identified
2025-01-15 10:31:20 INFO Extraction complete: 45 rules extracted
2025-01-15 10:31:22 INFO Validation complete: 43 rules validated
2025-01-15 10:31:23 INFO Deduplication complete: 40 unique rules
2025-01-15 10:31:35 INFO Grounding verification complete: 38 grounded rules
2025-01-15 10:31:35 INFO Results saved to: outputs/my_rules.json
```

### Example 2: Extract GRC Components with Anthropic

```bash
python cli.py \
  --mode grc_components \
  --provider anthropic \
  --input data/compliance_doc.docx \
  --output grc_output.json
```

### Example 3: Debug Mode with Intermediate Outputs

```bash
python cli.py \
  --provider openai \
  --debug \
  --dump-debug \
  --input data/document.docx
```

This creates a debug directory with intermediate files:
- `raw_rules.json`: Initial LLM extraction
- `validated_rules.json`: After validation
- `deduped_rules.json`: After deduplication

### Example 4: Custom Output Directory

```bash
python cli.py \
  --provider openai \
  --input data/document.docx \
  --output-dir ./results/2025-01
```

### Example 5: Use Specific Prompt Version

```bash
python cli.py \
  --provider openai \
  --prompt-version v1.2 \
  --input data/document.docx
```

## Advanced Usage

### Verbose Logging

For detailed execution logs:

```bash
python cli.py \
  --provider openai \
  --log-level DEBUG \
  --input data/document.docx
```

### Processing Multiple Documents

Use a bash loop to process multiple files:

```bash
for file in data/*.docx; do
  echo "Processing $file..."
  python cli.py --provider openai --input "$file" --output-dir results/
done
```

### Combining with Other Tools

#### Export to CSV

```bash
python cli.py --provider openai --input data/doc.docx --output rules.json
# Then convert JSON to CSV using jq or Python
cat rules.json | jq -r '.[] | [.rule_id, .rule_description] | @csv' > rules.csv
```

#### Pipeline Processing

```bash
# Extract rules
python cli.py --provider openai --input data/doc.docx --output stage1.json

# Further processing with custom script
python your_analysis_script.py stage1.json
```

## Programmatic API

For integration into Python applications:

### Basic Usage

```python
import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

# Initialize
registry = PromptRegistry(base_dir=Path("."))
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = RuleAgent(registry=registry, llm=llm)

# Extract rules
rules = agent.extract_rules(document_path="data/document.docx")
print(f"Extracted {len(rules)} rules")

# Access individual rules
for rule in rules:
    print(f"{rule.rule_id}: {rule.rule_description}")
```

### Extract GRC Components

```python
from langchain_anthropic import ChatAnthropic

# Initialize with Anthropic
llm = ChatAnthropic(model="claude-opus-4-20250805", max_tokens=3000)
agent = RuleAgent(registry=registry, llm=llm)

# Extract GRC components
components = agent.extract_grc_components(document_path="data/doc.docx")

print(f"Policies: {len(components['policies'])}")
print(f"Risks: {len(components['risks'])}")
print(f"Controls: {len(components['controls'])}")
```

### With Debug Mode

```python
agent = RuleAgent(
    registry=registry,
    llm=llm,
    debug=True,
    dump_debug_artifacts=True
)

rules = agent.extract_rules(document_path="data/doc.docx")
# Debug files will be created in outputs/debug_TIMESTAMP/
```

### Custom Configuration

```python
from rule_agent import RuleAgent, RuleAgentConfig

config = RuleAgentConfig(
    provider="openai",
    mode="grc_components",
    output_dir="custom_outputs",
    debug=True
)

agent = RuleAgent(registry=registry, llm=llm, config=config)
```

## Output Formats

### Rule Output Schema

```json
{
  "rule_id": "string",
  "category": "rule|control|risk",
  "rule_type": "string",
  "rule_description": "string",
  "grounded_in": "string",
  "confidence": 0.95,
  "attributes": {
    "key": "value"
  },
  "metadata": {
    "source_block": "string",
    "block_index": 0,
    "validation_status": "string"
  }
}
```

### GRC Components Output Schema

```json
{
  "policies": [
    {
      "policy_id": "string",
      "title": "string",
      "description": "string",
      "owner": "string",
      "source_table": "string"
    }
  ],
  "risks": [
    {
      "risk_id": "string",
      "title": "string",
      "description": "string",
      "owner": "string"
    }
  ],
  "controls": [
    {
      "control_id": "string",
      "title": "string",
      "description": "string",
      "owner": "string"
    }
  ]
}
```

## Best Practices

1. **Start Small**: Test with a small document first to validate your setup
2. **Use Debug Mode**: Enable debug mode for initial runs to understand the pipeline
3. **Version Control**: Track prompt versions for reproducibility
4. **Monitor API Costs**: Large documents can consume significant API tokens
5. **Validate Output**: Always review extracted rules for accuracy
6. **Ground Verification**: Trust the grounding scores - low scores indicate potential hallucinations

## Performance Tips

- **Batch Processing**: Process multiple documents in parallel when possible
- **Prompt Optimization**: Use the latest prompt version for better accuracy
- **Model Selection**: OpenAI GPT-4o-mini is faster; Claude Opus is more accurate
- **Segmentation**: Proper document structure improves extraction quality

## Next Steps

- Learn about [Configuration](Configuration.md) options
- Explore the [API Reference](API-Reference.md) for detailed API documentation
- Review [Troubleshooting](Troubleshooting.md) for common issues

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) on GitHub.
