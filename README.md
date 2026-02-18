# kratos-discover

Production-grade Rule Agent built with LangGraph for automated extraction and analysis of regulatory compliance documents.

## Overview

Kratos-discover is an intelligent document processing system designed to extract structured regulatory rules, policies, risks, and controls from compliance documents. Built on LangGraph and LangChain, it leverages large language models to transform unstructured regulatory text into actionable, machine-readable data.

The system currently supports processing FDIC 370 GRC Library documents and provides a robust pipeline for segmentation, extraction, validation, deduplication, and grounding.

## The Problem It Solves

This agent automates the extraction of structured regulatory compliance data from unstructured documents. Given a regulatory document (such as FDIC Part 370 or internal GRC policy libraries), the agent:

1. **Segments** the document into logical sections for processing
2. **Extracts** structured rules, policies, risks, and controls using LLM-powered analysis
3. **Validates** the extracted data against predefined schemas to ensure correctness
4. **Deduplicates** similar entries to eliminate redundancy
5. **Grounds** each extracted item by verifying it against the source text to prevent hallucinations
6. **Outputs** machine-readable JSON with complete metadata, ready for import into GRC platforms or further processing

The agent transforms unstructured regulatory text into structured, validated data that can be directly consumed by compliance management systems.

## Key Features

- **Automated Document Segmentation**: Intelligently splits regulatory documents into extractable sections
- **Multi-Mode Extraction**: Supports both rule extraction and GRC component (policies, risks, controls) extraction
- **LLM Provider Flexibility**: Compatible with OpenAI and Anthropic Claude models
- **Structured Output**: Uses schema-based structured output when supported by the LLM, with fallback to JSON parsing
- **Validation Pipeline**: Multi-stage validation, deduplication, and parsing to ensure data quality
- **Strict Grounding**: Enforces verification of extracted items against source text to prevent hallucinations
- **Versioned Prompts**: Supports prompt versioning for reproducibility and iterative improvement
- **Debug Mode**: Comprehensive debugging capabilities with intermediate artifact dumps
- **Flexible I/O**: Supports multiple document formats (DOCX, PDF, HTML) with configurable output options

## Architecture

Kratos-discover is built as a **modular, multi-stage document processing system** that combines deterministic parsing with LLM-powered extraction and validation. The architecture consists of two main processing pipelines:

### Pipeline 1: Rule/GRC Extraction (via RuleAgent)
A 5-node LangGraph workflow for extracting rules and GRC components:

1. **Segmentation Node**: Divides the source document into logical sections based on document structure
2. **Extraction Node**: Uses LLM to extract rules or GRC components with structured schemas
3. **Validation Node**: Parses and validates extracted data against Pydantic schemas
4. **Deduplication Node**: Removes duplicate entries based on content similarity
5. **Grounding Node**: Verifies each extracted item against source text and filters ungrounded items

### Pipeline 2: Advanced Requirements Processing (via Agent1)
A 5-stage pipeline for in-depth regulatory requirement extraction:

1. **Preprocessing (Node 1)**: Deterministic DOCX/XLSX/CSV parsing into structured chunks
2. **Schema Discovery (Node 2)**: LLM-powered inference of document structure (entities, fields, relationships)
3. **Confidence Gate (Node 3)**: Decision gate that validates schema confidence before proceeding
4. **Requirement Atomizer (Node 4)**: Extracts granular regulatory requirements with confidence scoring
5. **Quality Evaluation (Node 5)**: Multi-check quality assurance (grounding, testability, hallucination, deduplication)

### Core Components

- **RuleAgent**: Main orchestrator implementing the LangGraph pipeline for rule/GRC extraction
- **PromptRegistry**: Manages versioned prompt specifications stored as YAML files
- **CLI**: Multi-mode command-line interface with 4 subcommands (extract, preprocess, discover-schema, atomize)
- **Agent1**: Advanced processing pipeline with deterministic parsing and confidence-based quality gates
- **Shared Models**: Centralized enums and type definitions used across all modules
- **Scoring System**: Multi-factor confidence scoring with grounding verification
- **Data Models**: Pydantic models for Rules, Policies, Risks, Controls, and Regulatory Requirements

## Module Documentation

This section provides detailed explanations of each module in the codebase, describing what they do and how they work together.

### Command-Line Interface (`src/cli.py`)

**Purpose**: Multi-mode entry point for all document processing operations

The CLI module provides four distinct commands that expose different parts of the processing pipeline:

1. **`run` (default)**: Rule or GRC component extraction
   - Modes: `rules` or `grc_components`
   - Uses the complete 5-node RuleAgent pipeline
   - Supports debug mode with intermediate output dumps
   - Configurable LLM providers (OpenAI or Anthropic)
   - Example: `python -m src.cli --provider openai --mode rules`

2. **`preprocess`**: Deterministic document parsing (no LLM)
   - Parses DOCX/XLSX/CSV into structured chunks
   - Configurable chunk sizes (default: max 3000, min 50 chars)
   - Returns document statistics (word count, page count, table count)
   - Example: `python -m src.cli preprocess --input doc.docx --output chunks.json`

3. **`discover-schema`**: Document structure inference
   - Uses LLM (Claude recommended) to infer schema
   - Detects entities (tables, sections) and their fields
   - Returns schema map with confidence scores
   - Example: `python -m src.cli discover-schema --input doc.docx --provider anthropic`

4. **`atomize`**: Complete advanced pipeline (Nodes 1-5)
   - Runs full agent1 pipeline with quality evaluation
   - Includes preprocessing → schema discovery → confidence gate → atomization → quality checks
   - Outputs final requirements with quality metrics
   - Example: `python -m src.cli atomize --input doc.docx --provider anthropic`

**Key Functions**:
- `_build_llm()`: Factory method that creates OpenAI or Anthropic LLM instances
- `run()`: Orchestrates rule/GRC extraction workflow
- `run_preprocess()`: Executes deterministic chunking
- `run_schema_discovery()`: Runs schema inference
- `run_atomizer()`: Executes full pipeline with evaluation

### Rule Agent (`src/rule_agent.py`)

**Purpose**: LangGraph-based orchestrator for rule and GRC component extraction

The RuleAgent is the heart of the rule extraction system. It builds a state machine (LangGraph) with 5 nodes and manages the flow of data through the pipeline.

**Key Classes and Methods**:

- **`RuleAgent`**: Main orchestrator class
  - `extract_rules(document_path)`: Extracts regulatory rules from a document
  - `extract_grc_components(document_path)`: Extracts policies, risks, and controls
  - `_build_extraction_graph()`: Constructs the LangGraph state machine
  - `_build_grc_extraction_graph()`: Constructs GRC-specific extraction graph

**Data Models** (Pydantic):
- **`Rule`**: Represents an extracted regulatory rule
  - `rule_id`: Unique identifier (e.g., "DQ-001" for data quality rules)
  - `category`: RULE, CONTROL, or RISK (from shared.models.RuleCategory)
  - `rule_type`: One of 8 types (from shared.models.RuleType)
  - `rule_description`: Human-readable description
  - `grounded_in`: Source text that validates this rule
  - `confidence`: Float from 0.5 to 0.99
  - `attributes`: Dictionary of additional attributes
  - `metadata`: Source information (section, location)

