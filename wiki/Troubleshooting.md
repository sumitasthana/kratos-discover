# Troubleshooting Guide

Common issues and solutions for Kratos-Discover.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Runtime Issues](#runtime-issues)
- [LLM Provider Issues](#llm-provider-issues)
- [Document Processing Issues](#document-processing-issues)
- [Performance Issues](#performance-issues)
- [Debugging Tips](#debugging-tips)

## Installation Issues

### Python Version Error

**Problem**: `Python 3.8 or higher is required`

**Solution**:
1. Check your Python version:
```bash
python --version
# or
python3 --version
```

2. Install Python 3.8+:
- **macOS**: `brew install python@3.9`
- **Ubuntu/Debian**: `sudo apt-get install python3.9`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

3. Use the correct Python version:
```bash
python3.9 -m venv .venv
```

### Virtual Environment Not Activating

**Problem**: Virtual environment activation fails

**Solutions**:

**Windows PowerShell**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

**Windows Command Prompt**:
```cmd
.venv\Scripts\activate.bat
```

**Unix/macOS**:
```bash
source .venv/bin/activate
```

**Verify Activation**:
```bash
which python  # Should show .venv/bin/python
```

### Dependency Installation Fails

**Problem**: `pip install -r requirements.txt` fails

**Solutions**:

**1. Update pip**:
```bash
pip install --upgrade pip setuptools wheel
```

**2. Install build tools** (Linux):
```bash
sudo apt-get update
sudo apt-get install python3-dev build-essential
```

**3. Install build tools** (macOS):
```bash
xcode-select --install
```

**4. Install build tools** (Windows):
- Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

**5. Install dependencies one by one**:
```bash
pip install langchain
pip install langchain-openai
pip install langchain-anthropic
# ... continue for each package
```

### Import Errors After Installation

**Problem**: `ModuleNotFoundError: No module named 'langchain'`

**Solutions**:

**1. Verify virtual environment is activated**:
```bash
# You should see (.venv) in your prompt
# If not, activate it
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate  # Windows
```

**2. Reinstall dependencies**:
```bash
pip install -r requirements.txt --force-reinstall
```

**3. Check Python interpreter**:
```bash
which python  # Should point to .venv
python -c "import langchain; print(langchain.__file__)"
```

## Configuration Issues

### API Key Not Found

**Problem**: `Error: OPENAI_API_KEY not found`

**Solutions**:

**1. Check .env file exists**:
```bash
ls -la .env
```

**2. Create from example**:
```bash
cp config/.env.example .env
```

**3. Verify API key in .env**:
```bash
cat .env | grep API_KEY
```

**4. Check environment loading**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
print(os.getenv("OPENAI_API_KEY")[:10])  # Should print first 10 chars
```

**5. Set environment variable directly** (temporary):
```bash
export OPENAI_API_KEY=sk-your-key-here  # Unix/macOS
set OPENAI_API_KEY=sk-your-key-here  # Windows
```

### Invalid API Key

**Problem**: `AuthenticationError: Incorrect API key`

**Solutions**:

**1. Verify API key format**:
- OpenAI keys start with `sk-`
- Anthropic keys start with `sk-ant-`

**2. Check for extra spaces**:
```bash
# Remove any whitespace
OPENAI_API_KEY=sk-yourkey  # No quotes, no spaces
```

**3. Generate new API key**:
- OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Anthropic: [console.anthropic.com](https://console.anthropic.com/)

**4. Verify key permissions**:
- Ensure API key has necessary permissions
- Check if key is active/not expired

### Configuration File Not Found

**Problem**: `FileNotFoundError: prompts/registry.yaml not found`

**Solutions**:

**1. Verify you're in the correct directory**:
```bash
pwd  # Should be kratos-discover/
ls prompts/  # Should show registry.yaml
```

**2. Check file exists**:
```bash
ls -la prompts/registry.yaml
```

**3. Restore from git** (if accidentally deleted):
```bash
git checkout prompts/registry.yaml
```

## Runtime Issues

### File Not Found Error

**Problem**: `FileNotFoundError: data/document.docx not found`

**Solutions**:

**1. Check file exists**:
```bash
ls -la data/document.docx
```

**2. Use absolute path**:
```bash
python cli.py --input /full/path/to/document.docx
```

**3. Check file permissions**:
```bash
chmod 644 data/document.docx  # Unix/macOS
```

**4. Verify filename** (case-sensitive on Unix):
```bash
ls data/  # Check exact filename
```

### Validation Error

**Problem**: `ValidationError: X validation errors`

**Solutions**:

**1. Enable debug mode**:
```bash
python cli.py --debug --dump-debug --provider openai
```

**2. Check debug output**:
```bash
cat outputs/debug_*/raw_rules.json  # See what LLM returned
```

**3. Try different prompt version**:
```bash
python cli.py --prompt-version v1.1 --provider openai
```

**4. Check LLM output format**:
- Ensure LLM is returning valid JSON
- Verify all required fields are present

### No Rules Extracted

**Problem**: Pipeline runs but returns 0 rules

**Solutions**:

**1. Enable debug mode**:
```bash
python cli.py --debug --dump-debug --log-level DEBUG
```

**2. Check each pipeline stage**:
```bash
# Check segmentation
cat outputs/debug_*/segments.json

# Check raw extraction
cat outputs/debug_*/raw_rules.json

# Check validation
cat outputs/debug_*/validated_rules.json
```

**3. Verify document content**:
- Ensure document has extractable content
- Check document format is supported

**4. Try different LLM provider**:
```bash
python cli.py --provider anthropic  # Instead of openai
```

**5. Review grounding threshold**:
- Rules may be filtered out during grounding
- Check grounding scores in debug output

## LLM Provider Issues

### OpenAI Rate Limit

**Problem**: `RateLimitError: Rate limit exceeded`

**Solutions**:

**1. Wait and retry**:
```bash
# Wait a minute and try again
sleep 60
python cli.py --provider openai
```

**2. Use exponential backoff**:
```python
import time
from openai import RateLimitError

max_retries = 3
for i in range(max_retries):
    try:
        rules = agent.extract_rules(document_path)
        break
    except RateLimitError:
        wait_time = 2 ** i
        time.sleep(wait_time)
```

**3. Check quota**:
- Visit [platform.openai.com/usage](https://platform.openai.com/usage)
- Verify you have remaining quota

**4. Upgrade API plan**:
- Consider upgrading for higher rate limits

### Anthropic Timeout

**Problem**: `TimeoutError: Request timed out`

**Solutions**:

**1. Increase timeout**:
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-opus-4-20250805",
    timeout=300  # 5 minutes instead of default 120
)
```

**2. Process smaller segments**:
- Split large documents into smaller sections
- Process incrementally

**3. Use faster model**:
```bash
# Use Haiku instead of Opus
CLAUDE_MODEL=claude-3-haiku-20240307
```

### Model Not Available

**Problem**: `Model 'gpt-4o-mini' not found`

**Solutions**:

**1. Check model name**:
```bash
# Verify exact model name
echo $OPENAI_MODEL
```

**2. Use available model**:
```bash
# Try different model
export OPENAI_MODEL=gpt-3.5-turbo
```

**3. Check API access**:
- Verify your API key has access to the model
- Some models require specific API tiers

## Document Processing Issues

### Unsupported File Format

**Problem**: `ValueError: Unsupported file format`

**Solutions**:

**1. Convert to supported format**:
- Convert to DOCX, PDF, or HTML
- Use LibreOffice or Microsoft Word for conversion

**2. Check file extension**:
```bash
file document.pdf  # Verify actual file type
```

**3. For scanned PDFs**:
- Use OCR tool to extract text first
- Convert to searchable PDF

### Encoding Error

**Problem**: `UnicodeDecodeError: 'utf-8' codec can't decode`

**Solutions**:

**1. Convert file encoding**:
```bash
iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt
```

**2. Specify encoding in code**:
```python
with open(file_path, 'r', encoding='latin-1') as f:
    content = f.read()
```

**3. Remove problematic characters**:
```bash
# Remove non-UTF-8 characters
iconv -f UTF-8 -t UTF-8 -c input.txt > output.txt
```

### Document Too Large

**Problem**: Document processing fails or takes too long

**Solutions**:

**1. Split document into sections**:
- Process sections separately
- Combine results afterward

**2. Use faster model**:
```bash
export OPENAI_MODEL=gpt-4o-mini  # Faster than gpt-4o
```

**3. Adjust segment size**:
- Modify segmentation logic to create smaller segments

**4. Increase timeouts**:
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    timeout=600  # 10 minutes
)
```

## Performance Issues

### Slow Processing

**Problem**: Processing takes very long

**Solutions**:

**1. Use faster model**:
```bash
# OpenAI
export OPENAI_MODEL=gpt-4o-mini

# Anthropic
export CLAUDE_MODEL=claude-3-haiku-20240307
```

**2. Process in parallel**:
```bash
# Process multiple documents in parallel
for file in data/*.docx; do
  python cli.py --input "$file" &
done
wait
```

**3. Enable caching** (if supported):
```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())
```

**4. Optimize segmentation**:
- Fewer, larger segments = fewer API calls
- More, smaller segments = better parallel processing

### High API Costs

**Problem**: API costs are too high

**Solutions**:

**1. Use cheaper model**:
```bash
export OPENAI_MODEL=gpt-4o-mini  # Much cheaper than gpt-4o
```

**2. Optimize prompts**:
- Reduce prompt length
- Remove unnecessary examples

**3. Implement caching**:
- Cache LLM responses
- Avoid re-processing same content

**4. Monitor usage**:
```bash
# Track API calls
python cli.py --log-level DEBUG 2>&1 | grep "API call"
```

## Debugging Tips

### Enable Debug Mode

```bash
python cli.py --debug --dump-debug --log-level DEBUG --provider openai
```

This creates debug artifacts:
```
outputs/debug_TIMESTAMP/
├── raw_rules.json          # Initial LLM output
├── validated_rules.json    # After validation
└── deduped_rules.json      # After deduplication
```

### Examine Debug Output

```bash
# View raw LLM response
cat outputs/debug_*/raw_rules.json | jq .

# Count rules at each stage
echo "Raw: $(cat outputs/debug_*/raw_rules.json | jq '. | length')"
echo "Validated: $(cat outputs/debug_*/validated_rules.json | jq '. | length')"
echo "Deduped: $(cat outputs/debug_*/deduped_rules.json | jq '. | length')"
```

### Check Logs

```bash
# Save logs to file
python cli.py --provider openai --log-level DEBUG 2>&1 | tee debug.log

# Search for errors
grep ERROR debug.log
grep WARNING debug.log
```

### Test with Small Document

```bash
# Create a minimal test document
echo "Rule: Data must be validated daily." > test.txt

# Test extraction
python cli.py --input test.txt --provider openai --debug
```

### Verify API Connectivity

```bash
# Test OpenAI connection
python -c "
from langchain_openai import ChatOpenAI
import os
llm = ChatOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print(llm.invoke('Hello').content)
"

# Test Anthropic connection
python -c "
from langchain_anthropic import ChatAnthropic
import os
llm = ChatAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
print(llm.invoke('Hello').content)
"
```

### Use Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()

# Run with debugger
python -m pdb cli.py --provider openai
```

## Getting Help

If you can't resolve your issue:

1. **Search existing issues**: [GitHub Issues](https://github.com/sumitasthana/kratos-discover/issues)
2. **Check documentation**: Review all wiki pages
3. **Create detailed issue**:
   - Include error messages
   - Provide steps to reproduce
   - Share debug output (without sensitive data)
   - Specify your environment (OS, Python version, etc.)

### Issue Template

```markdown
**Problem Description**
Clear description of the issue

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Error Messages**
```
Paste error messages here
```

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.9.7]
- Kratos-Discover Version: [e.g., commit hash or tag]

**Debug Output**
Attach debug artifacts if available
```

---

**Still stuck?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) with details above.
