# kratos-discover

Production-grade Rule Agent built with LangGraph for automated extraction and analysis of regulatory compliance documents.

## Overview

Kratos-discover is an intelligent document processing system designed to extract structured regulatory rules, policies, risks, and controls from compliance documents. Built on LangGraph and LangChain, it leverages large language models to transform unstructured regulatory text into actionable, machine-readable data.

The system currently supports processing FDIC 370 GRC Library documents and provides a robust pipeline for segmentation, extraction, validation, deduplication, and grounding.

## Key Features

- **Automated Document Segmentation**: Intelligently splits regulatory documents into extractable sections
- **Multi-Mode Extraction**: Supports both rule extraction and GRC component (policies, risks, controls) extraction
- **LLM Provider Flexibility**: Compatible with OpenAI and Anthropic Claude models
- **Structured Output**: Uses schema-based structured output when supported by the LLM, with fallback to JSON parsing
- **Validation Pipeline**: Multi-stage validation, deduplication, and parsing to ensure data quality
- **Strict Grounding**: Enforces verification of extracted items against source text to prevent hallucinations
- **Versioned Prompts**: Supports prompt versioning for reproducibility and iterative improvement
- **Debug Mode**: Comprehensive debugging capabilities with intermediate artifact dumps
- **Flexible I/O**: Supports multiple document formats (DOCX, PDF, HTML) with configurable output options

## Architecture

The system implements a multi-node LangGraph pipeline:

1. **Segmentation Node**: Divides the source document into logical sections
2. **Extraction Node**: Uses LLM to extract rules or GRC components with structured schemas
3. **Validation Node**: Parses and validates extracted data against defined schemas
4. **Deduplication Node**: Removes duplicate entries based on content similarity
5. **Grounding Node**: Verifies each extracted item against source text and filters ungrounded items

### Core Components

- **RuleAgent**: Main orchestrator implementing the LangGraph pipeline
- **PromptRegistry**: Manages versioned prompt specifications
- **CLI**: Command-line interface for batch processing
- **Data Models**: Pydantic models for Rules, Policies, Risks, and Controls

## Installation

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/sumitasthana/kratos-discover.git
cd kratos-discover
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On Unix or MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp config/.env.example .env
```

Edit `.env` to add your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
CLAUDE_MODEL=claude-opus-4-20250805
OPENAI_MODEL=gpt-4o-mini
FDIC_370_PATH=data/FDIC_370_GRC_Library_National_Bank.docx
```

## Usage

### Data Preparation

Place your FDIC 370 source document in the `data/` directory:
```
data/FDIC_370_GRC_Library_National_Bank.docx
```

Note: The `data/` directory is gitignored to prevent accidental commits of sensitive documents.

### Command-Line Interface

#### Basic Rule Extraction

Extract rules using OpenAI:
```bash
python cli.py --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

Extract rules using Anthropic Claude:
```bash
python cli.py --provider anthropic --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

#### GRC Component Extraction

Extract policies, risks, and controls:
```bash
python cli.py --mode grc_components --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output grc_results.json
```

#### Advanced Options

Enable debug mode with intermediate outputs:
```bash
python cli.py --provider openai --debug --dump-debug --output results.json
```

Override the active prompt version:
```bash
python cli.py --provider openai --prompt-version v1.2 --output results.json
```

Specify a custom output directory:
```bash
python cli.py --provider openai --output-dir ./my_outputs
```

Adjust logging level:
```bash
python cli.py --provider openai --log-level DEBUG
```

### Programmatic API