- **`PolicyComponent`**: Organizational policy extracted from GRC documents
- **`RiskComponent`**: Risk statement extracted from GRC documents
- **`ControlComponent`**: Control measure extracted from GRC documents
- **`DocumentSection`**: Represents a logical section of the source document

**Pipeline Nodes** (internal methods):

1. **`_segment_requirements_node()`**: 
   - Divides document by heading hierarchy
   - Uses agent1 preprocessor for DOCX parsing
   - Returns list of DocumentSection objects

2. **`_extract_rules_node()`**: 
   - Sends sections to LLM with extraction prompts
   - Uses PromptRegistry to get the active prompt version
   - Returns raw LLM output (JSON)

3. **`_validate_parse_node()`**: 
   - Parses LLM JSON output
   - Validates against Pydantic Rule model
   - Filters out invalid entries
   - Returns list of valid Rule objects

4. **`_deduplication_node()`**: 
   - Compares rule titles and descriptions
   - Removes near-duplicate entries
   - Uses similarity threshold to detect duplicates

5. **`_grounding_scoring_node()`**: 
   - Validates that rule text appears in source
   - Computes confidence score (0.5-0.99)
   - Filters out rules that cannot be grounded
   - Uses agent1 scoring modules

**How It Works**:
When you call `extract_rules()`, the RuleAgent:
1. Builds a LangGraph state machine with 5 connected nodes
2. Initializes state with the document path and configuration
3. Executes the graph, passing state through each node
4. Each node transforms the state (adding/filtering/scoring rules)
5. Returns the final list of validated, deduplicated, grounded rules

### Prompt Registry (`src/prompt_registry.py`)

**Purpose**: Version control system for LLM prompts

The PromptRegistry manages prompt specifications as YAML files, allowing you to version prompts and switch between versions without changing code.

**Key Features**:
- Stores prompts as YAML with metadata (version, tags, description)
- Tracks active version for each prompt type
- Supports multiple versions of the same prompt
- Enables A/B testing and iterative improvement

**File Structure**:
```
prompts/
├── registry.yaml              # Maps prompt names to active versions
├── rule_extraction/
│   ├── v1.0.yaml             # Version 1.0 of rule extraction prompt
│   ├── v1.1.yaml             # Version 1.1 (improved)
│   └── v1.2.yaml             # Latest version
└── grc_extraction/
    ├── v1.0.yaml
    └── v1.1.yaml
```

**Key Methods**:
- `get_active_prompt(name)`: Returns the currently active version of a prompt
- `get_prompt(name, version)`: Fetches a specific version
- `set_active_version(name, version)`: Changes the active version
- `register_version(name, version, spec)`: Adds a new prompt version
- `list_versions(name)`: Shows all available versions

**Prompt Structure** (in YAML):
```yaml
version: "1.2"
tags: ["production", "improved"]
description: "Enhanced rule extraction with anti-patterns"
role: "You are an expert regulatory analyst..."
rule_types:
  - data_quality_threshold
  - ownership_category
  - ...
output_schema: |
  {
    "rules": [
      {"rule_id": "...", "rule_type": "..."}
    ]
  }
instructions: |
  1. Extract all regulatory rules from the text
  2. Classify each rule by type
  ...
anti_patterns: |
  - Do not extract examples or illustrations
  - Do not infer rules not explicitly stated
```

**Usage Example**:
```python
registry = PromptRegistry(base_dir=Path("."))
prompt = registry.get_active_prompt("rule_extraction")
# Returns fully rendered prompt string with all sections
```

### Shared Models (`src/shared/models.py`)

**Purpose**: Centralized definitions to avoid duplication across modules

This module contains canonical enums and type mappings used by both RuleAgent and Agent1. It prevents duplicate definitions and ensures consistency.

**Key Enums**:

1. **`RuleCategory`**: Classifies extracted items
   - `RULE`: Regulatory rule or requirement
   - `CONTROL`: Control measure or safeguard
   - `RISK`: Risk statement or concern

2. **`RuleType`**: Eight types of regulatory requirements
   
   **Core Types** (used by Agent1 atomizer):
   - `DATA_QUALITY_THRESHOLD`: Quantitative standards with measurable metrics (e.g., "accuracy must be ≥95%")
   - `OWNERSHIP_CATEGORY`: Account ownership classifications (e.g., "joint account", "trust account")
   - `BENEFICIAL_OWNERSHIP_THRESHOLD`: Numeric triggers for beneficial owners (e.g., "25% ownership")
   - `DOCUMENTATION_REQUIREMENT`: Required documents or records (e.g., "must maintain W-9 forms")
   - `UPDATE_REQUIREMENT`: Event-triggered record updates (e.g., "update within 30 days of address change")
   - `UPDATE_TIMELINE`: Time-bound deadlines or SLAs (e.g., "annual certification required")
   
   **Extended Types** (used by RuleAgent GRC mode):
   - `CONTROL_REQUIREMENT`: Control-specific requirements
   - `RISK_STATEMENT`: Risk-related statements

3. **`RULE_TYPE_CODES`**: Maps rule types to 2-3 character codes for ID generation
   - `DATA_QUALITY_THRESHOLD` → "DQ"
   - `OWNERSHIP_CATEGORY` → "OWN"
   - `BENEFICIAL_OWNERSHIP_THRESHOLD` → "BO"
   - `DOCUMENTATION_REQUIREMENT` → "DOC"
   - `UPDATE_REQUIREMENT` → "UPD"
   - `UPDATE_TIMELINE` → "TL"
   - `CONTROL_REQUIREMENT` → "CTL"
   - `RISK_STATEMENT` → "RSK"

These codes are used to generate readable IDs like "DQ-001", "OWN-002", etc.

### Pipeline Runner (`src/pipeline_runner.py`)

**Purpose**: Common orchestration utilities to reduce code duplication

This module provides helper functions used by multiple CLI commands to standardize logging, error handling, and output formatting.

**Key Features**:
- Generates unique run IDs with timestamps
- Structured logging with consistent formatting
- Step-by-step execution with error recovery
- JSON output serialization

**Key Methods**:
- `log_plan(steps)`: Logs the planned execution steps
- `log_step(step_name)`: Logs the start of a step
- `log_error(error)`: Logs errors with stack traces
- `run_with_steps(steps)`: Executes a list of (name, function) tuples with error handling
- `write_output(data, path)`: Writes results to JSON file

### Agent1 Pipeline - Advanced Processing

Agent1 is a sophisticated multi-stage pipeline for extracting granular regulatory requirements. Unlike the basic RuleAgent, it includes deterministic preprocessing, schema inference, confidence gating, and comprehensive quality evaluation.

#### Node 1: Preprocessor (`agent1/nodes/preprocessor.py`)

**Purpose**: Deterministic (no-LLM) document parsing into structured chunks

