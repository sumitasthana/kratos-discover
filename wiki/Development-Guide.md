# Development Guide

Guide for developers who want to contribute to or extend Kratos-Discover.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Code Style](#code-style)
- [Prompt Development](#prompt-development)
- [Adding Features](#adding-features)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.8+
- Git
- Virtual environment tool (venv or virtualenv)
- Code editor (VS Code, PyCharm, etc.)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/sumitasthana/kratos-discover.git
cd kratos-discover

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Unix/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
pip install pytest pytest-cov black flake8 mypy

# Configure environment
cp config/.env.example .env
# Edit .env with your API keys
```

### IDE Configuration

#### VS Code

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Select `.venv` as interpreter
3. Enable pytest as test runner
4. Configure Black as code formatter

## Project Structure

```
kratos-discover/
├── cli.py                      # Command-line interface
├── rule_agent.py               # Core RuleAgent implementation
├── prompt_registry.py          # Prompt version management
├── requirements.txt            # Python dependencies
│
├── config/
│   ├── .env.example            # Environment template
│   └── rule_attributes_schema.yaml
│
├── prompts/
│   ├── registry.yaml           # Active prompt versions
│   └── rule_extraction/        # Versioned prompts
│       ├── v1.0.yaml
│       ├── v1.1.yaml
│       └── v1.2.yaml
│
├── tests/
│   ├── conftest.py             # Pytest configuration
│   ├── test_cli.py             # CLI tests
│   ├── test_rule_agent.py      # RuleAgent tests
│   └── test_prompt_registry.py # PromptRegistry tests
│
├── data/                       # Input documents (gitignored)
├── outputs/                    # Extraction results (gitignored)
└── wiki/                       # Documentation
```

### Key Files

**cli.py**:
- Argument parsing
- LLM initialization
- Pipeline execution
- Output handling

**rule_agent.py**:
- RuleAgent class
- LangGraph pipeline
- Data models
- Extraction logic

**prompt_registry.py**:
- Prompt loading
- Version management
- Registry configuration

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_rule_agent.py

# Run specific test
pytest tests/test_rule_agent.py::test_extract_rules

# Run with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Writing Tests

#### Test Structure

```python
# tests/test_feature.py
import pytest
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

class TestFeature:
    """Test suite for Feature"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        # Arrange
        expected = "result"
        
        # Act
        actual = function_to_test()
        
        # Assert
        assert actual == expected
    
    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            function_that_should_fail()
```

#### Fixtures

Use fixtures for common setup:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

@pytest.fixture
def registry():
    """Provide PromptRegistry instance"""
    return PromptRegistry(base_dir=Path("."))

@pytest.fixture
def mock_llm():
    """Provide mock LLM for testing"""
    # Return mock LLM instance
    pass

@pytest.fixture
def agent(registry, mock_llm):
    """Provide RuleAgent instance"""
    return RuleAgent(registry=registry, llm=mock_llm)
```

#### Mocking LLM Calls

```python
from unittest.mock import Mock, patch

def test_extraction_with_mock_llm():
    """Test extraction with mocked LLM"""
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(
        content='{"rules": [{"rule_id": "TEST_001"}]}'
    )
    
    agent = RuleAgent(registry=registry, llm=mock_llm)
    rules = agent.extract_rules("test_doc.docx")
    
    assert len(rules) > 0
    assert rules[0].rule_id == "TEST_001"
```

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage for core logic
- **Integration Tests**: Test full pipeline with mock data
- **End-to-End Tests**: Test with real (small) documents

## Code Style

### Style Guide

Follow [PEP 8](https://peps.python.org/pep-0008/) Python style guide.

### Formatting

Use **Black** for automatic formatting:

```bash
# Format all files
black .

# Check formatting without changes
black --check .

# Format specific file
black rule_agent.py
```

### Linting

Use **flake8** for linting:

```bash
# Lint all files
flake8 .

# Lint specific file
flake8 rule_agent.py

# With configuration
flake8 --max-line-length=88 --ignore=E501,W503
```

Create `.flake8` config:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, E501, W503
exclude = .git, __pycache__, .venv
```

### Type Checking

Use **mypy** for type checking:

```bash
# Type check all files
mypy .

# Type check specific file
mypy rule_agent.py
```

Create `mypy.ini`:

```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
```

### Documentation

Use **docstrings** for all public functions and classes:

```python
def extract_rules(self, document_path: str) -> List[Rule]:
    """Extract regulatory rules from a document.
    
    Args:
        document_path: Path to the input document (DOCX, PDF, or HTML)
        
    Returns:
        List of extracted and validated Rule objects
        
    Raises:
        FileNotFoundError: If document_path doesn't exist
        ValidationError: If extracted data fails validation
        
    Example:
        >>> agent = RuleAgent(registry, llm)
        >>> rules = agent.extract_rules("data/doc.docx")
        >>> print(len(rules))
        42
    """
    pass
```

## Prompt Development

### Prompt Structure

Prompts are stored as YAML files:

```yaml
# prompts/rule_extraction/v1.3.yaml
version: v1.3
task: rule_extraction
description: "Extract regulatory rules from document sections"

prompt: |
  You are a regulatory compliance expert. Extract all rules from the following document section.
  
  For each rule, provide:
  - rule_id: A unique identifier
  - rule_description: Clear description of the rule
  - category: Type of rule (rule, control, risk)
  - confidence: Your confidence in this extraction (0.5 to 0.99)
  
  Return JSON format:
  {
    "rules": [
      {
        "rule_id": "RULE_001",
        "rule_description": "...",
        ...
      }
    ]
  }
  
  Document section:
  {section_text}

schema:
  type: object
  properties:
    rules:
      type: array
      items:
        type: object
        required: ["rule_id", "rule_description", "category"]
```

### Creating New Prompt Versions

1. **Copy Latest Version**:
```bash
cp prompts/rule_extraction/v1.2.yaml prompts/rule_extraction/v1.3.yaml
```

2. **Edit Prompt**:
- Update `version` field
- Modify `prompt` text
- Update `description` if needed
- Adjust `schema` if data model changes

3. **Test New Version**:
```bash
python cli.py --prompt-version v1.3 --provider openai --input test_doc.docx
```

4. **Compare Results**:
```bash
# Test with old version
python cli.py --prompt-version v1.2 --output results_v1.2.json

# Test with new version
python cli.py --prompt-version v1.3 --output results_v1.3.json

# Compare
diff results_v1.2.json results_v1.3.json
```

5. **Update Registry** (if satisfied):
```yaml
# prompts/registry.yaml
rule_extraction:
  active_version: v1.3
  description: "Rule extraction from regulatory documents"
```

### Prompt Engineering Tips

1. **Be Specific**: Clearly define what to extract
2. **Provide Examples**: Include sample outputs in prompts
3. **Define Schema**: Specify exact JSON structure
4. **Set Constraints**: Define value ranges and types
5. **Test Iteratively**: Test on various documents
6. **Version Control**: Track all changes

## Adding Features

### Adding a New Extraction Mode

**1. Define Data Model**:

```python
# In rule_agent.py
class NewComponent(BaseModel):
    component_id: str
    title: str
    description: str
    metadata: ComponentMetadata
```

**2. Create Prompt**:

```bash
mkdir -p prompts/new_extraction
cat > prompts/new_extraction/v1.0.yaml << EOF
version: v1.0
task: new_extraction
prompt: |
  Extract new components from the document...
EOF
```

**3. Update Registry**:

```yaml
# prompts/registry.yaml
new_extraction:
  active_version: v1.0
  description: "New component extraction"
```

**4. Add Extraction Method**:

```python
# In RuleAgent class
def extract_new_components(
    self,
    document_path: str
) -> List[NewComponent]:
    """Extract new components from document"""
    # Implementation similar to extract_rules()
    pass
```

**5. Update CLI**:

```python
# In cli.py
parser.add_argument(
    "--mode",
    choices=["rules", "grc_components", "new_components"],
    default="rules"
)

# In main execution
if args.mode == "new_components":
    results = agent.extract_new_components(document_path)
```

**6. Add Tests**:

```python
# tests/test_rule_agent.py
def test_extract_new_components(agent):
    """Test new component extraction"""
    components = agent.extract_new_components("test_doc.docx")
    assert len(components) > 0
    assert isinstance(components[0], NewComponent)
```

### Adding a New LLM Provider

**1. Add Dependency**:

```bash
pip install langchain-newprovider
```

Update `requirements.txt`:
```
langchain-newprovider>=1.0.0
```

**2. Update CLI**:

```python
# In cli.py
from langchain_newprovider import ChatNewProvider

if args.provider == "newprovider":
    llm = ChatNewProvider(
        model=os.getenv("NEWPROVIDER_MODEL"),
        api_key=os.getenv("NEWPROVIDER_API_KEY"),
        temperature=0
    )
```

**3. Update Environment Config**:

```bash
# config/.env.example
NEWPROVIDER_API_KEY=your_api_key
NEWPROVIDER_MODEL=model-name
```

**4. Update Documentation**:
- Add to Configuration.md
- Update Usage-Guide.md examples

## Contributing

### Contribution Workflow

1. **Fork Repository**:
```bash
# On GitHub, click "Fork"
git clone https://github.com/YOUR_USERNAME/kratos-discover.git
cd kratos-discover
```

2. **Create Feature Branch**:
```bash
git checkout -b feature/your-feature-name
```

3. **Make Changes**:
- Write code
- Add tests
- Update documentation

4. **Test Changes**:
```bash
pytest
black --check .
flake8 .
```

5. **Commit Changes**:
```bash
git add .
git commit -m "Add feature: your feature description"
```

6. **Push to Fork**:
```bash
git push origin feature/your-feature-name
```

7. **Create Pull Request**:
- Go to GitHub
- Click "New Pull Request"
- Describe your changes

### Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new extraction mode
fix: resolve validation error
docs: update API reference
test: add tests for grounding node
refactor: simplify prompt loading
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Changes Made
- Added feature X
- Fixed bug Y
- Updated documentation Z

## Testing
- [ ] Added unit tests
- [ ] All tests pass
- [ ] Manual testing completed

## Documentation
- [ ] Updated README
- [ ] Updated wiki pages
- [ ] Added code comments
```

## Next Steps

- Review [Architecture](Architecture.md) for system design
- Check [Testing](#testing) for test guidelines
- Explore [API Reference](API-Reference.md) for implementation details

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for development help.
