# Kratos-Discover Wiki

This directory contains comprehensive documentation for the Kratos-Discover Agent1 pipeline.

## Documentation Structure

### General Documentation

| Page | Description |
|------|-------------|
| [Home](Home.md) | Wiki landing page and overview |
| [Installation Guide](Installation-Guide.md) | Setup and installation instructions |
| [Usage Guide](Usage-Guide.md) | CLI and API usage examples |
| [Configuration](Configuration.md) | Environment variables and settings |
| [Architecture](Architecture.md) | System design and components |
| [API Reference](API-Reference.md) | Programmatic API documentation |
| [Development Guide](Development-Guide.md) | Contributing and development workflow |
| [Deployment Guide](Deployment-Guide.md) | Docker and production deployment |
| [Troubleshooting](Troubleshooting.md) | Common issues and solutions |

### Pipeline Components

| Node | Page | Description |
|------|------|-------------|
| 1 | [Parse and Chunk](Phase1-Parse-and-Chunk.md) | Deterministic document parsing |
| 2 | [Schema Discovery](Phase1-Schema-Discovery-Agent.md) | Automatic schema inference |
| 3 | [Confidence Gate](Phase1-Confidence-Scorer.md) | Quality gate with thresholds |
| 3.5 | [GRC Extractor](Phase1-GRC-Extractor.md) | Policy/Risk/Control extraction |
| 4 | [Atomizer](Phase1-Atomizer-Agent.md) | Requirement atomization |
| 5 | [Eval](Phase1-Eval.md) | Quality assessment |

## Quick Links

### Getting Started
- [Installation](Installation-Guide.md#installation-steps)
- [Quick Start](Home.md#quick-start)
- [CLI Commands](Usage-Guide.md#cli-commands)

### Development
- [Development Setup](Development-Guide.md#development-setup)
- [Running Tests](Development-Guide.md#testing)
- [Code Style](Development-Guide.md#code-style)

### Reference
- [API Reference](API-Reference.md)
- [Configuration Options](Configuration.md#environment-variables)
- [Architecture Overview](Architecture.md#system-overview)

## Contributing to Documentation

To improve or extend the documentation:

1. Fork the repository
2. Edit the relevant markdown file in the `wiki/` directory
3. Follow the existing structure and style
4. Submit a pull request

## Documentation Standards

- Use clear, concise language
- Include code examples where applicable
- Keep table of contents updated
- Cross-reference related pages
- Use proper markdown formatting
- Do not use emojis or icons

## Viewing the Documentation

View the markdown files directly in your IDE or text editor. The wiki pages can also be accessed through GitHub's wiki feature if enabled.

## License

This documentation is part of the Kratos-Discover project and follows the same license terms.
