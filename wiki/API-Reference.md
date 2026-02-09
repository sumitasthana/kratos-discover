# API Reference

Complete reference for the Kratos-Discover programmatic API.

## Table of Contents

- [RuleAgent Class](#ruleagent-class)
- [PromptRegistry Class](#promptregistry-class)
- [Data Models](#data-models)
- [Enumerations](#enumerations)
- [Exceptions](#exceptions)
- [Usage Examples](#usage-examples)

## RuleAgent Class

The main interface for document processing and rule extraction.

### Constructor

```python
class RuleAgent:
    def __init__(
        self,
        registry: PromptRegistry,
        llm: BaseChatModel,
        debug: bool = False,
        dump_debug_artifacts: bool = False
    )
```

**Parameters**:
- `registry` (PromptRegistry): Instance of PromptRegistry for prompt management
- `llm` (BaseChatModel): LangChain LLM instance (ChatOpenAI or ChatAnthropic)
- `debug` (bool): Enable debug logging (default: False)
- `dump_debug_artifacts` (bool): Save intermediate artifacts to disk (default: False)

**Example**:
```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

registry = PromptRegistry(base_dir=Path("."))
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = RuleAgent(registry=registry, llm=llm, debug=True)
```

### Methods

#### extract_rules()

Extract regulatory rules from a document.

```python
def extract_rules(
    self,
    document_path: str,
    prompt_version: Optional[str] = None
) -> List[Rule]
```

**Parameters**:
- `document_path` (str): Path to input document (DOCX, PDF, or HTML)
- `prompt_version` (Optional[str]): Override active prompt version

**Returns**:
- `List[Rule]`: List of extracted and validated Rule objects

**Raises**:
- `FileNotFoundError`: If document_path doesn't exist
- `ValueError`: If document format is unsupported
- `ValidationError`: If extracted data fails validation

**Example**:
```python
rules = agent.extract_rules(
    document_path="data/compliance_doc.docx",
    prompt_version="v1.2"
)

for rule in rules:
    print(f"{rule.rule_id}: {rule.rule_description}")
```

#### extract_grc_components()

Extract governance, risk, and compliance components.

```python
def extract_grc_components(
    self,
    document_path: str,
    prompt_version: Optional[str] = None
) -> Dict[str, List[BaseModel]]
```

**Parameters**:
- `document_path` (str): Path to input document
- `prompt_version` (Optional[str]): Override active prompt version

**Returns**:
- `Dict[str, List]`: Dictionary with keys 'policies', 'risks', 'controls'

**Example**:
```python
components = agent.extract_grc_components(
    document_path="data/grc_doc.docx"
)

print(f"Policies: {len(components['policies'])}")
print(f"Risks: {len(components['risks'])}")
print(f"Controls: {len(components['controls'])}")
```

### Internal Methods

These methods are part of the LangGraph pipeline and typically not called directly:

```python
def _segment_document(self, state: AgentState) -> AgentState
def _extract_rules(self, state: AgentState) -> AgentState
def _validate_rules(self, state: AgentState) -> AgentState
def _deduplicate_rules(self, state: AgentState) -> AgentState
def _ground_rules(self, state: AgentState) -> AgentState
```

## PromptRegistry Class

Manages versioned prompt specifications.

### Constructor

```python
class PromptRegistry:
    def __init__(self, base_dir: Path)
```

**Parameters**:
- `base_dir` (Path): Base directory containing prompts/ folder

**Example**:
```python
from pathlib import Path
from prompt_registry import PromptRegistry

registry = PromptRegistry(base_dir=Path("."))
```

### Methods

#### get_prompt()

Retrieve a prompt by task and version.

```python
def get_prompt(
    self,
    task: str,
    version: Optional[str] = None
) -> str
```

**Parameters**:
- `task` (str): Task name (e.g., "rule_extraction")
- `version` (Optional[str]): Specific version or None for active version

**Returns**:
- `str`: Prompt text

**Example**:
```python
# Get active version
prompt = registry.get_prompt("rule_extraction")

# Get specific version
prompt_v1 = registry.get_prompt("rule_extraction", version="v1.0")
```

#### get_active_version()

Get the active version for a task.

```python
def get_active_version(self, task: str) -> str
```

**Returns**:
- `str`: Active version identifier (e.g., "v1.2")

**Example**:
```python
version = registry.get_active_version("rule_extraction")
print(f"Active version: {version}")
```

#### list_versions()

List all available versions for a task.

```python
def list_versions(self, task: str) -> List[str]
```

**Returns**:
- `List[str]`: List of version identifiers

**Example**:
```python
versions = registry.list_versions("rule_extraction")
print(f"Available versions: {', '.join(versions)}")
```

## Data Models

All data models use Pydantic for validation and serialization.

### Rule

Represents a regulatory rule.

```python
class Rule(BaseModel):
    rule_id: str
    category: RuleCategory
    rule_type: RuleType
    rule_description: str
    grounded_in: str
    confidence: float
    attributes: Dict[str, Any]
    metadata: RuleMetadata
```

**Fields**:
- `rule_id`: Unique identifier (e.g., "RULE_001")
- `category`: Rule category (rule, control, or risk)
- `rule_type`: Specific type of rule
- `rule_description`: Human-readable description
- `grounded_in`: Source reference in document
- `confidence`: Extraction confidence (0.5 to 0.99)
- `attributes`: Additional rule-specific attributes
- `metadata`: Extraction metadata

**Example**:
```python
rule = Rule(
    rule_id="RULE_001",
    category=RuleCategory.RULE,
    rule_type=RuleType.DATA_QUALITY_THRESHOLD,
    rule_description="Data must be validated within 24 hours",
    grounded_in="Section 2.3, Paragraph 1",
    confidence=0.95,
    attributes={"threshold_hours": 24},
    metadata=RuleMetadata(
        source_block="Section 2.3",
        block_index=5,
        validation_status="valid"
    )
)
```

### RuleMetadata

Metadata for extracted rules.

```python
class RuleMetadata(BaseModel):
    source_block: str
    block_index: int
    validation_status: str
    extraction_timestamp: Optional[str]
```

**Fields**:
- `source_block`: Source text section
- `block_index`: Position in document
- `validation_status`: Validation result
- `extraction_timestamp`: When extracted (ISO format)

### PolicyComponent

Represents an organizational policy.

```python
class PolicyComponent(BaseModel):
    policy_id: str
    title: str
    description: str
    owner: str
    source_table: str
    metadata: ComponentMetadata
```

**Example**:
```python
policy = PolicyComponent(
    policy_id="POL_001",
    title="Data Retention Policy",
    description="Customer data must be retained for 7 years",
    owner="Compliance Department",
    source_table="Table 3.1",
    metadata=ComponentMetadata(
        source_block="Section 3",
        location="Page 15"
    )
)
```

### RiskComponent

Represents an identified risk.

```python
class RiskComponent(BaseModel):
    risk_id: str
    title: str
    description: str
    owner: str
    severity: Optional[str]
    metadata: ComponentMetadata
```

**Example**:
```python
risk = RiskComponent(
    risk_id="RISK_001",
    title="Data Loss Risk",
    description="Risk of customer data loss due to system failure",
    owner="IT Security",
    severity="high",
    metadata=ComponentMetadata(
        source_block="Section 4.2",
        location="Page 22"
    )
)
```

### ControlComponent

Represents a control measure.

```python
class ControlComponent(BaseModel):
    control_id: str
    title: str
    description: str
    owner: str
    control_type: Optional[str]
    metadata: ComponentMetadata
```

**Example**:
```python
control = ControlComponent(
    control_id="CTRL_001",
    title="Daily Backup Control",
    description="Automated daily backups of customer data",
    owner="IT Operations",
    control_type="preventive",
    metadata=ComponentMetadata(
        source_block="Section 5.1",
        location="Page 28"
    )
)
```

### ComponentMetadata

Metadata for GRC components.

```python
class ComponentMetadata(BaseModel):
    source_block: str
    location: Optional[str]
    extraction_timestamp: Optional[str]
```

## Enumerations

### RuleCategory

Categories of extracted rules.

```python
class RuleCategory(str, Enum):
    RULE = "rule"
    CONTROL = "control"
    RISK = "risk"
```

**Usage**:
```python
from rule_agent import RuleCategory

category = RuleCategory.RULE
if category == RuleCategory.RULE:
    print("This is a rule")
```

### RuleType

Specific types of rules.

```python
class RuleType(str, Enum):
    DATA_QUALITY_THRESHOLD = "data_quality_threshold"
    OWNERSHIP_CATEGORY = "ownership_category"
    TECHNICAL_REQUIREMENT = "technical_requirement"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"
    # ... more types
```

## Exceptions

### ValidationError

Raised when data validation fails.

```python
from pydantic import ValidationError

try:
    rule = Rule(**invalid_data)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### FileNotFoundError

Raised when document path doesn't exist.

```python
try:
    rules = agent.extract_rules("nonexistent.docx")
except FileNotFoundError as e:
    print(f"File not found: {e}")
```

## Usage Examples

### Example 1: Basic Rule Extraction

```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

# Setup
registry = PromptRegistry(base_dir=Path("."))
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = RuleAgent(registry=registry, llm=llm)

# Extract rules
rules = agent.extract_rules("data/document.docx")

# Process results
for rule in rules:
    print(f"ID: {rule.rule_id}")
    print(f"Description: {rule.rule_description}")
    print(f"Confidence: {rule.confidence}")
    print(f"Grounded in: {rule.grounded_in}")
    print("---")
```

### Example 2: GRC Component Extraction

```python
from langchain_anthropic import ChatAnthropic

# Setup with Anthropic
llm = ChatAnthropic(
    model="claude-opus-4-20250805",
    max_tokens=3000,
    temperature=0
)
agent = RuleAgent(registry=registry, llm=llm)

# Extract components
components = agent.extract_grc_components("data/grc_doc.docx")

# Process policies
for policy in components['policies']:
    print(f"Policy: {policy.title}")
    print(f"Owner: {policy.owner}")

# Process risks
for risk in components['risks']:
    print(f"Risk: {risk.title}")
    print(f"Severity: {risk.severity}")

# Process controls
for control in components['controls']:
    print(f"Control: {control.title}")
    print(f"Type: {control.control_type}")
```

### Example 3: Debug Mode

```python
# Enable debug mode
agent = RuleAgent(
    registry=registry,
    llm=llm,
    debug=True,
    dump_debug_artifacts=True
)

# Extract with debug output
rules = agent.extract_rules("data/document.docx")

# Debug artifacts saved to outputs/debug_TIMESTAMP/
```

### Example 4: Custom Processing

```python
import json

# Extract rules
rules = agent.extract_rules("data/document.docx")

# Filter high-confidence rules
high_confidence = [r for r in rules if r.confidence > 0.9]

# Group by category
from collections import defaultdict
by_category = defaultdict(list)
for rule in rules:
    by_category[rule.category].append(rule)

# Save custom format
output = {
    "total_rules": len(rules),
    "high_confidence": len(high_confidence),
    "by_category": {
        cat: len(rules) for cat, rules in by_category.items()
    },
    "rules": [rule.model_dump() for rule in rules]
}

with open("custom_output.json", "w") as f:
    json.dump(output, f, indent=2)
```

### Example 5: Error Handling

```python
from pydantic import ValidationError

try:
    rules = agent.extract_rules("data/document.docx")
    print(f"Successfully extracted {len(rules)} rules")
    
except FileNotFoundError:
    print("Error: Document not found")
    
except ValidationError as e:
    print(f"Validation error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Log full traceback
    import traceback
    traceback.print_exc()
```

### Example 6: Batch Processing

```python
from pathlib import Path
import json

# Process multiple documents
documents = Path("data").glob("*.docx")
all_rules = []

for doc in documents:
    print(f"Processing {doc.name}...")
    try:
        rules = agent.extract_rules(str(doc))
        all_rules.extend(rules)
        print(f"  Extracted {len(rules)} rules")
    except Exception as e:
        print(f"  Error: {e}")

# Save combined results
with open("all_rules.json", "w") as f:
    json.dump(
        [rule.model_dump() for rule in all_rules],
        f,
        indent=2
    )

print(f"Total rules extracted: {len(all_rules)}")
```

## Type Hints

Kratos-Discover uses Python type hints throughout:

```python
from typing import List, Dict, Optional, Any
from pathlib import Path
from pydantic import BaseModel

def process_documents(
    paths: List[Path],
    config: Dict[str, Any]
) -> Dict[str, List[BaseModel]]:
    """Process multiple documents"""
    pass
```

## Next Steps

- Explore [Usage Guide](Usage-Guide.md) for CLI examples
- Review [Architecture](Architecture.md) for system design
- Check [Development Guide](Development-Guide.md) for extending the API

---

**Need API help?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) with your question.
