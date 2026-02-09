# Architecture

Deep dive into the Kratos-Discover system architecture and design principles.

## Table of Contents

- [System Overview](#system-overview)
- [LangGraph Pipeline](#langgraph-pipeline)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Design Principles](#design-principles)
- [Extension Points](#extension-points)

## System Overview

Kratos-Discover is built on a graph-based workflow architecture using LangGraph, enabling flexible and maintainable document processing pipelines.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Input Layer                            │
│  (DOCX, PDF, HTML Documents)                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  RuleAgent (LangGraph)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Segmentation → 2. Extraction → 3. Validation     │  │
│  │         ↓              ↓                ↓             │  │
│  │  4. Deduplication → 5. Grounding → Output            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Output Layer                            │
│  (Structured JSON: Rules, Policies, Risks, Controls)        │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Core Framework**:
- **LangGraph**: State machine and workflow orchestration
- **LangChain**: LLM abstraction and chaining
- **Pydantic**: Data validation and serialization

**LLM Providers**:
- OpenAI (GPT-4, GPT-4o-mini)
- Anthropic (Claude Opus, Sonnet, Haiku)

**Document Processing**:
- `python-docx`: Microsoft Word documents
- `pypdf`: PDF parsing
- `beautifulsoup4`: HTML processing

## LangGraph Pipeline

### Pipeline Architecture

The core of Kratos-Discover is a 5-node LangGraph state machine:

```python
class RuleAgent:
    def build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("segment", self._segment_document)
        workflow.add_node("extract", self._extract_rules)
        workflow.add_node("validate", self._validate_rules)
        workflow.add_node("deduplicate", self._deduplicate_rules)
        workflow.add_node("ground", self._ground_rules)
        
        # Define edges
        workflow.set_entry_point("segment")
        workflow.add_edge("segment", "extract")
        workflow.add_edge("extract", "validate")
        workflow.add_edge("validate", "deduplicate")
        workflow.add_edge("deduplicate", "ground")
        workflow.add_edge("ground", END)
        
        return workflow.compile()
```

### Node Details

#### 1. Segmentation Node

**Purpose**: Divide the document into logical sections for processing

**Process**:
```
Input Document → Parse Format → Extract Sections → Identify Boundaries
                                                  ↓
                                          Return Segments
```

**Output**: List of document segments with metadata

**Example Segment**:
```python
{
    "content": "Section 2.3: Data Quality Requirements...",
    "section_id": "SEC_001",
    "start_index": 0,
    "end_index": 500
}
```

#### 2. Extraction Node

**Purpose**: Extract rules or GRC components using LLM

**Process**:
```
Segments → Build Prompt → Call LLM → Parse Response → Extract Items
                                                      ↓
                                              Return Raw Extracts
```

**LLM Interaction**:
- Uses structured output when supported (GPT-4o, Claude Opus)
- Falls back to JSON parsing for other models
- Applies versioned prompts from PromptRegistry

**Output**: List of raw extracted items (rules or components)

#### 3. Validation Node

**Purpose**: Validate extracted data against schemas

**Process**:
```
Raw Items → Pydantic Validation → Type Checking → Required Field Check
                                                  ↓
                                          Validated Items
```

**Validation Rules**:
- All required fields present
- Correct data types
- Value constraints (e.g., confidence 0.0-0.99)
- Enum validation (e.g., RuleCategory, RuleType)

**Output**: List of validated items, with invalid items logged and discarded

#### 4. Deduplication Node

**Purpose**: Remove duplicate entries

**Process**:
```
Validated Items → Compute Similarity → Cluster Duplicates → Select Best
                                                           ↓
                                                   Unique Items
```

**Deduplication Strategy**:
- Content-based similarity (text comparison)
- ID-based matching
- Confidence-based selection (keeps highest confidence)

**Output**: Deduplicated list of items

#### 5. Grounding Node

**Purpose**: Verify extracts against source text to prevent hallucinations

**Process**:
```
Items + Source Text → Verify Presence → Calculate Score → Filter Low Scores
                                                         ↓
                                                 Grounded Items
```

**Grounding Mechanism**:
- Checks if extracted content exists in source
- Calculates grounding confidence score
- Filters items below threshold
- Updates grounding metadata

**Output**: Final grounded and verified items

### State Management

The pipeline maintains state across nodes:

```python
class AgentState(TypedDict):
    """State passed between pipeline nodes"""
    document_path: str
    segments: List[DocumentSegment]
    raw_items: List[Dict]
    validated_items: List[BaseModel]
    deduplicated_items: List[BaseModel]
    grounded_items: List[BaseModel]
    metadata: Dict
    errors: List[str]
```

## Core Components

### 1. RuleAgent

**Location**: `rule_agent.py`

**Responsibilities**:
- Orchestrate the extraction pipeline
- Manage LangGraph workflow
- Handle debug artifacts
- Coordinate between components

**Key Methods**:
```python
class RuleAgent:
    def extract_rules(self, document_path: str) -> List[Rule]
    def extract_grc_components(self, document_path: str) -> Dict
    def _segment_document(self, state: AgentState) -> AgentState
    def _extract_rules(self, state: AgentState) -> AgentState
    def _validate_rules(self, state: AgentState) -> AgentState
    def _deduplicate_rules(self, state: AgentState) -> AgentState
    def _ground_rules(self, state: AgentState) -> AgentState
```

### 2. PromptRegistry

**Location**: `prompt_registry.py`

**Responsibilities**:
- Manage versioned prompts
- Load prompt specifications
- Track active versions
- Support prompt evolution

**Key Methods**:
```python
class PromptRegistry:
    def get_prompt(self, task: str, version: Optional[str] = None) -> str
    def get_active_version(self, task: str) -> str
    def list_versions(self, task: str) -> List[str]
```

**Prompt Structure**:
```yaml
# prompts/rule_extraction/v1.2.yaml
version: v1.2
task: rule_extraction
prompt: |
  Extract regulatory rules from the following document section...
  
  Return JSON with the following schema:
  {
    "rules": [
      {
        "rule_id": "unique identifier",
        "rule_description": "description",
        ...
      }
    ]
  }
schema:
  type: object
  properties:
    rules:
      type: array
      items:
        type: object
```

### 3. Data Models

**Location**: Defined in `rule_agent.py`

**Core Models**:

```python
# Rule Model
class Rule(BaseModel):
    rule_id: str
    category: RuleCategory  # Enum: rule, control, risk
    rule_type: RuleType
    rule_description: str
    grounded_in: str
    confidence: float  # 0.5 to 0.99
    attributes: Dict[str, Any]
    metadata: RuleMetadata

# GRC Components
class PolicyComponent(BaseModel):
    policy_id: str
    title: str
    description: str
    owner: str
    source_table: str
    metadata: ComponentMetadata

class RiskComponent(BaseModel):
    risk_id: str
    title: str
    description: str
    owner: str
    metadata: ComponentMetadata

class ControlComponent(BaseModel):
    control_id: str
    title: str
    description: str
    owner: str
    metadata: ComponentMetadata
```

### 4. CLI Interface

**Location**: `cli.py`

**Responsibilities**:
- Parse command-line arguments
- Initialize components
- Execute pipeline
- Save outputs
- Handle errors

**Argument Processing**:
```python
def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract rules from regulatory documents"
    )
    parser.add_argument("--provider", choices=["openai", "anthropic"])
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--mode", choices=["rules", "grc_components"])
    # ... more arguments
    return parser.parse_args()
```

## Data Flow

### End-to-End Flow

```
1. User Input
   ├─ CLI Arguments / API Call
   └─ Configuration (.env)
         ↓
2. Document Loading
   ├─ Read file (DOCX/PDF/HTML)
   └─ Parse content
         ↓
3. Segmentation
   ├─ Identify sections
   └─ Create segments
         ↓
4. LLM Extraction
   ├─ Build prompts
   ├─ Call LLM API
   └─ Parse responses
         ↓
5. Validation
   ├─ Schema validation
   └─ Data quality checks
         ↓
6. Deduplication
   ├─ Similarity analysis
   └─ Remove duplicates
         ↓
7. Grounding
   ├─ Verify against source
   └─ Filter ungrounded
         ↓
8. Output
   ├─ Format JSON
   └─ Save to file
```

### Debug Flow

When debug mode is enabled:

```
Each Node → Capture State → Dump to JSON → Continue
                           ↓
            outputs/debug_TIMESTAMP/
            ├─ raw_rules.json
            ├─ validated_rules.json
            └─ deduped_rules.json
```

## Design Principles

### 1. Modularity

Each pipeline node is independent and testable:
- Clear input/output contracts
- Single responsibility
- Easy to modify or replace

### 2. Extensibility

Easy to extend with new features:
- Add new extraction modes
- Support new document formats
- Integrate new LLM providers
- Add custom validation rules

### 3. Reliability

Multiple quality assurance layers:
- Schema validation
- Deduplication
- Grounding verification
- Error handling and logging

### 4. Reproducibility

Version control for prompts:
- Track prompt evolution
- Reproduce results with specific versions
- Compare prompt performance

### 5. Observability

Debug capabilities:
- Intermediate artifact dumps
- Detailed logging
- Pipeline state inspection

## Extension Points

### Adding a New Extraction Mode

```python
# 1. Define new data model
class CustomComponent(BaseModel):
    component_id: str
    # ... fields

# 2. Create extraction prompt
# prompts/custom_extraction/v1.0.yaml

# 3. Add extraction method
def extract_custom_components(self, document_path: str):
    # Implementation
    pass

# 4. Update CLI to support new mode
parser.add_argument("--mode", choices=["rules", "grc_components", "custom"])
```

### Adding a New LLM Provider

```python
# 1. Import provider SDK
from langchain_newprovider import ChatNewProvider

# 2. Initialize in CLI or API
if provider == "newprovider":
    llm = ChatNewProvider(
        model="model-name",
        api_key=os.getenv("NEWPROVIDER_API_KEY")
    )

# 3. Update documentation
```

### Adding a New Pipeline Node

```python
# 1. Define node function
def _custom_processing(self, state: AgentState) -> AgentState:
    # Process state
    return state

# 2. Add to workflow
workflow.add_node("custom", self._custom_processing)
workflow.add_edge("deduplicate", "custom")
workflow.add_edge("custom", "ground")
```

### Custom Validation Rules

```python
# 1. Extend validation node
def _validate_rules(self, state: AgentState) -> AgentState:
    # Standard validation
    validated = super()._validate_rules(state)
    
    # Custom validation
    for item in validated:
        if not self._custom_check(item):
            # Handle invalid item
            pass
    
    return state
```

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: Process multiple documents in parallel
2. **Caching**: Cache LLM responses for identical prompts
3. **Segmentation**: Optimize segment size for LLM context limits
4. **Streaming**: Use streaming responses for large documents

### Scalability

**Current Design**:
- Single-threaded pipeline
- In-memory processing
- Local file I/O

**Future Scalability**:
- Parallel processing of segments
- Database storage for results
- Queue-based document processing
- Distributed LLM calls

## Next Steps

- Review [Data Models](API-Reference.md#data-models)
- Learn about [Prompt Engineering](Development-Guide.md#prompt-development)
- Explore [Testing Strategies](Development-Guide.md#testing)

---

**Questions?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) for architecture discussions.