The preprocessor is the foundation of the Agent1 pipeline. It parses documents without using an LLM, ensuring consistent, reproducible results.

**Key Features**:
- **Deterministic**: Same input always produces same output
- **Fast**: No LLM API calls, pure Python parsing
- **Structured**: Preserves document hierarchy (headings, lists, tables)
- **Configurable**: Adjustable chunk sizes for downstream processing

**Supported Formats**:
- **DOCX**: Full support with table detection, heading hierarchy, list parsing
- **XLSX**: Placeholder (raises NotImplementedError)
- **CSV**: Placeholder (raises NotImplementedError)

**Key Function**:
```python
parse_and_chunk(
    file_path: Path,
    file_type: str,
    max_chunk_chars: int = 3000,
    min_chunk_chars: int = 50
) -> PreprocessorOutput
```

**Output Structure**:
- `chunks`: List of ContentChunk objects
  - `chunk_id`: Unique identifier (e.g., "chunk_001")
  - `chunk_type`: "prose", "heading", "list", or "table"
  - `text`: The actual content
  - `metadata`: Source information (page, heading, table data)
- `document_stats`: Statistics (word count, page count, table count, chunk count)
- `total_chunks`: Number of chunks created

**What It Does**:
1. Parses DOCX structure (paragraphs, tables, lists)
2. Detects heading hierarchy (Heading 1, Heading 2, etc.)
3. Splits large sections into manageable chunks
4. Preserves table structure as structured data (rows × columns)
5. Generates unique, stable chunk IDs
6. Returns document statistics

**Usage Example**:
```python
from src.agent1.nodes.preprocessor import parse_and_chunk

output = parse_and_chunk(
    file_path=Path("document.docx"),
    file_type="docx",
    max_chunk_chars=3000,
    min_chunk_chars=50
)

print(f"Created {output.total_chunks} chunks")
for chunk in output.chunks[:3]:
    print(f"{chunk.chunk_id}: {chunk.chunk_type}")
```

#### Node 2: Schema Discovery (`agent1/nodes/schema_discovery.py`)

**Purpose**: LLM-powered inference of document structure

After preprocessing, Schema Discovery uses an LLM (Claude recommended) to understand the semantic structure of the document.

**What It Discovers**:
1. **Entities**: Logical groupings in the document
   - Tables with their columns
   - Sections with their attributes
   - Repeated structures

2. **Fields**: Attributes of each entity
   - Field name and data type
   - Confidence score (0.0 to 1.0)
   - Example values
   - Relationships to other fields

3. **Structural Pattern**: Overall document organization
   - `vertical_table`: Rows represent items, columns are attributes
   - `horizontal_table`: Rows are attributes, columns are items
   - `prose_with_tables`: Mix of paragraphs and tables
   - `spreadsheet`: Pure tabular data
   - `mixed`: Complex multi-format document

4. **Relationships**: Connections between entities
   - Foreign key relationships
   - Parent-child hierarchies
   - Cross-references

5. **Anomalies**: Structural issues detected
   - Missing required fields
   - Inconsistent formatting
   - Ambiguous structures

**Key Function**:
```python
schema_discovery_agent(
    chunks: List[ContentChunk],
    llm: ChatAnthropic
) -> SchemaMap
```

**Output Structure** (`SchemaMap`):
```python
{
    "structural_pattern": "vertical_table",
    "entities": [
        {
            "name": "Account Requirements",
            "entity_type": "table",
            "fields": [
                {
                    "name": "requirement_id",
                    "confidence": 0.95,
                    "data_type": "string",
                    "examples": ["REQ-001", "REQ-002"]
                },
                {
                    "name": "description",
                    "confidence": 0.90,
                    "data_type": "text"
                }
            ]
        }
    ],
    "relationships": [],
    "anomalies": [],
    "confidence_avg": 0.87
}
```

**How It Works**:
1. Takes preprocessed chunks as input
2. Sends a sample of chunks to LLM with discovery prompt
3. LLM analyzes structure and returns JSON schema
4. Calculates average confidence across all fields
5. Returns SchemaMap for use by downstream nodes

#### Node 3: Confidence Gate (`agent1/nodes/confidence_gate.py`)

**Purpose**: Decision gate that validates schema quality before proceeding

The Confidence Gate implements a structured decision-making process. It prevents the pipeline from continuing with low-quality schemas.

**Decision Logic**:
```
IF avg_confidence >= 0.85 THEN auto_accept
ELSE IF avg_confidence >= 0.50 THEN human_review
ELSE IF has_required_fields THEN schema_compliance_ok
ELSE reject
```

**Thresholds** (configured in `agent1/config/gate_config.yaml`):
- **auto_accept_threshold**: 0.85 (high confidence, proceed automatically)
- **human_review_threshold**: 0.50 (medium confidence, flag for review)
- **schema_compliance_threshold**: 0.50 (minimum schema quality)

**Key Function**:
```python
check_confidence(schema: SchemaMap) -> GateDecision
```

**Output Structure** (`GateDecision`):
```python
{
    "decision": "auto_accept",  # or "human_review" or "reject"
    "confidence_score": 0.87,
    "failing_checks": [],
    "rationale": "Schema confidence 0.87 exceeds auto-accept threshold"
}
```

**What It Checks**:
1. Average confidence across all fields
2. Presence of required fields (e.g., requirement_id, description)
3. Minimum number of entities discovered
4. Schema compliance score

**Usage**:
- If decision is "auto_accept": proceed to Node 4
- If decision is "human_review": log warning, proceed with caution
- If decision is "reject": stop pipeline, report error

#### Node 4: Requirement Atomizer (`agent1/nodes/atomizer/`)

**Purpose**: Extracts granular regulatory requirements with confidence scoring

The Atomizer is the core extraction node. It takes schema-validated chunks and extracts individual requirements using LLM-powered analysis.

**Architecture**:
The atomizer is built from four sub-components:

1. **`BatchProcessor`** (`batch_processor.py`):
   - Batches chunks for efficient LLM processing
   - Manages rate limits and retries
   - Handles partial failures gracefully

2. **`PromptBuilder`** (`prompt_builder.py`):
   - Loads prompts from `agent1/prompts/`
   - Injects schema information into prompts
   - Renders final prompt with examples

3. **`ResponseParser`** (`response_parser.py`):
   - Parses LLM JSON responses
   - Handles malformed JSON gracefully
   - Validates against requirement schema

4. **`SchemaRepairer`** (`schema_repair.py`):
   - Attempts to fix partial or invalid outputs
   - Fills in missing required fields
   - Applies heuristics for common errors

**Key Class**:
```python
class RequirementAtomizerNode:
    def __init__(self, llm, prompt_registry):
        self.llm = llm
        self.prompt_builder = PromptBuilder(prompt_registry)
        self.batch_processor = BatchProcessor()
        self.parser = ResponseParser()
        self.repairer = SchemaRepairer()
    
    def atomize(
        self, 
        chunks: List[ContentChunk], 
        schema: SchemaMap
    ) -> List[RegulatoryRequirement]
```

