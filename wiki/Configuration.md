# Configuration Guide

Comprehensive guide to configuring Kratos-Discover for your environment.

## Table of Contents

- [Environment Variables](#environment-variables)
- [LLM Configuration](#llm-configuration)
- [Prompt Versioning](#prompt-versioning)
- [Document Processing](#document-processing)
- [Output Configuration](#output-configuration)
- [Advanced Settings](#advanced-settings)

## Environment Variables

Kratos-Discover uses environment variables for configuration. These can be set in:
1. `.env` file in the project root
2. System environment variables
3. Command-line arguments (takes precedence)

### Creating Your Configuration

```bash
# Copy the example file
cp config/.env.example .env

# Edit with your settings
nano .env  # or your preferred editor
```

### Complete Environment Variables Reference

#### LLM Provider Keys

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
CLAUDE_MODEL=claude-opus-4-20250805
```

**Notes**:
- You need at least one API key configured
- Both can be configured to switch between providers
- API keys are sensitive - never commit them to version control

#### Document Configuration

```env
# Default document path
FDIC_370_PATH=data/FDIC_370_GRC_Library_National_Bank.docx
```

**Supported Formats**:
- `.docx` - Microsoft Word documents
- `.pdf` - PDF files
- `.html` - HTML documents

#### Application Settings

```env
# Default LLM provider (openai or anthropic)
LLM_PROVIDER=openai

# Extraction mode (rules or grc_components)
RULE_AGENT_MODE=rules

# Output directory for results
RULE_AGENT_OUTPUT_DIR=outputs

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
RULE_AGENT_LOG_LEVEL=INFO
```

## LLM Configuration

### OpenAI Configuration

#### Available Models

| Model | Speed | Cost | Accuracy | Best For |
|-------|-------|------|----------|----------|
| gpt-4o-mini | Fast | Low | Good | Development, testing |
| gpt-4o | Medium | Medium | Excellent | Production use |
| gpt-4-turbo | Medium | Medium | Excellent | Complex documents |

#### Example Configuration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,        # Deterministic output
    max_tokens=4000,      # Maximum response length
    timeout=120,          # Request timeout in seconds
    max_retries=3         # Retry failed requests
)
```

### Anthropic Claude Configuration

#### Available Models

| Model | Speed | Cost | Accuracy | Best For |
|-------|-------|------|----------|----------|
| claude-3-haiku | Very Fast | Low | Good | Quick processing |
| claude-3-sonnet | Medium | Medium | Very Good | Balanced use |
| claude-opus-4 | Slow | High | Excellent | Highest accuracy |

#### Example Configuration

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-opus-4-20250805",
    max_tokens=3000,
    temperature=0,
    timeout=120
)
```

### Choosing a Provider

**Use OpenAI when**:
- Cost is a primary concern
- Faster processing is needed
- Document structure is straightforward

**Use Anthropic when**:
- Maximum accuracy is required
- Processing complex regulatory language
- Budget allows for premium service

## Prompt Versioning

Kratos-Discover uses versioned prompts for reproducibility and iterative improvement.

### Prompt Registry Structure

```
prompts/
├── registry.yaml                # Active version configuration
└── rule_extraction/
    ├── v1.0.yaml               # Version 1.0
    ├── v1.1.yaml               # Version 1.1
    └── v1.2.yaml               # Version 1.2 (latest)
```

### Viewing Active Prompt Version

```bash
cat prompts/registry.yaml
```

Example output:
```yaml
rule_extraction:
  active_version: v1.2
  description: "Rule extraction from regulatory documents"
```

### Changing the Active Version

#### Method 1: Edit Registry (Permanent)

```bash
nano prompts/registry.yaml
```

Change `active_version`:
```yaml
rule_extraction:
  active_version: v1.1  # Changed from v1.2
  description: "Rule extraction from regulatory documents"
```

#### Method 2: CLI Override (Temporary)

```bash
python cli.py --prompt-version v1.1 --provider openai
```

### Creating a New Prompt Version

1. Copy the latest version:
```bash
cp prompts/rule_extraction/v1.2.yaml prompts/rule_extraction/v1.3.yaml
```

2. Edit the new version with your improvements

3. Update the registry to use the new version:
```yaml
rule_extraction:
  active_version: v1.3
  description: "Rule extraction from regulatory documents"
```

### Prompt Version Best Practices

- **Document Changes**: Add comments explaining modifications
- **Test Thoroughly**: Validate new versions on sample documents
- **Version Control**: Commit prompt changes with descriptive messages
- **Rollback Safety**: Keep previous versions for easy rollback

## Document Processing

### Input Document Configuration

#### File Path Configuration

**Via Environment Variable**:
```env
FDIC_370_PATH=data/my_document.docx
```

**Via CLI**:
```bash
python cli.py --input data/my_document.docx
```

**Via API**:
```python
rules = agent.extract_rules(document_path="data/my_document.docx")
```

#### Supported File Formats

**DOCX Files**:
- Microsoft Word 2007+ (.docx)
- OpenOffice/LibreOffice ODT (with conversion)

**PDF Files**:
- Text-based PDFs (not scanned images)
- PDFs with selectable text

**HTML Files**:
- Clean HTML structure recommended
- Supports basic formatting

### Processing Options

#### Segmentation

The system automatically segments documents into logical sections. Control this via prompts.

#### Extraction Modes

Configure the extraction mode:

```env
RULE_AGENT_MODE=rules  # or grc_components
```

Or via CLI:
```bash
python cli.py --mode grc_components
```

## Output Configuration

### Output Directory

**Default**: `outputs/` directory

**Custom Directory**:
```env
RULE_AGENT_OUTPUT_DIR=./results
```

Or via CLI:
```bash
python cli.py --output-dir ./my_results
```

### Output File Naming

**Auto-generated** (default):
- Format: `rules_YYYYMMDD_HHMMSS.json`
- Example: `rules_20250115_143022.json`

**Custom Filename**:
```bash
python cli.py --output my_custom_name.json
```

**Full Path**:
```bash
python cli.py --output /path/to/results/output.json --output-dir /path/to/results
```

### Output Format

Results are saved as JSON with proper formatting:

```json
[
  {
    "rule_id": "RULE_001",
    "category": "rule",
    "rule_type": "data_quality_threshold",
    "rule_description": "Description here",
    "grounded_in": "Source reference",
    "confidence": 0.95,
    "attributes": {},
    "metadata": {
      "source_block": "Section text",
      "block_index": 0,
      "validation_status": "valid"
    }
  }
]
```

### Debug Output

Enable debug mode to save intermediate artifacts:

```bash
python cli.py --debug --dump-debug
```

Creates a debug directory:
```
outputs/debug_20250115_143022/
├── raw_rules.json          # Initial extraction
├── validated_rules.json    # After validation
└── deduped_rules.json      # After deduplication
```

## Advanced Settings

### Logging Configuration

#### Log Levels

```env
RULE_AGENT_LOG_LEVEL=DEBUG  # Most verbose
RULE_AGENT_LOG_LEVEL=INFO   # Standard (default)
RULE_AGENT_LOG_LEVEL=WARNING
RULE_AGENT_LOG_LEVEL=ERROR  # Least verbose
```

#### Log Output

Logs are written to:
- **Console**: Standard output (stdout)
- **File**: Can be redirected with shell

```bash
# Save logs to file
python cli.py --provider openai 2>&1 | tee execution.log
```

### Performance Tuning

#### Timeout Settings

Adjust LLM timeouts for large documents:

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    timeout=300  # 5 minutes
)
```

#### Rate Limiting

Implement delays between API calls:

```python
import time

for document in documents:
    rules = agent.extract_rules(document_path=document)
    time.sleep(2)  # 2-second delay between requests
```

### Security Configuration

#### API Key Management

**Best Practices**:
1. Never commit `.env` to version control
2. Use environment-specific `.env` files (`.env.dev`, `.env.prod`)
3. Rotate API keys periodically
4. Use minimal API key permissions

#### Secure Storage

**For Production**:
- Use secret management systems (AWS Secrets Manager, HashiCorp Vault)
- Set environment variables at the system level
- Use encrypted configuration files

### Multi-Environment Setup

#### Development Environment

`.env.development`:
```env
OPENAI_API_KEY=sk-dev-key
OPENAI_MODEL=gpt-4o-mini
RULE_AGENT_LOG_LEVEL=DEBUG
```

#### Production Environment

`.env.production`:
```env
OPENAI_API_KEY=sk-prod-key
OPENAI_MODEL=gpt-4o
RULE_AGENT_LOG_LEVEL=INFO
```

**Load Specific Environment**:
```bash
cp .env.production .env
python cli.py --provider openai
```

## Configuration Examples

### Example 1: Development Setup

```env
# .env for development
OPENAI_API_KEY=sk-your-dev-key
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
RULE_AGENT_MODE=rules
RULE_AGENT_OUTPUT_DIR=dev_outputs
RULE_AGENT_LOG_LEVEL=DEBUG
FDIC_370_PATH=data/test_document.docx
```

### Example 2: Production Setup

```env
# .env for production
ANTHROPIC_API_KEY=sk-ant-your-prod-key
CLAUDE_MODEL=claude-opus-4-20250805
LLM_PROVIDER=anthropic
RULE_AGENT_MODE=grc_components
RULE_AGENT_OUTPUT_DIR=/var/data/outputs
RULE_AGENT_LOG_LEVEL=INFO
```

### Example 3: Testing Setup

```env
# .env for testing
OPENAI_API_KEY=sk-your-test-key
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
RULE_AGENT_MODE=rules
RULE_AGENT_OUTPUT_DIR=test_outputs
RULE_AGENT_LOG_LEVEL=WARNING
```

## Validation

Verify your configuration:

```bash
# Check environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10])"

# Run a test extraction
python cli.py --provider openai --log-level DEBUG
```

## Next Steps

- Review the [Usage Guide](Usage-Guide.md) for running extractions
- Check the [Troubleshooting](Troubleshooting.md) guide for common issues
- Explore [Advanced Features](API-Reference.md) in the API documentation

---

**Need Help?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) with your configuration question.
