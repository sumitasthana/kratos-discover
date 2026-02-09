# Installation Guide

This guide will help you install and set up Kratos-Discover on your system.

## System Requirements

### Prerequisites

- **Python**: Version 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 4GB RAM recommended
- **Storage**: At least 500MB free disk space
- **API Keys**: OpenAI or Anthropic API key (or both)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/sumitasthana/kratos-discover.git
cd kratos-discover
```

### 2. Create Virtual Environment

Using a virtual environment is highly recommended to isolate dependencies.

#### On Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### On Unix or macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- LangChain and LangGraph
- OpenAI and Anthropic SDKs
- Pydantic for data validation
- Document processing libraries (python-docx, pypdf, beautifulsoup4)
- Testing framework (pytest)

### 4. Configure Environment

Copy the example environment file and add your API keys:

```bash
cp config/.env.example .env
```

Edit the `.env` file with your preferred text editor:

```bash
# For Unix/macOS
nano .env

# For Windows
notepad .env
```

Add your API keys:

```env
# Required: At least one LLM provider API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Model Configuration
CLAUDE_MODEL=claude-opus-4-20250805
OPENAI_MODEL=gpt-4o-mini

# Document Path
FDIC_370_PATH=data/FDIC_370_GRC_Library_National_Bank.docx

# Default Settings
LLM_PROVIDER=openai
RULE_AGENT_MODE=rules
RULE_AGENT_OUTPUT_DIR=outputs
RULE_AGENT_LOG_LEVEL=INFO
```

### 5. Prepare Data Directory

Create the data directory and add your source documents:

```bash
mkdir -p data
# Copy your FDIC 370 document to the data/ directory
```

### 6. Verify Installation

Test that everything is working:

```bash
# Check Python version
python --version

# Verify dependencies
pip list | grep langchain

# Run tests
pytest
```

## Obtaining API Keys

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new API key
5. Copy and save the key securely

**Note**: OpenAI charges per token. Monitor your usage to avoid unexpected costs.

### Anthropic API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new API key
5. Copy and save the key securely

**Note**: Anthropic also charges per token. Check their pricing for details.

## Docker Installation (Alternative)

For containerized deployment, see the [Deployment Guide](Deployment-Guide.md).

```bash
# Build Docker image
docker build -t kratos-discover .

# Run with environment file
docker run --env-file .env kratos-discover
```

## Troubleshooting Installation

### Common Issues

#### Python Version Error

**Error**: `Python 3.8 or higher is required`

**Solution**: Install Python 3.8+ from [python.org](https://www.python.org/downloads/)

#### Virtual Environment Not Activating

**Solution**: 
- On Windows PowerShell, you may need to run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Ensure you're using the correct activation script for your shell

#### Dependency Installation Fails

**Error**: `pip install` fails with compilation errors

**Solutions**:
- Update pip: `pip install --upgrade pip`
- Install build tools (on Linux): `sudo apt-get install python3-dev build-essential`
- On Windows, install Microsoft C++ Build Tools

#### Import Errors After Installation

**Solution**:
- Verify virtual environment is activated (you should see `(.venv)` in your prompt)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

## Next Steps

Once installation is complete:

1. Review the [Configuration Guide](Configuration.md) for detailed settings
2. Follow the [Usage Guide](Usage-Guide.md) to process your first document
3. Explore the [API Reference](API-Reference.md) for programmatic usage

## Updating

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
```

---

**Need help?** Visit the [Troubleshooting](Troubleshooting.md) page or [open an issue](https://github.com/sumitasthana/kratos-discover/issues).