**Output Structure** (`RegulatoryRequirement`):
```python
{
    "requirement_id": "DQ-001",
    "rule_type": "data_quality_threshold",
    "category": "rule",
    "description": "Customer name accuracy must be ≥95%",
    "grounded_in": "...source text from document...",
    "confidence": 0.85,
    "attributes": {
        "threshold": "95%",
        "metric": "accuracy",
        "applies_to": "customer name"
    },
    "metadata": {
        "source_chunk_id": "chunk_042",
        "extraction_timestamp": "2026-02-18T03:10:36Z"
    }
}
```

**Confidence Scoring**:
Each requirement gets a confidence score (0.0 to 1.0) based on six factors:

1. **Grounding Match** (40% weight): How well the requirement text matches source text
2. **Completeness** (20% weight): Are all required fields present?
3. **Quantification** (15% weight): Does it include measurable criteria?
4. **Schema Compliance** (10% weight): Does it match expected schema?
5. **Coherence** (10% weight): Is the text logical and clear?
6. **Domain Signals** (5% weight): Contains domain-specific keywords?

Confidence scores are computed by `agent1/scoring/confidence_scorer.py`.

**What It Does**:
1. Takes chunks and schema as input
2. Batches chunks for LLM processing
3. For each batch:
   - Builds extraction prompt with schema context
   - Sends to LLM
   - Parses JSON response
   - Validates requirements
   - Attempts repair if needed
   - Scores confidence
4. Returns list of requirements with metadata

#### Node 5: Quality Evaluation (`agent1/eval/eval_node.py`)

**Purpose**: Comprehensive quality assurance with six check types

After extraction, the Quality Evaluation node runs six independent checks to assess output quality and identify issues.

**The Six Checks**:

1. **Grounding Check** (`checks/grounding.py`):
   - **What**: Validates that requirement text appears in source chunks
   - **How**: Fuzzy string matching with configurable threshold
   - **Pass**: If grounded_in text is found in source with >70% similarity
   - **Fail**: If text appears fabricated or cannot be traced to source
   - **Severity**: HIGH (hallucination risk)

2. **Testability Check** (`checks/testability.py`):
   - **What**: Detects vague or untestable language
   - **How**: Scans for weak verbs ("should", "may", "could", "consider")
   - **Pass**: Uses strong, definitive verbs ("must", "shall", "will")
   - **Fail**: Contains vague verbs that make testing ambiguous
   - **Severity**: MEDIUM (implementation risk)
   - **Example Failures**:
     - "Banks *should* maintain records" ❌
     - "Banks *must* maintain records" ✅

3. **Hallucination Check** (`checks/hallucination.py`):
   - **What**: Detects claims not supported by source document
   - **How**: Cross-references requirement attributes with source text
   - **Pass**: All attributes can be traced to source
   - **Fail**: Attributes appear invented or inferred without evidence
   - **Severity**: CRITICAL (accuracy risk)

4. **Deduplication Check** (`checks/deduplication.py`):
   - **What**: Finds near-duplicate requirements
   - **How**: Compares descriptions using cosine similarity
   - **Pass**: Requirement is unique (similarity < 0.85)
   - **Fail**: Requirement is near-duplicate of another (similarity ≥ 0.85)
   - **Severity**: LOW (redundancy, not incorrectness)

5. **Schema Compliance Check** (`checks/schema_compliance.py`):
   - **What**: Validates attributes match discovered schema
   - **How**: Checks that attribute keys match schema fields
   - **Pass**: All attributes present in schema
   - **Fail**: Attributes missing from schema or unexpected attributes present
   - **Severity**: MEDIUM (consistency risk)

6. **Coverage Analysis** (`checks/coverage.py`):
   - **What**: Measures extraction completeness
   - **How**: Compares extracted chunks to total preprocessed chunks
   - **Pass**: High coverage (>80% of chunks resulted in requirements)
   - **Fail**: Low coverage (<50% of chunks resulted in requirements)
   - **Severity**: INFO (not a failure, but a metric)
   - **Metrics**:
     - `chunks_processed`: Total chunks analyzed
     - `chunks_with_extractions`: Chunks that yielded requirements
     - `coverage_percentage`: Percentage of successful extractions
     - `avg_requirements_per_chunk`: Density metric

**Key Function**:
```python
eval_quality(
    requirements: List[RegulatoryRequirement],
    chunks: List[ContentChunk],
    schema: SchemaMap
) -> EvalReport
```

**Output Structure** (`EvalReport`):
```python
{
    "total_requirements": 127,
    "passed": 98,
    "failed": 29,
    "failures_by_check": {
        "grounding": 5,
        "testability": 12,
        "hallucination": 2,
        "deduplication": 8,
        "schema_compliance": 2,
        "coverage": 0
    },
    "failures_by_severity": {
        "critical": 2,
        "high": 5,
        "medium": 14,
        "low": 8
    },
    "quality_score": 0.77,  # passed / total
    "detailed_failures": [
        {
            "requirement_id": "DQ-042",
            "check": "testability",
            "severity": "medium",
            "reason": "Contains vague verb 'should' - not testable"
        }
    ],
    "coverage_metrics": {
        "chunks_processed": 156,
        "chunks_with_extractions": 134,
        "coverage_percentage": 85.9
    }
}
```

**What It Does**:
1. Runs all six checks in parallel
2. Aggregates results by check type and severity
3. Calculates overall quality score
4. Flags specific requirements with issues
5. Returns comprehensive evaluation report

**Severity Levels**:
- **CRITICAL**: Must fix (hallucination)
- **HIGH**: Should fix (grounding failure)
- **MEDIUM**: Consider fixing (testability, schema compliance)
- **LOW**: Optional (deduplication)
- **INFO**: Informational only (coverage)

### Agent1 Supporting Modules

#### Scoring System (`agent1/scoring/`)

**Purpose**: Multi-factor confidence scoring for extracted requirements

The scoring system computes confidence scores (0.0-1.0) for each requirement based on six factors:

1. **`confidence_scorer.py`**: Main scoring orchestrator
   - `score_requirement(req, chunk, schema)`: Computes overall confidence
   - Weights: grounding (40%), completeness (20%), quantification (15%), schema (10%), coherence (10%), domain (5%)
   - Returns score between 0.0 and 1.0

2. **`grounding.py`**: Text matching logic
   - `find_grounding_span(req_text, chunk_text)`: Finds matching text spans
   - Uses fuzzy matching with configurable threshold (default 70%)
   - Returns match percentage and span location

3. **`verb_replacer.py`**: Vague verb detection
   - `detect_weak_verbs(text)`: Scans for weak/vague verbs
   - Weak verbs: "should", "may", "could", "might", "consider", "optionally"
   - Strong verbs: "must", "shall", "will", "required", "prohibited"

4. **`features.py`**: Feature extraction for scoring
   - `compute_completeness(req)`: Checks for required fields
   - `compute_quantification(req)`: Detects numeric thresholds
   - `compute_schema_compliance(req, schema)`: Validates against schema
   - `compute_coherence(req)`: Assesses text quality