```python
import os
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

# Initialize prompt registry
registry = PromptRegistry(base_dir=Path("."))

# Configure LLM (choose one)
# Option A: Anthropic Claude
llm = ChatAnthropic(
    model=os.getenv("CLAUDE_MODEL", "claude-opus-4-20250805"),
    max_tokens=3000,
    temperature=0
)

# Option B: OpenAI
# llm = ChatOpenAI(
#     model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
#     temperature=0
# )

# Create agent instance
agent = RuleAgent(registry=registry, llm=llm)

# Extract rules
rules = agent.extract_rules(document_path=os.getenv("FDIC_370_PATH"))
print(f"Extracted {len(rules)} rules")

# Extract GRC components
components = agent.extract_grc_components(document_path=os.getenv("FDIC_370_PATH"))
print(f"Policies: {len(components['policies'])}")
print(f"Risks: {len(components['risks'])}")
print(f"Controls: {len(components['controls'])}")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | Required for Anthropic |
| `OPENAI_API_KEY` | API key for OpenAI | Required for OpenAI |
| `CLAUDE_MODEL` | Claude model identifier | `claude-opus-4-20250805` |
| `OPENAI_MODEL` | OpenAI model identifier | `gpt-4o-mini` |
| `FDIC_370_PATH` | Path to FDIC 370 document | `data/FDIC_370_GRC_Library_National_Bank.docx` |
| `LLM_PROVIDER` | Default LLM provider | `openai` |
| `RULE_AGENT_MODE` | Default extraction mode | `rules` |
| `RULE_AGENT_OUTPUT_DIR` | Default output directory | `outputs` |
| `RULE_AGENT_LOG_LEVEL` | Logging verbosity | `INFO` |

### Prompt Versioning

Prompt specifications are stored in `prompts/` with version control:

- `prompts/registry.yaml`: Defines active prompt versions
- `prompts/rule_extraction/v1.0.yaml`: Rule extraction prompt v1.0
- `prompts/rule_extraction/v1.1.yaml`: Rule extraction prompt v1.1
- `prompts/rule_extraction/v1.2.yaml`: Rule extraction prompt v1.2

To switch prompt versions, either:
1. Edit `prompts/registry.yaml` to change the active version
2. Use the `--prompt-version` CLI flag to override at runtime

## Data Models

### Rule Model

```python
class Rule(BaseModel):
    rule_id: str
    category: RuleCategory  # rule, control, risk
    rule_type: RuleType     # data_quality_threshold, ownership_category, etc.
    rule_description: str
    grounded_in: str
    confidence: float       # 0.5 to 0.99
    attributes: Dict[str, Any]
    metadata: RuleMetadata
```

### GRC Components

- **PolicyComponent**: Represents organizational policies
- **RiskComponent**: Represents identified risks
- **ControlComponent**: Represents control measures

Each component includes:
- Unique identifier
- Description/title
- Owner information
- Source table reference
- Validation status
- Metadata (source block, location)

## Development

### Running Tests

Execute the test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

Run specific test files:
```bash
pytest tests/test_rule_agent.py
pytest tests/test_prompt_registry.py
pytest tests/test_cli.py
```

### Project Structure

```
kratos-discover/
├── cli.py                      # Command-line interface
├── rule_agent.py               # Main RuleAgent implementation
├── prompt_registry.py          # Prompt version management
├── requirements.txt            # Python dependencies
├── config/
│   ├── .env.example            # Environment variable template
│   └── rule_attributes_schema.yaml
├── prompts/
│   ├── registry.yaml           # Active prompt versions
│   └── rule_extraction/        # Versioned prompt specs
│       ├── v1.0.yaml
│       ├── v1.1.yaml
│       └── v1.2.yaml
├── tests/
│   ├── test_cli.py
│   ├── test_rule_agent.py
│   ├── test_prompt_registry.py
│   └── conftest.py
├── data/                       # Input documents (gitignored)
└── outputs/                    # Extraction results (gitignored)
```

### Debug Mode

Debug mode provides visibility into the extraction pipeline:

```bash
python cli.py --debug --dump-debug --provider openai
```

This creates a timestamped debug directory containing:
- `raw_rules.json`: Initial LLM extraction output
- `validated_rules.json`: Post-validation results
- `deduped_rules.json`: After deduplication

## Quality Assurance

### Strict Grounding

The grounding node implements a verification step that:
- Compares extracted content against source section text
- Calculates grounding scores
- Filters out items that cannot be verified in the source
- Prevents LLM hallucinations and ensures accuracy

### Validation Pipeline

Multi-stage validation ensures data quality:
1. Schema validation using Pydantic models
2. Required field verification
3. Data type and constraint checking
4. Deduplication based on content similarity
5. Source text verification

## Troubleshooting

### Common Issues

**Import Errors**: Ensure virtual environment is activated and dependencies are installed
```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**API Key Errors**: Verify environment variables are set correctly
```bash
echo $OPENAI_API_KEY  # or echo %OPENAI_API_KEY% on Windows
```

**File Not Found**: Check that input document path is correct and file exists
```bash
ls -la data/FDIC_370_GRC_Library_National_Bank.docx
```

**Model Timeout**: For large documents, consider using debug mode to process incrementally

### Logging

Increase log verbosity for troubleshooting:
```bash
python cli.py --log-level DEBUG
```

## Contributing

Contributions are welcome. Please ensure:
- Code follows existing style conventions
- Tests pass with `pytest`
- New features include appropriate test coverage
- Documentation is updated for new functionality

## License

This project is provided as-is for regulatory compliance document processing.

## Acknowledgments

Built with:
- LangChain: Framework for LLM applications
- LangGraph: Graph-based workflow orchestration
- Pydantic: Data validation and schema management
- OpenAI and Anthropic: LLM providers
