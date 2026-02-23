# kratos-discover

Regulatory requirement extraction system for automated processing of compliance documents.

## Overview

Kratos-Discover is an LLM-powered document processing system that extracts structured regulatory requirements, policies, risks, and controls from compliance documents such as FDIC Part 370 IT Controls. The system uses a 5-node pipeline architecture with confidence scoring, schema validation, and quality evaluation.

## The Problem It Solves

This system automates the extraction of structured regulatory compliance data from DOCX documents. Given a regulatory document, the pipeline:

1. **Parses** the document into deterministic chunks (tables, prose, lists)
2. **Discovers** document schema structure using LLM analysis
3. **Gates** processing based on confidence thresholds
4. **Extracts** GRC components (policies, risks, controls) from tables
5. **Atomizes** complex text into atomic regulatory requirements
6. **Evaluates** extraction quality with hallucination detection and grounding verification

The system transforms unstructured regulatory text into structured, validated data with confidence scores and quality metrics.

## Key Features

- **Deterministic Preprocessing**: Parse DOCX into structured chunks with consistent IDs
- **Schema Discovery**: Automatically infer document structure using stratified sampling
- **Confidence Scoring**: Multi-dimensional confidence with grounding verification
- **GRC Extraction**: Extract policies, risks, and controls from Word tables
- **Requirement Atomization**: Break complex text into atomic, testable requirements
- **Quality Evaluation**: Comprehensive checks including hallucination detection, testability, and schema compliance
- **Grounding Classification**: EXACT/PARAPHRASE/INFERENCE classification for each extraction
- **Auto-Repair**: Automatic schema violation repair attempts

## Architecture

The system implements a 5-node pipeline:

| Node | Name | Description |
|------|------|-------------|
| 1 | Preprocessor | Parse DOCX into deterministic chunks |
| 2 | Schema Discovery | Infer document structure using Claude |
| 3 | Confidence Gate | Validate schema confidence meets thresholds |
| 3.5 | GRC Extractor | Extract Policy/Risk/Control components from tables |
| 4 | Atomizer | Extract atomic regulatory requirements |
| 5 | Eval | Quality assessment and failure classification |

### Core Components

- **CLI**: Command-line interface (`cli.py`)
- **Nodes**: Pipeline processing nodes (`nodes/`)
- **Models**: Pydantic data models (`models/`)
- **Scoring**: Confidence scoring system (`scoring/`)
- **Eval**: Quality evaluation checks (`eval/`)

## Installation

### Prerequisites

- Python 3.11 or higher
- Virtual environment (recommended)
- Anthropic API key

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

3. Install the package and dependencies:
```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Or install just the runtime dependencies
pip install -e .
```

Alternatively, install dependencies directly:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp config/.env.example .env
```

Edit `.env` to add your API key:
```
ANTHROPIC_API_KEY=your_anthropic_key
```

## Usage

### Data Preparation

Place your source document in the `data/` directory:
```
data/FDIC_Part370_IT_Controls.docx
```

Note: The `data/` directory is gitignored to prevent accidental commits of sensitive documents.

### Command-Line Interface

#### Full Pipeline (Recommended)

Run the complete extraction pipeline:
```bash
python cli.py atomize --input data/document.docx
```

With custom output path:
```bash
python cli.py atomize --input data/document.docx --output results.json
```

#### Preprocessing Only

Parse document into chunks without LLM processing:
```bash
python cli.py preprocess --input data/document.docx
```

#### Schema Discovery

Run preprocessing and schema discovery:
```bash
python cli.py discover-schema --input data/document.docx
```

### Programmatic API

```python
from pathlib import Path
from nodes.preprocessor import parse_and_chunk
from nodes.schema_discovery import schema_discovery_agent
from nodes.confidence_gate import check_confidence
from nodes.grc_extractor import GRCComponentExtractorNode
from nodes.atomizer import RequirementAtomizerNode
from eval.eval_node import eval_quality

# Node 1: Parse document
preprocessor_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx",
    max_chunk_chars=3000,
    min_chunk_chars=50,
)

# Build state for pipeline
state = {
    "chunks": preprocessor_output.chunks,
    "preprocessor_stats": preprocessor_output.document_stats,
}

# Node 2: Schema Discovery
schema_result = schema_discovery_agent(state)
state["schema_map"] = schema_result["schema_map"]

# Node 3: Confidence Gate
gate_result = check_confidence(state)
print(f"Gate decision: {gate_result.decision}")

# Node 3.5: GRC Extraction
grc_extractor = GRCComponentExtractorNode()
grc_result = grc_extractor(state)
state.update(grc_result)

# Node 4: Atomizer
atomizer = RequirementAtomizerNode()
atomizer_result = atomizer(state)
state.update(atomizer_result)

# Node 5: Eval
eval_result = eval_quality(state)
print(f"Quality score: {eval_result['eval_report']['overall_quality_score']}")
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | Yes |

