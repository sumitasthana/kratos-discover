# Kratos-Discover Wiki

Welcome to the Kratos-Discover documentation! This wiki provides comprehensive information about the production-grade Rule Agent for automated regulatory document processing.

## 📖 Table of Contents

- [Home](Home.md) - You are here
- [Installation Guide](Installation-Guide.md) - Setup and installation instructions
- [Usage Guide](Usage-Guide.md) - How to use the CLI and API
- [Configuration](Configuration.md) - Environment variables and configuration options
- [Architecture](Architecture.md) - System design and components
- [API Reference](API-Reference.md) - Programmatic API documentation
- [Development Guide](Development-Guide.md) - Contributing and development workflow
- [Deployment Guide](Deployment-Guide.md) - Docker and production deployment
- [Troubleshooting](Troubleshooting.md) - Common issues and solutions

## 🎯 What is Kratos-Discover?

Kratos-Discover is an intelligent document processing system that extracts structured regulatory rules, policies, risks, and controls from compliance documents. Built on LangGraph and LangChain, it leverages large language models to transform unstructured regulatory text into actionable, machine-readable data.

### Key Capabilities

- **Automated Extraction**: Extract rules, policies, risks, and controls from regulatory documents
- **Multi-Provider Support**: Works with OpenAI GPT and Anthropic Claude models
- **Structured Output**: Schema-based validation and structured data models
- **Quality Assurance**: Multi-stage validation, deduplication, and grounding verification
- **Flexible Pipeline**: 5-node LangGraph workflow with debug capabilities

## 🚀 Quick Start

1. **Install**: Follow the [Installation Guide](Installation-Guide.md)
2. **Configure**: Set up your environment using the [Configuration](Configuration.md) guide
3. **Run**: Process your first document with the [Usage Guide](Usage-Guide.md)

```bash
# Basic extraction
python cli.py --provider openai --input data/document.docx --output results.json
```

## 📋 Use Cases

- **Regulatory Compliance**: Process FDIC 370 and similar regulatory documents
- **GRC Automation**: Extract governance, risk, and compliance components
- **Policy Management**: Convert policy documents into structured data
- **Risk Assessment**: Identify and catalog risks from unstructured sources

## 🔧 Technology Stack

- **Core Framework**: LangGraph, LangChain
- **LLM Providers**: OpenAI GPT-4, Anthropic Claude
- **Data Validation**: Pydantic
- **Document Processing**: python-docx, pypdf, beautifulsoup4
- **Testing**: pytest

## 📚 Additional Resources

- [GitHub Repository](https://github.com/sumitasthana/kratos-discover)
- [Report Issues](https://github.com/sumitasthana/kratos-discover/issues)
- [View Changelog](https://github.com/sumitasthana/kratos-discover/commits)

## 🤝 Contributing

We welcome contributions! See the [Development Guide](Development-Guide.md) for details on:
- Setting up your development environment
- Running tests
- Code style guidelines
- Submitting pull requests

## 📄 License

This project is provided as-is for regulatory compliance document processing.

---

**Need Help?** Check the [Troubleshooting](Troubleshooting.md) guide or [open an issue](https://github.com/sumitasthana/kratos-discover/issues).