#### Data Models (`agent1/models/`)

**Purpose**: Pydantic models for type safety and validation

1. **`chunks.py`**: Preprocessing models
   - `ContentChunk`: Individual chunk of document
   - `PreprocessorOutput`: Complete preprocessing results

2. **`schema_map.py`**: Schema discovery models
   - `SchemaMap`: Overall document schema
   - `DiscoveredEntity`: Logical entity (table, section)
   - `DiscoveredField`: Attribute of an entity

3. **`requirements.py`**: Extraction models
   - `RegulatoryRequirement`: Single extracted requirement
   - `ExtractionMetadata`: Statistics and metadata

4. **`state.py`**: Pipeline state
   - `Phase1State`: TypedDict for LangGraph state management

5. **`control_metadata/`**: Control enrichment
   - Infers control-specific metadata (control type, owner, frequency)
   - Uses templates and patterns to enrich control requirements

#### Parsers (`agent1/parsers/`)

**Purpose**: Format-specific document parsers

1. **`docx_parser.py`**: DOCX parsing
   - Parses paragraphs, tables, lists
   - Detects heading hierarchy
   - Preserves table structure
   - Returns ContentChunk list

2. **`xlsx_parser.py`**: Excel parsing (placeholder)
   - Currently raises NotImplementedError
   - Planned for future release

3. **`csv_parser.py`**: CSV parsing (placeholder)
   - Currently raises NotImplementedError
   - Planned for future release

#### Utilities (`agent1/utils/`)

**Purpose**: Helper functions used across agent1

1. **`chunking.py`**: Chunk management
   - `generate_chunk_id(index)`: Creates stable chunk IDs
   - `split_by_size(text, max_size)`: Splits text into chunks
   - Ensures deterministic, collision-free IDs

#### Cache (`agent1/cache/`)

**Purpose**: Schema caching for performance

1. **`schema_cache.py`**: Cache implementation
   - Caches SchemaMap results by document hash
   - Avoids redundant LLM calls for same documents
   - Configurable cache directory and TTL

### Module Interaction Flow

Here's how the modules work together in a typical extraction workflow:

**Scenario 1: Basic Rule Extraction**
```
User runs: python -m src.cli --provider openai --mode rules

Flow:
1. cli.py::run() called
2. Loads PromptRegistry
3. Creates OpenAI LLM via _build_llm()
4. Instantiates RuleAgent(registry, llm)
5. Calls agent.extract_rules(document_path)
6. RuleAgent builds 5-node LangGraph:
   - Node 1: _segment_requirements_node()
     → Uses agent1.nodes.preprocessor.parse_and_chunk()
   - Node 2: _extract_rules_node()
     → Uses PromptRegistry.get_active_prompt("rule_extraction")
   - Node 3: _validate_parse_node()
     → Validates against shared.models.RuleType/RuleCategory
   - Node 4: _deduplication_node()
   - Node 5: _grounding_scoring_node()
     → Uses agent1.scoring.confidence_scorer
7. Returns validated rules
8. cli.py writes results to JSON
```

**Scenario 2: Advanced Atomization**
```
User runs: python -m src.cli atomize --provider anthropic

Flow:
1. cli.py::run_atomizer() called
2. Creates Anthropic LLM via _build_llm()
3. Executes 5-stage pipeline:
   - Stage 1: agent1.nodes.preprocessor.parse_and_chunk()
     → Returns PreprocessorOutput with chunks
   - Stage 2: agent1.nodes.schema_discovery.schema_discovery_agent()
     → Returns SchemaMap
   - Stage 3: agent1.nodes.confidence_gate.check_confidence()
     → Returns GateDecision (auto_accept/human_review/reject)
   - Stage 4: agent1.nodes.atomizer.RequirementAtomizerNode.atomize()
     → Returns List[RegulatoryRequirement] with confidence scores
   - Stage 5: agent1.eval.eval_node.eval_quality()
     → Returns EvalReport with quality metrics
4. cli.py writes:
   - requirements.json (extracted requirements)
   - evaluation.json (quality report)
   - schema.json (discovered schema)
```

**Scenario 3: Preprocessing Only**
```
User runs: python -m src.cli preprocess --input doc.docx

Flow:
1. cli.py::run_preprocess() called
2. Calls agent1.nodes.preprocessor.parse_and_chunk()
   → Uses agent1.parsers.docx_parser.DOCXParser
   → Uses agent1.utils.chunking for ID generation
3. Returns PreprocessorOutput
4. cli.py writes chunks.json
```

### Integration Points

**Where Modules Connect**:

1. **shared.models → rule_agent + agent1**:
   - RuleType enum used for validation in both
   - RuleCategory enum used for classification
   - RULE_TYPE_CODES used for ID generation

2. **agent1.nodes.preprocessor → rule_agent**:
   - RuleAgent._segment_requirements_node() calls parse_and_chunk()
   - Enables RuleAgent to use deterministic DOCX parsing

3. **agent1.scoring → rule_agent**:
   - RuleAgent._grounding_scoring_node() uses confidence_scorer
   - Provides grounding verification for extracted rules

4. **prompt_registry → rule_agent + agent1**:
   - RuleAgent loads prompts for rule extraction
   - Agent1 atomizer loads prompts for requirement extraction
   - Both use versioned YAML specs

5. **pipeline_runner → cli**:
   - All CLI commands use PipelineRunner utilities
   - Standardizes logging and error handling

## Installation

### Prerequisites

- Python 3.10 or higher
- Virtual environment (recommended)

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

Edit `.env` to add your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
CLAUDE_MODEL=claude-opus-4-20250805
OPENAI_MODEL=gpt-4o-mini
FDIC_370_PATH=data/FDIC_370_GRC_Library_National_Bank.docx
```

## Usage

### Data Preparation

Place your FDIC 370 source document in the `data/` directory:
```
data/FDIC_370_GRC_Library_National_Bank.docx
```

Note: The `data/` directory is gitignored to prevent accidental commits of sensitive documents.

### Command-Line Interface

#### Basic Rule Extraction

Extract rules using OpenAI:
```bash
python -m src.cli --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

Extract rules using Anthropic Claude:
```bash
python -m src.cli --provider anthropic --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

Alternatively, if you installed the package:
```bash
kratos-discover --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

#### GRC Component Extraction

Extract policies, risks, and controls:
```bash
python -m src.cli --mode grc_components --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output grc_results.json
```

#### Advanced Options

Enable debug mode with intermediate outputs:
```bash
python -m src.cli --provider openai --debug --dump-debug --output results.json
```

Override the active prompt version:
```bash
python -m src.cli --provider openai --prompt-version v1.2 --output results.json
```

Specify a custom output directory:
```bash
python -m src.cli --provider openai --output-dir ./my_outputs
```

Adjust logging level:
```bash
python -m src.cli --provider openai --log-level DEBUG
```

### Programmatic API