### Gate Thresholds

Confidence gate thresholds are configured in `src/config/gate_config.yaml`:

```yaml
auto_accept: 0.85      # Auto-accept above this
human_review: 0.70     # Human review between this and auto_accept
auto_reject: 0.50      # Auto-reject below this
```

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

## Project Structure

```
kratos-discover/
├── cli.py                      # CLI wrapper
├── README.md                   # Project documentation
├── pyproject.toml              # Python package configuration
├── requirements.txt            # Python dependencies
│
├── src/                        # Source code
│   ├── cli.py                  # Main CLI implementation
│   ├── exceptions.py           # Custom exceptions
│   │
│   ├── nodes/                  # Pipeline nodes
│   │   ├── preprocessor.py    # Node 1: Parse & Chunk
│   │   ├── schema_discovery.py # Node 2: Schema Discovery
│   │   ├── confidence_gate.py # Node 3: Confidence Gate
│   │   ├── grc_extractor.py   # Node 3.5: GRC Extraction
│   │   └── atomizer/          # Node 4: Atomizer
│   │
│   ├── eval/                   # Node 5: Quality Evaluation
│   │   ├── eval_node.py
│   │   ├── classifier.py
│   │   └── checks/            # Individual quality checks
│   │
│   ├── models/                 # Data models
│   │   ├── chunks.py
│   │   ├── requirements.py
│   │   ├── grc_components.py
│   │   ├── schema_map.py
│   │   └── state.py
│   │
│   ├── scoring/                # Confidence scoring
│   │   ├── confidence_scorer.py
│   │   ├── grounding.py
│   │   └── features.py
│   │
│   ├── parsers/                # Document parsers
│   ├── prompts/                # LLM prompt templates
│   ├── config/                 # Configuration files
│   ├── cache/                  # Caching utilities
│   └── utils/                  # Utility functions
│
├── tests/                      # Test suite
├── wiki/                       # Documentation
├── dashboard/                  # React compliance dashboard
├── data/                       # Input documents (gitignored)
└── outputs/                    # Extraction results (gitignored)
```

## Quality Assurance

### Confidence Scoring

Multi-dimensional confidence scoring with features:
- **Grounding Match**: Jaccard similarity with source text
- **Completeness**: Required field coverage
- **Quantification**: Presence of measurable values
- **Schema Compliance**: Schema validation status
- **Coherence**: Internal consistency
- **Domain Signals**: Domain-specific indicators

### Grounding Classification

Each extraction is classified:
- **EXACT**: Direct quote from source (Jaccard > 0.70)
- **PARAPHRASE**: Rephrased content (Jaccard 0.30-0.70)
- **INFERENCE**: Inferred content (Jaccard < 0.30) - requires human review

### Quality Evaluation

The eval node performs comprehensive checks:
- Testability assessment
- Hallucination detection
- Deduplication analysis
- Schema compliance verification
- Coverage analysis

## Troubleshooting

### Common Issues

**Import Errors**: Ensure virtual environment is activated and dependencies are installed
```bash
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # Unix/Mac
pip install -r requirements.txt
```

**API Key Errors**: Verify environment variable is set
```bash
echo $ANTHROPIC_API_KEY
```

**File Not Found**: Check that input document path is correct
```bash
ls data/
```

### Logging

The system uses `structlog` for structured logging. Key events:
- `parse_started`: Document parsing begins
- `parse_completed`: Chunk counts and statistics
- `schema_discovery_complete`: Schema inference results
- `gate_decision`: Accept/review/reject decision
- `atomizer_complete`: Extraction statistics

## Documentation

Comprehensive documentation is available in the [wiki](wiki/) directory:

- **[Home](wiki/Home.md)** - Overview and quick start
- **[Architecture](wiki/Architecture.md)** - System design and folder structure
- **[Usage Guide](wiki/Usage-Guide.md)** - CLI and API usage
- **[Phase1-Parse-and-Chunk](wiki/Phase1-Parse-and-Chunk.md)** - Preprocessor node
- **[Phase1-Schema-Discovery-Agent](wiki/Phase1-Schema-Discovery-Agent.md)** - Schema discovery
- **[Phase1-Confidence-Scorer](wiki/Phase1-Confidence-Scorer.md)** - Confidence gate
- **[Phase1-GRC-Extractor](wiki/Phase1-GRC-Extractor.md)** - GRC extraction
- **[Phase1-Atomizer-Agent](wiki/Phase1-Atomizer-Agent.md)** - Requirement atomization
- **[Phase1-Eval](wiki/Phase1-Eval.md)** - Quality evaluation

## License

This project is provided as-is for regulatory compliance document processing.

## Technology Stack

- **Python 3.11+**: Primary language
- **Pydantic**: Data validation
- **structlog**: Structured logging
- **Anthropic Claude**: LLM provider
- **python-docx**: Document parsing
