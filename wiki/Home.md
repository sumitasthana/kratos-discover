# Kratos-Discover Wiki

Welcome to the Kratos-Discover documentation. This wiki provides comprehensive information about the Agent1 pipeline for automated regulatory document processing and GRC component extraction.

## Table of Contents

### General Documentation
- [Home](Home.md) - You are here
- [Installation Guide](Installation-Guide.md) - Setup and installation instructions
- [Usage Guide](Usage-Guide.md) - How to use the CLI
- [Configuration](Configuration.md) - Environment variables and configuration options
- [Architecture](Architecture.md) - System design and components
- [API Reference](API-Reference.md) - Programmatic API documentation
- [Development Guide](Development-Guide.md) - Contributing and development workflow
- [Deployment Guide](Deployment-Guide.md) - Docker and production deployment
- [Troubleshooting](Troubleshooting.md) - Common issues and solutions

### Pipeline Components
- [Parse and Chunk](Phase1-Parse-and-Chunk.md) - Node 1: Deterministic document parsing and chunking
- [Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md) - Node 2: Automatic schema inference from document structure
- [Confidence Gate](Phase1-Confidence-Scorer.md) - Node 3: Quality gate with configurable thresholds
- [GRC Extractor](Phase1-GRC-Extractor.md) - Node 3.5: Policy, Risk, and Control extraction
- [Atomizer Agent](Phase1-Atomizer-Agent.md) - Node 4: Requirement atomization
- [Eval](Phase1-Eval.md) - Node 5: Pipeline evaluation and quality metrics
- [Router](Phase1-Router.md) - Routing layer for pipeline decisions

## What is Kratos-Discover?

Kratos-Discover is an LLM-powered document processing system that extracts structured regulatory requirements, policies, risks, and controls from compliance documents such as FDIC 370 GRC libraries. The system uses a 5-node pipeline architecture with Claude as the primary LLM provider.

### Key Capabilities

- **Automated Extraction**: Extract atomic requirements from regulatory documents
- **GRC Component Extraction**: Identify and structure policies, risks, and controls from Word tables
- **Schema Discovery**: Automatically infer document structure and entity types
- **Confidence Scoring**: Multi-tier confidence calibration with grounding verification
- **Quality Evaluation**: Comprehensive eval checks including testability, hallucination detection, and schema compliance

## Quick Start

1. **Install**: Follow the [Installation Guide](Installation-Guide.md)
2. **Configure**: Set up your `.env` file with `ANTHROPIC_API_KEY`
3. **Run**: Process your first document

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run full pipeline
python cli.py atomize --input "path/to/document.docx"
```

## Pipeline Overview

The Agent1 pipeline consists of five nodes executed sequentially:

| Node | Name | Description |
|------|------|-------------|
| 1 | Preprocessor | Parse DOCX into deterministic chunks |
| 2 | Schema Discovery | Infer document structure using Claude |
| 3 | Confidence Gate | Validate schema confidence meets thresholds |
| 3.5 | GRC Extractor | Extract Policy/Risk/Control components from tables |
| 4 | Atomizer | Extract atomic regulatory requirements |
| 5 | Eval | Quality assessment and failure classification |

## Use Cases

- **Regulatory Compliance**: Process FDIC 370 and similar regulatory documents
- **GRC Automation**: Extract governance, risk, and compliance components from Word tables
- **Policy Management**: Convert policy documents into structured, machine-readable data
- **Requirements Extraction**: Atomize complex regulatory text into testable requirements

## Technology Stack

- **LLM Provider**: Anthropic Claude (claude-sonnet-4-20250514)
- **Data Validation**: Pydantic
- **Document Processing**: python-docx
- **Logging**: structlog
- **Testing**: pytest

## Additional Resources

- [GitHub Repository](https://github.com/sumitasthana/kratos-discover)
- [Report Issues](https://github.com/sumitasthana/kratos-discover/issues)

## Contributing

See the [Development Guide](Development-Guide.md) for details on:
- Setting up your development environment
- Running tests
- Code style guidelines
- Submitting pull requests

## License

This project is provided as-is for regulatory compliance document processing.

---

**Need Help?** Check the [Troubleshooting](Troubleshooting.md) guide or [open an issue](https://github.com/sumitasthana/kratos-discover/issues).