```python
import os
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from src.rule_agent import RuleAgent
from src.prompt_registry import PromptRegistry

# Initialize prompt registry
registry = PromptRegistry(base_dir=Path("."))

# Configure LLM (choose one)
# Option A: Anthropic Claude
llm = ChatAnthropic(
    model=os.getenv("CLAUDE_MODEL", "claude-opus-4-20250805"),
    max_tokens=3000,
    temperature=0
)

# Option B: OpenAI
# llm = ChatOpenAI(
#     model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
#     temperature=0
# )

# Create agent instance
agent = RuleAgent(registry=registry, llm=llm)

# Extract rules
rules = agent.extract_rules(document_path=os.getenv("FDIC_370_PATH"))
print(f"Extracted {len(rules)} rules")

# Extract GRC components
components = agent.extract_grc_components(document_path=os.getenv("FDIC_370_PATH"))
print(f"Policies: {len(components['policies'])}")
print(f"Risks: {len(components['risks'])}")
print(f"Controls: {len(components['controls'])}")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | Required for Anthropic |
| `OPENAI_API_KEY` | API key for OpenAI | Required for OpenAI |
| `CLAUDE_MODEL` | Claude model identifier | `claude-opus-4-20250805` |
| `OPENAI_MODEL` | OpenAI model identifier | `gpt-4o-mini` |
| `FDIC_370_PATH` | Path to FDIC 370 document | `data/FDIC_370_GRC_Library_National_Bank.docx` |
| `LLM_PROVIDER` | Default LLM provider | `openai` |
| `RULE_AGENT_MODE` | Default extraction mode | `rules` |
| `RULE_AGENT_OUTPUT_DIR` | Default output directory | `outputs` |
| `RULE_AGENT_LOG_LEVEL` | Logging verbosity | `INFO` |

### Prompt Versioning

Prompt specifications are stored in `prompts/` with version control:

- `prompts/registry.yaml`: Defines active prompt versions
- `prompts/rule_extraction/v1.0.yaml`: Rule extraction prompt v1.0
- `prompts/rule_extraction/v1.1.yaml`: Rule extraction prompt v1.1
- `prompts/rule_extraction/v1.2.yaml`: Rule extraction prompt v1.2

To switch prompt versions, either:
1. Edit `prompts/registry.yaml` to change the active version
2. Use the `--prompt-version` CLI flag to override at runtime

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

## Quick Start Examples

### Example 1: Extract Rules from a Document

```bash
# Using OpenAI
python -m src.cli --provider openai --input data/document.docx --output rules.json

# Using Anthropic Claude (recommended for better accuracy)
python -m src.cli --provider anthropic --input data/document.docx --output rules.json
```

### Example 2: Preprocess a Document (No LLM)

```bash
# Parse DOCX into structured chunks
python -m src.cli preprocess --input data/document.docx --output chunks.json

# Configure chunk sizes
python -m src.cli preprocess \
  --input data/document.docx \
  --max-chunk-size 5000 \
  --min-chunk-size 100 \
  --output chunks.json
```

### Example 3: Discover Document Schema

```bash
# Infer document structure using LLM
python -m src.cli discover-schema \
  --input data/document.docx \
  --provider anthropic \
  --output schema.json
```

### Example 4: Run Full Advanced Pipeline

```bash
# Execute complete 5-stage pipeline with quality evaluation
python -m src.cli atomize \
  --input data/document.docx \
  --provider anthropic \
  --output-dir ./results/
```

This creates three output files:
- `results/requirements.json`: Extracted requirements
- `results/evaluation.json`: Quality assessment report
- `results/schema.json`: Discovered document schema

### Example 5: Extract GRC Components

```bash
# Extract policies, risks, and controls
python -m src.cli \
  --mode grc_components \
  --provider openai \
  --input data/grc_document.docx \
  --output grc_components.json
```

### Example 6: Debug Mode with Intermediate Outputs

```bash
# Enable debug mode to see intermediate results
python -m src.cli \
  --provider openai \
  --debug \
  --dump-debug \
  --output results.json

# This creates a timestamped debug directory with:
# - raw_rules.json (initial LLM output)
# - validated_rules.json (post-validation)
# - deduped_rules.json (after deduplication)
```

## Agent1 Deterministic Preprocessor

## Agent1 Deterministic Preprocessor

**Note**: This section provides a quick overview. For comprehensive module documentation, see the [Module Documentation](#module-documentation) section above.

Agent1 is the foundation of the advanced processing pipeline. It provides deterministic (no-LLM) preprocessing as the first step in document analysis.

### Why Agent1?

Traditional document processing approaches parse documents inconsistently. Agent1 solves this by providing:

- **Deterministic Parsing**: Same input file always produces the same chunk IDs and structure
- **No LLM Dependency**: Fast, reliable parsing without API calls or costs
- **Structure Preservation**: Maintains document hierarchy (headings, lists, tables)
- **Clean Output**: Light whitespace normalization without aggressive transformation

### What It Does

Agent1 parses a `.docx` file and:

1. **Detects Structure**: Identifies headings, prose blocks, lists, and tables
2. **Creates Chunks**: Splits content into manageable pieces (configurable size)
3. **Preserves Hierarchy**: Maintains heading levels and document organization
4. **Extracts Tables**: Preserves table structure as `table_data` (rows × columns)
5. **Generates IDs**: Creates stable, unique chunk identifiers
6. **Returns Statistics**: Provides document metrics (word count, page count, etc.)

### Supported File Types

- **DOCX**: ✅ Full support
- **XLSX**: ⏳ Placeholder (raises `NotImplementedError`)
- **CSV**: ⏳ Placeholder (raises `NotImplementedError`)

### Text Normalization

Agent1 applies minimal whitespace normalization:
- Trims trailing spaces per line
- Collapses repeated blank lines (max 2 consecutive)
- **Does NOT**: Remove punctuation, change capitalization, or alter words

### Package Layout

```
src/agent1/
  __init__.py
  exceptions.py
  models/
    __init__.py
    input.py
    chunks.py
  nodes/
    __init__.py
    preprocessor.py
  parsers/
    __init__.py
    docx_parser.py
    xlsx_parser.py  # placeholder
    csv_parser.py   # placeholder
  utils/
    __init__.py
    chunking.py
```

### Agent1 Package Layout

The Agent1 module is organized into logical subpackages:

```
src/agent1/
├── __init__.py               # Package exports
├── exceptions.py             # Custom exceptions
│
├── models/                   # Data models (Pydantic)
│   ├── chunks.py            # ContentChunk, PreprocessorOutput
│   ├── schema_map.py        # SchemaMap, DiscoveredEntity, DiscoveredField
│   ├── requirements.py      # RegulatoryRequirement, ExtractionMetadata
│   ├── state.py             # Phase1State (LangGraph state)
│   └── control_metadata/    # Control enrichment logic
│
├── nodes/                    # Processing nodes (pipeline stages)
│   ├── preprocessor.py      # Node 1: Deterministic parsing
│   ├── schema_discovery.py  # Node 2: Structure inference
│   ├── confidence_gate.py   # Node 3: Quality gate
│   └── atomizer/            # Node 4: Requirement extraction
│       ├── node.py          # Main atomizer logic
│       ├── batch_processor.py
│       ├── prompt_builder.py
│       ├── response_parser.py
│       └── schema_repair.py
│
├── parsers/                  # Format-specific parsers
│   ├── docx_parser.py       # DOCX → chunks (full support)
│   ├── xlsx_parser.py       # Excel (placeholder)
│   └── csv_parser.py        # CSV (placeholder)
│
├── scoring/                  # Confidence scoring system
│   ├── confidence_scorer.py # Multi-factor scoring
│   ├── grounding.py         # Text span matching
│   ├── verb_replacer.py     # Vague verb detection
│   └── features.py          # Feature extraction
│
├── eval/                     # Node 5: Quality evaluation
│   ├── eval_node.py         # Main evaluation orchestrator
│   ├── checks/              # Individual quality checks
│   │   ├── grounding.py
│   │   ├── testability.py
│   │   ├── hallucination.py
│   │   ├── deduplication.py
│   │   ├── schema_compliance.py
│   │   └── coverage.py
│   └── models.py            # Evaluation result models
│
├── utils/                    # Utility functions
│   └── chunking.py          # Chunk ID generation, text splitting
│
├── cache/                    # Caching for performance
│   └── schema_cache.py      # SchemaMap caching
│
├── config/                   # Configuration files
│   └── gate_config.yaml     # Confidence gate thresholds
│
└── prompts/                  # Agent1-specific prompts
    ├── registry.yaml
    ├── requirement_atomizer/
    └── schema_discovery/
```

### Programmatic Usage

#### Example 1: Basic Preprocessing

```python
from pathlib import Path
from src.agent1.nodes.preprocessor import parse_and_chunk

# Parse a DOCX file into chunks
output = parse_and_chunk(
    file_path=Path("data/FDIC_370_GRC_Library_National_Bank.docx"),
    file_type="docx",
    max_chunk_chars=3000,  # Maximum characters per chunk
    min_chunk_chars=50,    # Minimum characters (smaller chunks are dropped)
)

# Access results
print(f"Total chunks: {output.total_chunks}")
print(f"Document stats: {output.document_stats}")

# Iterate through chunks
for chunk in output.chunks:
    print(f"{chunk.chunk_id} ({chunk.chunk_type}): {chunk.text[:100]}...")
    
# Example output:
# chunk_001 (heading): FDIC Part 370 - Recordkeeping for...
# chunk_002 (prose): This rule establishes standards for...
# chunk_003 (table): [Table data preserved in chunk.metadata['table_data']]
```

#### Example 2: Full Pipeline with Schema Discovery

```python
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from src.agent1.nodes.preprocessor import parse_and_chunk
from src.agent1.nodes.schema_discovery import schema_discovery_agent
from src.agent1.nodes.confidence_gate import check_confidence

# Step 1: Preprocess document
prep_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx"
)

# Step 2: Discover schema
llm = ChatAnthropic(model="claude-opus-4-20250805", temperature=0)
schema = schema_discovery_agent(
    chunks=prep_output.chunks,
    llm=llm
)

print(f"Discovered {len(schema.entities)} entities")
print(f"Average confidence: {schema.confidence_avg:.2f}")
print(f"Structural pattern: {schema.structural_pattern}")

# Step 3: Check schema confidence
gate_decision = check_confidence(schema)

if gate_decision.decision == "auto_accept":
    print("✅ Schema quality is high, proceeding with extraction")
elif gate_decision.decision == "human_review":
    print("⚠️  Schema quality is medium, recommend human review")
else:
    print("❌ Schema quality is low, cannot proceed")
    
print(f"Confidence score: {gate_decision.confidence_score:.2f}")
print(f"Rationale: {gate_decision.rationale}")
```

#### Example 3: Extract Requirements with Atomizer

```python
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from src.agent1.nodes.preprocessor import parse_and_chunk
from src.agent1.nodes.schema_discovery import schema_discovery_agent
from src.agent1.nodes.atomizer import RequirementAtomizerNode
from src.prompt_registry import PromptRegistry

# Initialize components
llm = ChatAnthropic(model="claude-opus-4-20250805", temperature=0)
prompt_registry = PromptRegistry(base_dir=Path("."))

# Run preprocessing and schema discovery
prep_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx"
)
schema = schema_discovery_agent(chunks=prep_output.chunks, llm=llm)

# Extract requirements
atomizer = RequirementAtomizerNode(llm=llm, prompt_registry=prompt_registry)
requirements = atomizer.atomize(
    chunks=prep_output.chunks,
    schema=schema
)

print(f"Extracted {len(requirements)} requirements")

# Show first requirement
req = requirements[0]
print(f"ID: {req.requirement_id}")
print(f"Type: {req.rule_type}")
print(f"Description: {req.description}")
print(f"Confidence: {req.confidence:.2f}")
print(f"Grounded in: {req.grounded_in[:200]}...")
```

#### Example 4: Quality Evaluation

```python
from src.agent1.eval.eval_node import eval_quality

# After extraction, evaluate quality
eval_report = eval_quality(
    requirements=requirements,
    chunks=prep_output.chunks,
    schema=schema
)

print(f"Quality Score: {eval_report.quality_score:.2%}")
print(f"Total Requirements: {eval_report.total_requirements}")
print(f"Passed: {eval_report.passed}")
print(f"Failed: {eval_report.failed}")

# Show failures by check type
print("\nFailures by Check:")
for check, count in eval_report.failures_by_check.items():
    print(f"  {check}: {count}")

# Show failures by severity
print("\nFailures by Severity:")
for severity, count in eval_report.failures_by_severity.items():
    print(f"  {severity}: {count}")

# Show coverage metrics
print(f"\nCoverage: {eval_report.coverage_metrics['coverage_percentage']:.1f}%")
```

### Agent1 Logging

Agent1 uses **structlog** for structured, parseable logging. All log events are emitted as JSON objects for easy integration with log aggregation systems.

**Common Log Events**:

**Preprocessing Events**:
- `parse_started`: Document parsing begins
  ```json
  {"event": "parse_started", "file_path": "document.docx", "file_type": "docx"}
  ```
- `parse_completed`: Parsing finished successfully
  ```json
  {"event": "parse_completed", "total_chunks": 156, "total_chars": 425000, "duration_ms": 1250}
  ```
- `empty_chunk_skipped`: Chunk dropped (below min_chunk_chars)
  ```json
  {"event": "empty_chunk_skipped", "chunk_id": "chunk_042", "char_count": 12}
  ```
- `chunk_parse_failed`: Non-fatal per-block parsing failure
  ```json
  {"event": "chunk_parse_failed", "block_index": 87, "error": "Malformed table"}
  ```

**Schema Discovery Events**:
- `schema_discovery_started`: Schema inference begins
- `schema_discovery_completed`: Schema inference finished
- `low_confidence_field`: Field with confidence < 0.5 detected

**Atomizer Events**:
- `batch_processing_started`: LLM batch processing begins
- `batch_processing_completed`: Batch finished
- `requirement_extracted`: Single requirement extracted
- `schema_repair_attempted`: Attempted to fix malformed output

**Evaluation Events**:
- `quality_check_started`: Quality evaluation begins
- `quality_check_completed`: Evaluation finished
- `check_failed`: Specific requirement failed a check
  ```json
  {
    "event": "check_failed",
    "requirement_id": "DQ-042",
    "check": "testability",
    "severity": "medium",
    "reason": "Contains vague verb 'should'"
  }
  ```

**Log Level Configuration**:
```python
import structlog

# Set log level
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
)
```

**Viewing Logs**:
```bash
# Pipe to jq for pretty-printing
python -m src.cli atomize --input doc.docx 2>&1 | jq '.'
```

### Agent1 Tests

Agent1 has comprehensive test coverage across all modules. Tests are located in `tests/agent1/`.

**Test Strategy**:
- **No Binary Fixtures**: Tests generate `.docx` files at runtime (no committed binary files)
- **Deterministic**: Tests verify that same input produces same output
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test full pipeline flows

**Running Agent1 Tests**:

```bash
# Run all agent1 tests
pytest tests/agent1/

# Run specific test file
pytest tests/test_agent1_preprocessor.py

# Run with verbose output
pytest tests/agent1/ -v

# Run with coverage report
pytest tests/agent1/ --cov=src/agent1 --cov-report=html
```

**Test Files**:
- `test_agent1_preprocessor.py`: Preprocessing and chunking tests
- `test_schema_discovery.py`: Schema discovery tests
- `test_atomizer.py`: Requirement extraction tests
- `test_confidence_gate.py`: Gate decision tests
- `test_eval_node.py`: Quality evaluation tests

**Example Test Output**:
```
tests/agent1/test_atomizer.py::test_atomizer_extracts_requirements PASSED
tests/agent1/test_atomizer.py::test_atomizer_confidence_scoring PASSED
tests/agent1/test_schema_discovery.py::test_schema_discovery_vertical_table PASSED
```

**Writing Tests**:
When adding new features to Agent1, ensure:
1. Unit tests for new functions/classes
2. Integration tests for end-to-end flows
3. Tests use runtime-generated fixtures (no binary commits)
4. Tests validate both success and error cases

### Project Structure

```
kratos-discover/
├── README.md                   # Project documentation
├── pyproject.toml              # Python package configuration
├── setup.py                    # Package setup script
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container definition
├── docker-compose.yml          # Docker Compose configuration
├── .gitignore                  # Git ignore rules
├── .dockerignore               # Docker ignore rules
├── config/
│   ├── .env.example            # Environment variable template
│   └── rule_attributes_schema.yaml
├── prompts/
│   ├── registry.yaml           # Active prompt versions
│   └── rule_extraction/        # Versioned prompt specs
│       ├── v1.0.yaml
│       ├── v1.1.yaml
│       └── v1.2.yaml
├── src/
│   ├── cli.py                  # Command-line interface
│   ├── rule_agent.py           # Main RuleAgent implementation
│   ├── prompt_registry.py      # Prompt version management
│   └── agent1/                 # Deterministic preprocessor module
│       ├── __init__.py
│       ├── exceptions.py
│       ├── models/             # Data models
│       ├── nodes/              # Processing nodes
│       ├── parsers/            # Document parsers
│       └── utils/              # Utility functions
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_rule_agent.py
│   ├── test_prompt_registry.py
│   └── test_agent1_preprocessor.py
├── wiki/                       # Documentation wiki
│   ├── Home.md
│   ├── Installation-Guide.md
│   ├── Usage-Guide.md
│   ├── Configuration.md
│   ├── Architecture.md
│   ├── API-Reference.md
│   ├── Development-Guide.md
│   ├── Deployment-Guide.md
│   └── Troubleshooting.md
├── data/                       # Input documents (gitignored)
└── outputs/                    # Extraction results (gitignored)
```

### Debug Mode

Debug mode provides visibility into the extraction pipeline:

```bash
python -m src.cli --debug --dump-debug --provider openai
```

This creates a timestamped debug directory containing:
- `raw_rules.json`: Initial LLM extraction output
- `validated_rules.json`: Post-validation results
- `deduped_rules.json`: After deduplication

## Quality Assurance

### Strict Grounding

The grounding node implements a verification step that:
- Compares extracted content against source section text
- Calculates grounding scores
- Filters out items that cannot be verified in the source
- Prevents LLM hallucinations and ensures accuracy

### Validation Pipeline

Multi-stage validation ensures data quality:
1. Schema validation using Pydantic models
2. Required field verification
3. Data type and constraint checking
4. Deduplication based on content similarity
5. Source text verification

## Troubleshooting

### Common Issues

**Import Errors**: Ensure virtual environment is activated and dependencies are installed
```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**API Key Errors**: Verify environment variables are set correctly
```bash
echo $OPENAI_API_KEY  # or echo %OPENAI_API_KEY% on Windows
```

**File Not Found**: Check that input document path is correct and file exists
```bash
ls -la data/FDIC_370_GRC_Library_National_Bank.docx
```

**Model Timeout**: For large documents, consider using debug mode to process incrementally

### Logging

Increase log verbosity for troubleshooting:
```bash
python -m src.cli --log-level DEBUG
```

## Docker Deployment

Kratos-Discover includes Docker support for easy deployment.

### Quick Start with Docker

```bash
# Build the image
docker build -t kratos-discover .

# Run with environment file
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/outputs:/app/outputs \
  kratos-discover \
  --provider openai --input data/document.docx
```

### Using Docker Compose

```bash
# Start services
docker-compose up

# Run extraction
docker-compose run kratos-discover \
  --provider openai --input data/document.docx
```

For detailed deployment instructions, see the [Deployment Guide](wiki/Deployment-Guide.md).

## Documentation

Comprehensive documentation is available in the [wiki](wiki/) directory:

- **[Installation Guide](wiki/Installation-Guide.md)** - Setup and installation
- **[Usage Guide](wiki/Usage-Guide.md)** - CLI and API usage
- **[Configuration](wiki/Configuration.md)** - Environment variables and settings
- **[Architecture](wiki/Architecture.md)** - System design and components
- **[API Reference](wiki/API-Reference.md)** - Programmatic API documentation
- **[Development Guide](wiki/Development-Guide.md)** - Contributing and development
- **[Deployment Guide](wiki/Deployment-Guide.md)** - Docker and production deployment
- **[Troubleshooting](wiki/Troubleshooting.md)** - Common issues and solutions

## Contributing

Contributions are welcome. Please ensure:
- Code follows existing style conventions
- Tests pass with `pytest`
- New features include appropriate test coverage
- Documentation is updated for new functionality

See the [Development Guide](wiki/Development-Guide.md) for detailed contribution guidelines.

## License

This project is provided as-is for regulatory compliance document processing.

## Acknowledgments

Built with:
- LangChain: Framework for LLM applications
- LangGraph: Graph-based workflow orchestration
- Pydantic: Data validation and schema management
- OpenAI and Anthropic: LLM providers
