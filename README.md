# kratos-discover

Production-grade regulatory requirement extraction system for automated processing of compliance documents. Built with Anthropic Claude as the LLM backbone, it runs a sequential multi-stage pipeline for deterministic parsing, schema-aware extraction, confidence gating, and quality evaluation.

## Table of Contents

- [Overview](#overview)
- [The Problem It Solves](#the-problem-it-solves)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
  - [System Overview](#system-overview)
  - [Pipeline: Advanced Requirements Processing](#pipeline-advanced-requirements-processing-via-agent1)
  - [Data Flow Diagrams](#data-flow-diagrams)
- [Module Documentation](#module-documentation)
- [Complete API Reference](#complete-api-reference)
- [Configuration Guide](#configuration-guide)
- [Advanced Usage](#advanced-usage)
- [Performance Optimization](#performance-optimization)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

Kratos-Discover is an LLM-powered document processing system that extracts structured regulatory requirements, policies, risks, and controls from compliance documents such as FDIC Part 370 IT Controls. The system uses a 6-stage pipeline architecture (Nodes 1–3.5, 4, 5 plus an Insights Generator post-processor) with confidence scoring, schema validation, and quality evaluation.

### Use Cases

- **Regulatory Compliance**: Extract structured requirements from FDIC, OCC, FFIEC, and other regulatory documents
- **GRC Automation**: Transform policy documents into machine-readable controls and risks
- **Risk Assessment**: Identify and categorize risks from unstructured compliance documents
- **Control Cataloging**: Build comprehensive control libraries from multiple sources
- **Policy Management**: Structure organizational policies for governance systems
- **Audit Preparation**: Extract testable requirements for compliance audits

## The Problem It Solves

This system automates the extraction of structured regulatory compliance data from DOCX documents. Given a regulatory document, the pipeline:

1. **Parses** the document into deterministic chunks (tables, prose, lists) — DOCX only
2. **Discovers** document schema structure using LLM analysis
3. **Gates** processing based on confidence thresholds
4. **Extracts** GRC components (policies, risks, controls) from tables
5. **Atomizes** complex text into atomic regulatory requirements
6. **Evaluates** extraction quality with hallucination detection and grounding verification
7. **Generates** narrative insights (quality tiers, risk flags, recommendations) without additional LLM calls

The system transforms unstructured regulatory text into structured, validated data with confidence scores and quality metrics.

## Key Features

- **Deterministic Preprocessing**: Parse DOCX into structured chunks with consistent IDs
- **Schema Discovery**: Automatically infer document structure using stratified sampling
- **Confidence Scoring**: Multi-dimensional confidence with grounding verification
- **GRC Extraction**: Extract policies, risks, and controls from Word tables
- **Requirement Atomization**: Break complex text into atomic, testable requirements
- **Quality Evaluation**: Comprehensive checks including hallucination detection, testability, and schema compliance
- **Grounding Classification**: EXACT/PARAPHRASE/INFERENCE classification for each extraction
- **Auto-Repair**: Automatic schema violation repair attempts
- **Insights Generator**: Post-processing narrative insights (quality tier, risk flags, recommendations) with no extra LLM calls
### Core Capabilities
- **Automated Document Segmentation**: Intelligently splits regulatory documents into extractable sections
- **Agent1 Pipeline Extraction**: Uses the Agent1 pipeline for comprehensive regulatory requirement extraction
- **Anthropic Claude Integration**: Powered exclusively by Anthropic Claude (default: `claude-sonnet-4-20250514`)
- **Structured Output**: Uses schema-based structured output when supported by the LLM, with fallback to JSON parsing
- **Validation Pipeline**: Multi-stage validation, deduplication, and parsing to ensure data quality
- **Strict Grounding**: Enforces verification of extracted items against source text to prevent hallucinations
- **Versioned Prompts**: Supports prompt versioning for reproducibility and iterative improvement
- **Debug Mode**: Comprehensive debugging capabilities with intermediate artifact dumps
- **DOCX Support**: Optimized for `.docx` regulatory documents

### Advanced Features
- **Schema Discovery**: Automatically infers document structure using LLM analysis
- **Confidence Gating**: Quality checkpoints with configurable thresholds
- **Multi-Factor Scoring**: Confidence scores based on 6 independent factors
- **Batch Processing**: Efficient processing of large documents with rate limiting
- **Error Recovery**: Graceful handling of LLM failures with automatic retries
- **Deterministic Parsing**: No-LLM preprocessing for consistent, reproducible results
- **Quality Evaluation**: Six-check quality assurance framework (grounding, testability, hallucination, deduplication, schema compliance, coverage)
- **Caching Support**: Schema caching for improved performance on similar documents
- **Extensible Architecture**: Easy to add new extraction modes, LLM providers, or validation rules

### Quality Assurance
- **Grounding Verification**: Every extraction is verified against source text
- **Hallucination Detection**: Identifies LLM-fabricated content
- **Deduplication**: Removes redundant extractions using similarity matching
- **Testability Analysis**: Flags vague requirements that can't be tested
- **Schema Compliance**: Validates extractions match discovered schema
- **Coverage Metrics**: Measures extraction completeness across document

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/sumitasthana/kratos-discover.git
cd kratos-discover

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install in editable mode for development
pip install -e .
```

### Environment Setup

Create a `.env` file in the project root:

```bash
# Required: Anthropic API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: SSL and configuration overrides
ANTHROPIC_VERIFY_SSL=false
KRATOS_LOG_LEVEL=INFO
KRATOS_OUTPUT_DIR=outputs
```

### Basic Usage

#### 1. Preprocess a Document (No LLM)

```bash
# Parse DOCX into deterministic structured chunks
python -m src.cli preprocess \
  --input data/regulatory_document.docx \
  --output outputs/chunks.json
```

#### 2. Discover Document Schema

```bash
# Infer document structure using LLM
python -m src.cli discover-schema \
  --input data/regulatory_document.docx \
  --output outputs/schema.json
```

#### 3. Advanced Pipeline with Quality Evaluation

```bash
# Run the complete Agent1 pipeline (preprocess → schema → gate → grc-extract → atomize → eval → insights)
python -m src.cli atomize \
  --input data/compliance_doc.docx \
  --output outputs/requirements.json
```

### Quick Example

```python
# Programmatic API usage
from pathlib import Path
from nodes.preprocessor import parse_and_chunk
from nodes.schema_discovery import schema_discovery_agent

# Step 1: Preprocess document
result = parse_and_chunk(
    file_path=Path("document.docx"),
    file_type="docx",
    max_chunk_chars=3000
)
print(f"Created {result.total_chunks} chunks")

# Step 2: Discover schema (pass full state dict)
state = {"file_path": str(result.file_path), "chunks": result.chunks, "prompt_versions": {}, "errors": []}
schema_result = schema_discovery_agent(state)
schema_map = schema_result["schema_map"]
print(f"Discovered {len(schema_map.entities)} entities")
print(f"Schema avg confidence: {schema_map.avg_confidence:.2f}")

# Step 3: Run full pipeline via CLI
# python -m src.cli atomize --input document.docx
```

## Architecture

The system implements a 6-stage pipeline:

| Stage | Node | Name | Description |
|-------|------|------|-------------|
| 1 | 1 | Preprocessor | Parse DOCX into deterministic chunks |
| 2 | 2 | Schema Discovery | Infer document structure using Claude |
| 3 | 3 | Confidence Gate | Validate schema confidence meets thresholds |
| 4 | 3.5 | GRC Extractor | Extract Policy/Risk/Control components from tables |
| 5 | 4 | Atomizer | Extract atomic regulatory requirements |
| 6 | 5 | Eval | Quality assessment and failure classification |
| Post | — | Insights Generator | Narrative insights without additional LLM calls |

### Core Components

- **CLI**: Command-line interface (`cli.py`)
- **Nodes**: Pipeline processing nodes (`nodes/`)
- **Models**: Pydantic data models (`models/`)
- **Scoring**: Confidence scoring system (`scoring/`)
- **Eval**: Quality evaluation checks (`eval/`)
Kratos-discover is built as a **modular, multi-stage document processing system** that combines deterministic parsing with LLM-powered extraction and validation. The architecture is centered around the Agent1 pipeline:

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       KRATOS-DISCOVER                            │
│                 Document Processing System                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────┬──────────────┐
                              │             │              │
                    ┌─────────▼───────┐ ┌───▼────────┐ ┌──▼─────┐
                    │   CLI Entry      │ │ Python API │ │ Docker │
                    └─────────┬────────┘ └───┬────────┘ └──┬─────┘
                              │              │             │
                              └──────────────┼─────────────┘
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    │                                                  │
          ┌─────────▼────────────┐
          │   PIPELINE           │
          │   Agent1             │
          │   (6 Stages)         │
          │                      │
          │  Advanced            │
          │  Requirements        │
          └─────────┬────────────┘
                    │
                    │
          ┌─────────▼───────────┐
          │  Shared Components   │
          │  - Models            │
          │  - LLM Clients       │
          │  - Scoring           │
          │  - Chunking          │
          │  - Parsers           │
          └──────────────────────┘
```

### Pipeline: Advanced Requirements Processing (via Agent1)
A 6-stage pipeline for in-depth regulatory requirement extraction:

1. **Preprocessing (Node 1)**: Deterministic DOCX parsing into structured chunks
2. **Schema Discovery (Node 2)**: LLM-powered inference of document structure (entities, fields, relationships)
3. **Confidence Gate (Node 3)**: Decision gate that validates schema confidence before proceeding
4. **GRC Extraction (Node 3.5)**: Extracts Policy, Risk, and Control components from document tables
5. **Requirement Atomizer (Node 4)**: Extracts granular regulatory requirements with confidence scoring
6. **Quality Evaluation (Node 5)**: Multi-check quality assurance (grounding, testability, hallucination, deduplication)
7. **Insights Generator (Post-processing)**: Narrative insights — quality tier, risk flags, and recommendations — without additional LLM calls

#### Pipeline Flow Diagram (Agent1)

```
Input: Document (DOCX)
    │
    ▼
┌──────────────────────────────────────────────┐
│  NODE 1: PREPROCESSOR (Deterministic)        │
│  - Parse DOCX structure                      │
│  - Extract tables, lists, prose              │
│  - Chunk text (50-3000 chars)                │
│  - Generate document statistics              │
└────────────────────┬─────────────────────────┘
                     │ List[ContentChunk] + Stats
                     ▼
┌──────────────────────────────────────────────┐
│  NODE 2: SCHEMA DISCOVERY (LLM)              │
│  - Analyze chunk structure                   │
│  - Identify entities & fields                │
│  - Detect relationships                      │
│  - Calculate field confidence                │
└────────────────────┬─────────────────────────┘
                     │ SchemaMap + confidence
                     ▼
┌──────────────────────────────────────────────┐
│  NODE 3: CONFIDENCE GATE (Decision)          │
│  - Evaluate schema confidence                │
│  - Check required fields present             │
│  ┌──────────────────┐                        │
│  │ Decision Logic:  │                        │
│  │ ≥0.85 → Accept   │                        │
│  │ ≥0.50 → Review   │                        │
│  │ <0.50 → Reject   │                        │
│  └──────────────────┘                        │
└────────────────────┬─────────────────────────┘
                     │ GateDecision
                     ├─[REJECT]──→ Stop & Report Error
                     ├─[REVIEW]──→ Continue with Warning
                     └─[ACCEPT]──→ Continue
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  NODE 3.5: GRC EXTRACTOR (LLM)              │
│  - Extract Policy components from tables     │
│  - Extract Risk components from tables       │
│  - Extract Control components from tables    │
│  - Build component index (chunk → component) │
└────────────────────┬─────────────────────────┘
                     │ GRCComponentsResponse
                     ▼
┌──────────────────────────────────────────────┐
│  NODE 4: REQUIREMENT ATOMIZER (LLM)          │
│  - Batch chunks for processing               │
│  - Build schema-aware prompts                │
│  - Extract atomic requirements               │
│  - Parse & validate responses                │
│  - Apply schema repair if needed             │
│  - Score confidence (6 factors)              │
└────────────────────┬─────────────────────────┘
                     │ List[RegulatoryRequirement]
                     ▼
┌──────────────────────────────────────────────┐
│  NODE 5: QUALITY EVALUATION (6 Checks)       │
│  ┌────────────────────────────────────────┐  │
│  │ 1. Grounding Check     (HIGH)          │  │
│  │ 2. Testability Check   (MEDIUM)        │  │
│  │ 3. Hallucination Check (CRITICAL)      │  │
│  │ 4. Deduplication Check (LOW)           │  │
│  │ 5. Schema Compliance   (MEDIUM)        │  │
│  │ 6. Coverage Analysis   (INFO)          │  │
│  └────────────────────────────────────────┘  │
│  - Aggregate results by severity             │
│  - Calculate quality score                   │
│  - Flag specific failures                    │
└────────────────────┬─────────────────────────┘
                     │ EvalReport
                     ▼
┌──────────────────────────────────────────────┐
│  POST-PROCESSING: INSIGHTS GENERATOR         │
│  - Quality tier (Excellent/Good/Fair/Needs   │
│    Review) based on schema completeness,     │
│    grounding quality, data source coverage   │
│  - Risk flags (low coverage, schema issues,  │
│    fragment warnings, low confidence)        │
│  - Hallucination risk summary                │
│  - Confidence distribution breakdown         │
│  - Actionable recommendations               │
│  (No additional LLM calls)                  │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
Output: requirements.json (with embedded insights + eval_report)
```

### Data Flow Diagrams

#### Complete Data Flow (Agent1 Pipeline - Detailed)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │  Document (DOCX)            │
                    │  - Text content             │
                    │  - Tables                   │
                    │  - Formatting               │
                    └──────────────┬──────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                        PREPROCESSING LAYER                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  DOCXParser                 │
                    │  - Extract paragraphs       │
                    │  - Extract tables (2D)      │
                    │  - Extract lists            │
                    │  - Identify headings        │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  ChunkingEngine             │
                    │  - Split on boundaries      │
                    │  - Min: 50, Max: 3000 chars │
                    │  - Preserve structure       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────────────────────┐
                    │  ContentChunks (List)                       │
                    │  [                                          │
                    │    {                                        │
                    │      "chunk_id": "chunk_001",               │
                    │      "chunk_type": "prose",                 │
                    │      "text": "Banks must maintain...",     │
                    │      "metadata": {                          │
                    │        "heading": "Section 2.1",            │
                    │        "page": 5                            │
                    │      }                                      │
                    │    },                                       │
                    │    ...                                      │
                    │  ]                                          │
                    └──────────────┬──────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                       SCHEMA DISCOVERY LAYER                             │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  LLM (Claude Recommended)   │
                    │  + Schema Discovery Prompt  │
                    │  - Analyze structure        │
                    │  - Infer entities/fields    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼─────────────────────────────┐
                    │  SchemaMap                                 │
                    │  {                                         │
                    │    "structural_pattern": "vertical_table", │
                    │    "entities": [                           │
                    │      {                                     │
                    │        "name": "Requirements",             │
                    │        "fields": [                         │
                    │          {                                 │
                    │            "name": "requirement_id",       │
                    │            "confidence": 0.95,             │
                    │            "data_type": "string"           │
                    │          },                                │
                    │          ...                               │
                    │        ]                                   │
                    │      }                                     │
                    │    ],                                      │
                    │    "confidence_avg": 0.87                  │
                    │  }                                         │
                    └──────────────┬─────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                       CONFIDENCE GATE LAYER                              │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Gate Logic Evaluator       │
                    │  - Check confidence ≥ 0.85  │
                    │  - Verify required fields   │
                    │  - Validate entity count    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  GateDecision               │
                    │  {                          │
                    │    "decision": "auto_accept"│
                    │    "confidence": 0.87,      │
                    │    "rationale": "..."       │
                    │  }                          │
                    └──────────────┬──────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                       ATOMIZATION LAYER                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Batch Processor            │
                    │  - Group chunks             │
                    │  - Manage rate limits       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Prompt Builder             │
                    │  - Inject schema context    │
                    │  - Add examples             │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  LLM (Claude)               │
                    │  + Atomization Prompt       │
                    │  - Extract requirements     │
                    │  - Apply rule types         │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Response Parser            │
                    │  - Parse JSON               │
                    │  - Validate schema          │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Schema Repairer            │
                    │  - Fix partial outputs      │
                    │  - Fill missing fields      │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Confidence Scorer          │
                    │  - 6 scoring factors        │
                    │  - Weighted calculation     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼─────────────────────────┐
                    │  RegulatoryRequirements (List)         │
                    │  [                                     │
                    │    {                                   │
                    │      "requirement_id": "DQ-001",       │
                    │      "rule_type": "data_quality_...",  │
                    │      "description": "Accuracy ≥95%",   │
                    │      "grounded_in": "source text...",  │
                    │      "confidence": 0.85,               │
                    │      "attributes": {...},              │
                    │      "metadata": {...}                 │
                    │    },                                  │
                    │    ...                                 │
                    │  ]                                     │
                    └──────────────┬─────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                    QUALITY EVALUATION LAYER                              │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴──────────────────────────┐
         │                                                     │
    ┌────▼────┐  ┌───────────┐  ┌──────────────┐  ┌──────────▼─────┐
    │Grounding│  │Testability│  │Hallucination │  │ Deduplication  │
    │  Check  │  │   Check   │  │    Check     │  │     Check      │
    └────┬────┘  └─────┬─────┘  └──────┬───────┘  └───────┬────────┘
         │             │                │                  │
         └─────────────┼────────────────┼──────────────────┘
                       │                │
              ┌────────▼────────┐  ┌────▼────────────┐
              │ Schema          │  │   Coverage      │
              │ Compliance      │  │   Analysis      │
              └────────┬────────┘  └────┬────────────┘
                       │                │
                       └────────┬───────┘
                                │
                    ┌───────────▼────────────────────────────┐
                    │  EvalReport                            │
                    │  {                                     │
                    │    "total_requirements": 127,          │
                    │    "passed": 98,                       │
                    │    "failed": 29,                       │
                    │    "quality_score": 0.77,              │
                    │    "failures_by_severity": {           │
                    │      "critical": 2,                    │
                    │      "high": 5,                        │
                    │      "medium": 14,                     │
                    │      "low": 8                          │
                    │    },                                  │
                    │    "detailed_failures": [...]          │
                    │  }                                     │
                    └────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                          OUTPUT LAYER                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  JSON Output Files          │
                    │  - requirements.json        │
                    │  - eval_report.json         │
                    │  - metadata.json            │
                    └─────────────────────────────┘
```

### Core Components

- **Agent1**: Advanced processing pipeline with deterministic parsing and confidence-based quality gates
- **CLI**: Command-line interface with 3 subcommands (preprocess, discover-schema, atomize)
- **Shared Models**: Centralized enums and type definitions used across all modules
- **Scoring System**: Multi-factor confidence scoring with grounding verification
- **Data Models**: Pydantic models for Regulatory Requirements

## Module Documentation

This section provides detailed explanations of each module in the codebase, describing what they do and how they work together.

### Command-Line Interface (`src/cli.py`)

**Purpose**: Entry point for all document processing operations

The CLI module provides three commands that expose different parts of the processing pipeline:

1. **`preprocess`**: Deterministic document parsing (no LLM)
   - Parses DOCX into structured chunks
   - Configurable chunk sizes (default: max 3000, min 50 chars)
   - Returns document statistics (word count, page count, table count)
   - Example: `python -m src.cli preprocess --input doc.docx --output chunks.json`

2. **`discover-schema`**: Document structure inference
   - Uses LLM (Claude recommended) to infer schema
   - Detects entities (tables, sections) and their fields
   - Returns schema map with confidence scores
   - Example: `python -m src.cli discover-schema --input doc.docx`

3. **`atomize`**: Complete Agent1 pipeline (Nodes 1-5)
   - Runs full pipeline with quality evaluation
   - Includes preprocessing → schema discovery → confidence gate → atomization → quality checks
   - Outputs final requirements with quality metrics
   - Example: `python -m src.cli atomize --input doc.docx`

**Key Functions**:
- `run_preprocess()`: Executes deterministic chunking
- `run_schema_discovery()`: Runs schema inference
- `run_atomizer()`: Executes full pipeline with evaluation

### Shared Models (`src/models/shared.py`)

**Purpose**: Centralized definitions to avoid duplication across modules

This module contains canonical enums and type mappings used by the Agent1 pipeline. It prevents duplicate definitions and ensures consistency.

**Key Enums**:

1. **`RuleCategory`**: Classifies extracted items
   - `RULE`: Regulatory rule or requirement
   - `CONTROL`: Control measure or safeguard
   - `RISK`: Risk statement or concern

2. **`RuleType`**: Ten types of regulatory requirements
   
   - `DATA_QUALITY_THRESHOLD`: Quantitative standards with measurable metrics (e.g., "accuracy must be ≥95%")
   - `ENUMERATION_CONSTRAINT`: Field must contain one of a fixed set of values (e.g., "account_type must be one of: savings, checking, trust")
   - `REFERENTIAL_INTEGRITY`: Record in one file must have a matching record in another (e.g., "account_id must exist in Customer file")
   - `OWNERSHIP_CATEGORY`: Account ownership classifications (e.g., "joint account", "trust account")
   - `BENEFICIAL_OWNERSHIP_THRESHOLD`: Numeric triggers for beneficial owners (e.g., "25% ownership")
   - `DOCUMENTATION_REQUIREMENT`: Required documents or records (e.g., "must maintain W-9 forms")
   - `UPDATE_REQUIREMENT`: Event-triggered record updates (e.g., "update within 30 days of address change")
   - `UPDATE_TIMELINE`: Time-bound deadlines or SLAs (e.g., "annual certification required")
   - `CONTROL_REQUIREMENT`: Control-specific requirements
   - `RISK_STATEMENT`: Risk-related statements

3. **`RULE_TYPE_CODES`**: Maps rule types to 2-3 character codes for ID generation
   - `DATA_QUALITY_THRESHOLD` → "DQ"
   - `ENUMERATION_CONSTRAINT` → "EC"
   - `REFERENTIAL_INTEGRITY` → "RI"
   - `OWNERSHIP_CATEGORY` → "OWN"
   - `BENEFICIAL_OWNERSHIP_THRESHOLD` → "BO"
   - `DOCUMENTATION_REQUIREMENT` → "DOC"
   - `UPDATE_REQUIREMENT` → "UPD"
   - `UPDATE_TIMELINE` → "TL"
   - `CONTROL_REQUIREMENT` → "CTL"
   - `RISK_STATEMENT` → "RSK"

These codes are used to generate readable IDs like "DQ-a1b2c3", "OWN-d4e5f6", etc. (prefix + 6-char SHA-256 hash).

### Agent1 Pipeline - Advanced Processing

Agent1 is a sophisticated multi-stage pipeline for extracting granular regulatory requirements. It includes deterministic preprocessing, schema inference, confidence gating, and comprehensive quality evaluation.

#### Node 1: Preprocessor (`nodes/preprocessor.py`)

**Purpose**: Deterministic (no-LLM) document parsing into structured chunks

The preprocessor is the foundation of the Agent1 pipeline. It parses documents without using an LLM, ensuring consistent, reproducible results.

**Key Features**:
- **Deterministic**: Same input always produces same output
- **Fast**: No LLM API calls, pure Python parsing
- **Structured**: Preserves document hierarchy (headings, lists, tables)
- **Configurable**: Adjustable chunk sizes for downstream processing

**Supported Formats**:
- **DOCX**: Full support with table detection, heading hierarchy, list parsing
- **Other formats**: Not supported (raises `ValueError`)

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
from nodes.preprocessor import parse_and_chunk

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

#### Node 2: Schema Discovery (`nodes/schema_discovery.py`)

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
schema_discovery_agent(state: Phase1State) -> dict
# Returns dict with "schema_map" key containing a SchemaMap object
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
1. Takes the pipeline state (with all preprocessed chunks) as input
2. Performs stratified sampling (up to 15 chunks across different chunk types)
3. Sends sampled chunks to Claude with the schema discovery prompt
4. LLM analyzes structure and returns JSON schema
5. Calculates average confidence across all fields
6. Caches the result by document hash for re-use
7. Returns updated state with `schema_map` key

#### Node 3: Confidence Gate (`nodes/confidence_gate.py`)

**Purpose**: Decision gate that validates schema quality before proceeding

The Confidence Gate implements a structured decision-making process. It prevents the pipeline from continuing with low-quality schemas.

**Decision Logic**:
```
IF avg_confidence >= 0.85 THEN auto_accept
ELSE IF avg_confidence >= 0.50 THEN human_review
ELSE IF has_required_fields THEN schema_compliance_ok
ELSE reject
```

**Thresholds** (configured in `config/gate_config.yaml` and `config/pipeline_config.yaml`):
- **auto_accept_threshold**: 0.85 (high confidence, proceed automatically)
- **human_review_threshold**: 0.50 (medium confidence, flag for review)
- **min_schema_compliance**: 0.50 (minimum schema quality)
- **min_coverage**: 0.60 (minimum coverage threshold)

**Key Function**:
```python
check_confidence(state: Phase1State) -> GateDecision
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

#### Node 4: Requirement Atomizer (`nodes/atomizer/`)

**Purpose**: Extracts granular regulatory requirements with confidence scoring

The Atomizer is the core extraction node. It takes schema-validated chunks and extracts individual requirements using LLM-powered analysis.

**Architecture**:
The atomizer is built from four sub-components:

1. **`BatchProcessor`** (`batch_processor.py`):
   - Batches chunks for efficient LLM processing
   - Manages rate limits and retries
   - Handles partial failures gracefully

2. **`PromptBuilder`** (`prompt_builder.py`):
   - Loads prompts from `src/prompts/`
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
    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        self.model_name = model_name
        self.batch_processor = BatchProcessor(model_name)
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        self.repairer = SchemaRepairer()
    
    def __call__(
        self, 
        state: Phase1State
    ) -> Phase1State
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

1. **Grounding Match** (35% weight): How well the requirement text matches source text
2. **Completeness** (25% weight): Are all required fields present?
3. **Quantification** (15% weight): Does it include measurable criteria?
4. **Schema Compliance** (10% weight): Does it match expected schema?
5. **Coherence** (10% weight): Is the text logical and clear?
6. **Domain Signals** (5% weight): Contains domain-specific keywords?

Confidence scores are computed by `scoring/confidence_scorer.py`.

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

#### Node 5: Quality Evaluation (`eval/eval_node.py`)

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

#### Scoring System (`scoring/`)

**Purpose**: Multi-factor confidence scoring for extracted requirements

The scoring system computes confidence scores (0.0-1.0) for each requirement based on six factors:

1. **`confidence_scorer.py`**: Main scoring orchestrator
   - Weights: grounding (35%), completeness (25%), quantification (15%), schema (10%), coherence (10%), domain (5%)
   - Returns score between 0.0 and 1.0

2. **`grounding.py`**: Text matching logic
   - Uses Jaccard similarity to measure overlap between requirement text and source
   - Returns match score and grounding classification (EXACT/PARAPHRASE/INFERENCE)

3. **`verb_replacer.py`**: Vague verb detection
   - Scans for weak/vague verbs: "should", "may", "could", "might", "consider", "optionally"
   - Strong verbs: "must", "shall", "will", "required", "prohibited"

4. **`features.py`**: Feature extraction for scoring
   - `compute_completeness(req)`: Checks for required fields
   - `compute_quantification(req)`: Detects numeric thresholds
   - `compute_schema_compliance(req, schema)`: Validates against schema
   - `compute_coherence(req)`: Assesses text quality

#### Data Models (`models/`)

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
   - `ChunkSkipRecord`: Record of a skipped chunk with reason

4. **`state.py`**: Pipeline state
   - `Phase1State`: TypedDict for pipeline state management

5. **`grc_components.py`**: GRC component models
   - `PolicyComponent`, `RiskComponent`, `ControlComponent`
   - `GRCComponentsResponse`: Aggregated extraction result

6. **`control_metadata/`**: Control enrichment
   - Infers control-specific metadata (control type, owner, frequency)
   - Uses templates and patterns to enrich control requirements

#### Parsers (`parsers/`)

**Purpose**: Format-specific document parsers

1. **`docx_parser.py`**: DOCX parsing
   - Parses paragraphs, tables, lists
   - Detects heading hierarchy
   - Preserves table structure
   - Returns ContentChunk list

#### Utilities (`utils/`)

**Purpose**: Helper functions used across the pipeline

1. **`chunking.py`**: Chunk management
   - `generate_chunk_id(file_path, position, content)`: Creates stable SHA-based chunk IDs
   - Ensures deterministic, collision-free IDs

2. **`llm_client.py`**: Anthropic client factory
   - `get_anthropic_client()`: Returns configured Anthropic client (SSL handling for corporate proxies)
   - `call_anthropic(prompt, model, ...)`: Centralized API call with token tracking
   - Default model: `claude-sonnet-4-20250514`

3. **`error_handler.py`**: Standardized error handling
   - `APIError`: Custom exception for LLM API errors
   - `handle_anthropic_error()`: Translates Anthropic errors with context
   - `exit_with_error()`: Graceful CLI exit with error details

#### Cache (`cache/`)

**Purpose**: Schema caching for performance

1. **`schema_cache.py`**: Cache implementation
   - Caches SchemaMap results by document hash
   - Avoids redundant LLM calls for same documents

#### Insights Generator (`nodes/insights_generator.py`)

**Purpose**: Post-processing narrative insights without additional LLM calls

After quality evaluation, the Insights Generator analyzes extraction results and produces structured insights:

1. **Quality Assessment**: Scores schema completeness, grounding quality, and data source coverage; returns an overall quality tier (Excellent/Good/Fair/Needs Review)
2. **Risk Flags**: Identifies issues such as low data source coverage, schema compliance problems, fragment context warnings, and low-confidence requirements
3. **Hallucination Risk**: Summarizes hallucination count and severity based on eval report flags
4. **Confidence Distribution**: Breakdown of requirements by confidence tier (high/medium/low)
5. **Recommendations**: Actionable suggestions for improving extraction quality

**Key Functions**:
```python
generate_insights(requirements, extraction_metadata, gate_decision) -> InsightsResult
insights_to_dict(insights: InsightsResult) -> dict
```

The insights are embedded directly in the output `requirements.json` under the `"insights"` key.

### Module Interaction Flow

Here's how the modules work together in a typical extraction workflow:

**Scenario 1: Full Atomization**
```
User runs: python -m src.cli atomize --input doc.docx

Flow:
1. cli.py::run_atomizer() called
2. Executes 6-stage pipeline:
   - Stage 1: nodes.preprocessor.parse_and_chunk()
     → Returns PreprocessorOutput with chunks
   - Stage 2: nodes.schema_discovery.schema_discovery_agent()
     → Returns SchemaMap (with caching)
   - Stage 3: nodes.confidence_gate.check_confidence()
     → Returns GateDecision (accept/human_review/reject)
   - Stage 3.5: nodes.grc_extractor.GRCComponentExtractorNode()
     → Returns GRCComponentsResponse (policies, risks, controls)
   - Stage 4: nodes.atomizer.RequirementAtomizerNode()
     → Returns List[RegulatoryRequirement] with confidence scores
   - Stage 5: eval.eval_node.eval_quality()
     → Returns EvalReport with quality metrics
   - Post: nodes.insights_generator.generate_insights()
     → Returns InsightsResult (quality, risk flags, recommendations)
3. cli.py writes requirements.json with embedded insights
```

**Scenario 2: Preprocessing Only**
```
User runs: python -m src.cli preprocess --input doc.docx

Flow:
1. cli.py::run_preprocess() called
2. Calls nodes.preprocessor.parse_and_chunk()
   → Uses parsers.docx_parser
   → Uses utils.chunking for ID generation
3. cli.py writes preprocess_{stem}_{run_id}.json
```

### Integration Points

**Where Modules Connect**:

1. **models.shared → pipeline**:
   - RuleType enum used for validation and ID generation
   - RuleCategory enum used for classification
   - RULE_TYPE_CODES used for requirement IDs (e.g., "R-DQ-a1b2c3")

## Installation

### Prerequisites

- Python 3.10 or higher (3.11+ recommended)
- Virtual environment (recommended)
- Anthropic API key (`ANTHROPIC_API_KEY`)

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

Edit `.env` to add your API key:
```
ANTHROPIC_API_KEY=your_anthropic_key
```

## Usage

### Data Preparation

Place your source document in the `data/` directory:
```
data/FDIC_Part370_IT_Controls.docx
```

Note: The `data/` directory is gitignored to prevent accidental commits of sensitive documents.

### Command-Line Interface

#### Preprocess a Document (No LLM)

Parse a DOCX into structured chunks:
```bash
python -m src.cli preprocess --input data/FDIC_370_GRC_Library_National_Bank.docx --output chunks.json
```

#### Discover Document Schema

Infer document structure using the LLM:
```bash
python -m src.cli discover-schema --input data/FDIC_370_GRC_Library_National_Bank.docx --output schema.json
```

#### Full Pipeline Extraction (Atomize)

Extract regulatory requirements using the complete 6-stage pipeline:
```bash
python -m src.cli atomize --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

Alternatively, if you installed the package:
```bash
kratos-discover atomize --input data/FDIC_370_GRC_Library_National_Bank.docx --output results.json
```

#### Advanced Options

Specify a custom output directory:
```bash
python -m src.cli atomize --input data/document.docx --output-dir ./my_outputs
```

Adjust logging level:
```bash
python -m src.cli atomize --input data/document.docx --log-level DEBUG
```

### Programmatic API

```python
import os
import subprocess
from pathlib import Path

# Use the CLI to run the full Agent1 pipeline programmatically
result = subprocess.run(
    [
        "python", "-m", "src.cli", "atomize",
        "--input", os.getenv("FDIC_370_PATH", "data/document.docx"),
        "--output", "outputs/requirements.json",
    ],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    import json
    with open("outputs/requirements.json") as f:
        data = json.load(f)
    requirements = data.get("requirements", [])
    print(f"Extracted {len(requirements)} requirements")
    eval_report = data.get("eval_report", {})
    print(f"Quality Score: {eval_report.get('overall_quality_score', 0):.2%}")
else:
    print(f"Error: {result.stderr}")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | **Required** |
| `ANTHROPIC_VERIFY_SSL` | Enable SSL verification (set `true` for non-proxy environments) | `false` |
| `KRATOS_OUTPUT_DIR` | Directory for output files | `outputs` |
| `KRATOS_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### Regulatory Requirement Model

The `RegulatoryRequirement` model represents a single extracted requirement from the Agent1 pipeline.

```python
class RegulatoryRequirement(BaseModel):
    requirement_id: str             # Unique identifier format: R-{TYPE_CODE}-{HASH6}
    rule_type: RuleType             # Type of requirement (see RuleType enum)
    rule_description: str           # Plain-English statement of the obligation
    grounded_in: str                # Verbatim text from source that supports this requirement
    confidence: float               # Confidence score from 0.50 to 0.99
    attributes: Dict[str, Any]      # Type-specific structured attributes
    metadata: RuleMetadata          # Source information and extraction metadata
```

**Example Requirement**:
```json
{
  "requirement_id": "R-DQ-a1b2c3",
  "rule_type": "data_quality_threshold",
  "rule_description": "Customer name accuracy must be at least 95%",
  "grounded_in": "Section 2.3 states that institutions must maintain customer name records with a minimum accuracy threshold of 95 percent.",
  "confidence": 0.87,
  "attributes": {
    "metric": "accuracy",
    "threshold_value": 95,
    "threshold_direction": ">=",
    "threshold_unit": "%"
  },
  "metadata": {
    "source_chunk_id": "chunk_42",
    "source_location": "Section 2.3",
    "schema_version": "1.0",
    "prompt_version": "v2.1",
    "extraction_iteration": 1
  }
}
```

### Agent1 Data Models

Agent1 uses additional specialized models for its advanced processing pipeline.

#### ContentChunk

Represents a single chunk of parsed document content.

```python
class ContentChunk(BaseModel):
    chunk_id: str               # Unique identifier (e.g., "chunk_001")
    chunk_type: str             # "prose", "heading", "list", or "table"
    text: str                   # The actual content text
    metadata: Dict[str, Any]    # Additional metadata (page, heading, table_data)
```

**Example Chunk**:
```json
{
  "chunk_id": "chunk_042",
  "chunk_type": "table",
  "text": "Requirement ID | Description | Owner\nREQ-001 | Data quality checks | Data Team",
  "metadata": {
    "page": 5,
    "heading_context": "Data Quality Requirements",
    "table_data": [
      ["Requirement ID", "Description", "Owner"],
      ["REQ-001", "Data quality checks", "Data Team"]
    ]
  }
}
```

#### RegulatoryRequirement

Represents a single extracted regulatory requirement from Agent1's atomizer.

```python
class RegulatoryRequirement(BaseModel):
    requirement_id: str         # Unique identifier with type code (e.g., "DQ-001")
    rule_type: RuleType         # Type from models.shared.RuleType enum
    category: RuleCategory      # Category from models.shared.RuleCategory enum
    description: str            # Human-readable requirement description
    grounded_in: str            # Source text excerpt
    confidence: float           # Confidence score (0.0 to 1.0)
    attributes: Dict[str, Any]  # Structured attributes
    metadata: Dict[str, Any]    # Extraction metadata
```

**Example Requirement**:
```json
{
  "requirement_id": "BO-003",
  "rule_type": "beneficial_ownership_threshold",
  "category": "rule",
  "description": "Beneficial ownership must be identified for individuals owning 25% or more",
  "grounded_in": "Section 4.2: Any individual with 25 percent or greater ownership stake must be identified as a beneficial owner.",
  "confidence": 0.92,
  "attributes": {
    "threshold_percentage": 25,
    "applies_to": "beneficial owners",
    "identification_required": true
  },
  "metadata": {
    "source_chunk_id": "chunk_078",
    "extraction_timestamp": "2026-02-18T03:10:36Z",
    "confidence_factors": {
      "grounding_match": 0.95,
      "completeness": 0.90,
      "quantification": 1.0,
      "schema_compliance": 0.88,
      "coherence": 0.92,
      "domain_signals": 0.85
    }
  }
}
```

#### SchemaMap

Represents the discovered structure of a document from Agent1's schema discovery.

```python
class SchemaMap(BaseModel):
    structural_pattern: str                 # Document pattern type
    entities: List[DiscoveredEntity]        # Discovered logical entities
    relationships: List[Dict[str, Any]]     # Entity relationships
    anomalies: List[str]                    # Detected structural issues
    confidence_avg: float                   # Average confidence across all fields
```

**Example SchemaMap**:
```json
{
  "structural_pattern": "vertical_table",
  "entities": [
    {
      "name": "Data Quality Requirements",
      "entity_type": "table",
      "fields": [
        {
          "name": "requirement_id",
          "confidence": 0.95,
          "data_type": "string",
          "examples": ["DQ-001", "DQ-002", "DQ-003"]
        },
        {
          "name": "threshold",
          "confidence": 0.88,
          "data_type": "percentage",
          "examples": ["95%", "99%", "90%"]
        }
      ]
    }
  ],
  "relationships": [],
  "anomalies": ["Missing header in section 3"],
  "confidence_avg": 0.87
}
```

### Enum Types (from `models.shared`)

#### RuleCategory

```python
class RuleCategory(str, Enum):
    RULE = "rule"           # Regulatory rule or requirement
    CONTROL = "control"     # Control measure or safeguard
    RISK = "risk"           # Risk statement or concern
```

#### RuleType

```python
class RuleType(str, Enum):
    DATA_QUALITY_THRESHOLD = "data_quality_threshold"
    ENUMERATION_CONSTRAINT = "enumeration_constraint"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    OWNERSHIP_CATEGORY = "ownership_category"
    BENEFICIAL_OWNERSHIP_THRESHOLD = "beneficial_ownership_threshold"
    DOCUMENTATION_REQUIREMENT = "documentation_requirement"
    UPDATE_REQUIREMENT = "update_requirement"
    UPDATE_TIMELINE = "update_timeline"
    CONTROL_REQUIREMENT = "control_requirement"
    RISK_STATEMENT = "risk_statement"
```

### Model Validation

All models use Pydantic for automatic validation:

- **Type Checking**: Ensures fields have correct types
- **Required Fields**: Validates presence of mandatory fields
- **Constraints**: Enforces value ranges (e.g., confidence 0.5-0.99)
- **Custom Validators**: Applies business logic validation

**Example Validation Error**:
```python
# This will raise ValidationError
rule = Rule(
    rule_id="DQ-001",
    category="invalid_category",  # ❌ Not in RuleCategory enum
    rule_type="data_quality_threshold",
    rule_description="...",
    grounded_in="...",
    confidence=1.5,  # ❌ Must be between 0.5 and 0.99
    attributes={},
    metadata={}
)
```

## Complete API Reference

This section provides detailed API documentation for programmatic usage of kratos-discover components.

### CLI Module (`src.cli`)

#### Main Entry Point

```python
def main():
    """Main CLI entry point with argument parsing."""
```

**Subcommands**:
- `preprocess` - Deterministic document parsing (Node 1)
- `discover-schema` - Schema discovery (Nodes 1-3)
- `atomize` - Complete Agent1 pipeline (Nodes 1-5 + Insights Generator)

### Preprocessor (`nodes.preprocessor`)

#### parse_and_chunk

```python
def parse_and_chunk(
    file_path: Path,
    file_type: str,
    max_chunk_chars: int = 3000,
    min_chunk_chars: int = 50
) -> PreprocessorOutput:
    """
    Parse document and chunk into structured content blocks.
    
    Args:
        file_path: Path to document file
        file_type: "docx" (only supported format)
        max_chunk_chars: Maximum characters per chunk (default: 3000)
        min_chunk_chars: Minimum characters per chunk (default: 50)
    
    Returns:
        PreprocessorOutput with:
            - chunks: List[ContentChunk]
            - document_stats: Dict with word_count, page_count, table_count
            - total_chunks: int
    
    Raises:
        FileNotFoundError: If file_path doesn't exist
        ValueError: If file_type is not "docx"
    
    Example:
        from pathlib import Path
        from nodes.preprocessor import parse_and_chunk
        
        result = parse_and_chunk(
            file_path=Path("document.docx"),
            file_type="docx",
            max_chunk_chars=2000
        )
        print(f"Created {result.total_chunks} chunks")
        for chunk in result.chunks[:5]:
            print(f"{chunk.chunk_id}: {chunk.chunk_type}")
    """
```

### Schema Discovery (`nodes.schema_discovery`)

#### schema_discovery_agent

```python
def schema_discovery_agent(state: Phase1State) -> dict:
    """
    Infer document structure using Claude LLM analysis.
    
    Args:
        state: Phase1State containing 'chunks', 'prompt_versions', and 'errors'
    
    Returns:
        Updated state dict with 'schema_map' key (SchemaMap) and 'prompt_versions'
    
    Example:
        from nodes.schema_discovery import schema_discovery_agent
        
        state = {"chunks": chunks, "prompt_versions": {}, "errors": [],
                 "file_path": "document.docx"}
        result = schema_discovery_agent(state)
        schema = result.get("schema_map")
        
        print(f"Pattern: {schema.structural_pattern}")
        print(f"Entities: {len(schema.entities)}")
        print(f"Confidence: {schema.avg_confidence:.2f}")
    """
```

### Confidence Gate (`nodes.confidence_gate`)

#### check_confidence

```python
def check_confidence(state: Phase1State) -> GateDecision:
    """
    Evaluate schema quality and make gate decision.
    
    Args:
        state: Phase1State with 'schema_map' key set
    
    Returns:
        GateDecision with:
            - decision: "accept" | "human_review" | "reject"
            - score: float
            - failing_checks: List[str]
            - conditional_flags: List[str]
            - rationale: str explaining the decision
    
    Decision Logic:
        - score >= 0.85: accept
        - score >= 0.50: human_review
        - score < 0.50: reject
    
    Example:
        from nodes.confidence_gate import check_confidence
        
        gate_decision = check_confidence(state)
        
        if gate_decision.decision == "reject":
            print(f"Rejected: {gate_decision.rationale}")
            sys.exit(1)
        elif gate_decision.decision == "human_review":
            print(f"Warning: {gate_decision.rationale}")
    """
```

### Atomizer (`nodes.atomizer`)

#### RequirementAtomizerNode

```python
class RequirementAtomizerNode:
    """
    Extracts atomic regulatory requirements with confidence scoring.
    
    Attributes:
        model_name: LLM model identifier (default: claude-sonnet-4-20250514)
        batch_processor: BatchProcessor for efficient API calls
        response_parser: ResponseParser for JSON parsing
        schema_repairer: SchemaRepairer for error recovery
    """
    
    def __init__(self): ...
    
    def __call__(
        self,
        state: Phase1State
    ) -> Phase1State:
        """
        Extract requirements from state using schema context.
        
        Args:
            state: Phase1State with chunks, schema_map, grc_components, and prompt_versions
        
        Returns:
            Updated Phase1State with requirements and extraction_metadata
        
        Example:
            from nodes.atomizer import RequirementAtomizerNode
            
            atomizer = RequirementAtomizerNode()
            result = atomizer(state)
            
            requirements = result.get("requirements", [])
            print(f"Extracted {len(requirements)} requirements")
            
            high_conf = [r for r in requirements if r.confidence >= 0.85]
            print(f"High confidence: {len(high_conf)}")
        """
```

### Evaluation (`eval.eval_node`)

#### eval_quality

```python
def eval_quality(state: Phase1State) -> dict:
    """
    Run comprehensive quality checks on extracted requirements.
    
    Args:
        state: Phase1State with 'requirements', 'chunks', and 'schema_map' set
    
    Returns:
        Updated state dict with 'eval_report' key containing:
            - failure_type: str
            - failure_severity: str
            - overall_quality_score: float (0.0 to 1.0)
            - hallucination_flags: List[dict]
            - testability_issues: List[dict]
            - grounding_issues: List[dict]
            - coverage_metrics: dict
    
    Quality Checks:
        1. Grounding (HIGH): Verifies text exists in source
        2. Testability (MEDIUM): Detects vague language
        3. Hallucination (CRITICAL): Identifies fabricated content
        4. Deduplication (LOW): Finds near-duplicates
        5. Schema Compliance (MEDIUM): Validates against schema
        6. Coverage (INFO): Measures extraction completeness
    
    Example:
        from eval.eval_node import eval_quality
        
        eval_result = eval_quality(state)
        eval_report = eval_result.get("eval_report", {})
        
        print(f"Quality Score: {eval_report.get('overall_quality_score', 0):.2%}")
    """
```

### Scoring Module (`scoring`)

#### ConfidenceScorer

```python
class ConfidenceScorer:
    """
    Multi-factor confidence scoring for requirements.
    
    Scoring Factors (weights):
        1. Grounding Match (40%): Text similarity to source
        2. Completeness (20%): All required fields present
        3. Quantification (15%): Contains measurable criteria
        4. Schema Compliance (10%): Matches expected schema
        5. Coherence (10%): Logical and clear text
        6. Domain Signals (5%): Domain-specific keywords
    """
    
    def score(
        self,
        requirement: RegulatoryRequirement,
        source_text: str,
        schema: SchemaMap
    ) -> float:
        """
        Calculate confidence score for a requirement.
        
        Args:
            requirement: The requirement to score
            source_text: Original source text for grounding
            schema: Schema for compliance check
        
        Returns:
            float: Confidence score from 0.0 to 1.0
        
        Example:
            from scoring.confidence_scorer import ConfidenceScorer
            
            scorer = ConfidenceScorer()
            confidence = scorer.score(requirement, source_chunk.text, schema)
            
            if confidence >= 0.85:
                print("✓ High confidence extraction")
            elif confidence >= 0.70:
                print("⚠ Medium confidence - review recommended")
            else:
                print("✗ Low confidence - needs review")
        """
```

#### GroundingVerifier

```python
class GroundingVerifier:
    """
    Verifies extractions against source text to prevent hallucinations.
    """
    
    def verify(
        self,
        extracted_text: str,
        source_chunks: List[ContentChunk],
        threshold: float = 0.70
    ) -> Tuple[bool, float, str]:
        """
        Verify extracted text exists in source.
        
        Args:
            extracted_text: The text to verify (e.g., requirement description)
            source_chunks: Original content chunks
            threshold: Minimum similarity score (0.0 to 1.0)
        
        Returns:
            Tuple of (is_grounded, similarity_score, matching_chunk_id)
        
        Example:
            from scoring.grounding import GroundingVerifier
            
            verifier = GroundingVerifier()
            is_grounded, score, chunk_id = verifier.verify(
                requirement.rule_description,
                chunks,
                threshold=0.75
            )
            
            if not is_grounded:
                print(f"⚠️  Not grounded (score: {score:.2f})")
            else:
                print(f"✓ Grounded in {chunk_id} (score: {score:.2f})")
        """
```

### Prompt Files (`src/prompts/`)

Prompts are stored as YAML files in `src/prompts/`:
- `requirement_atomizer/`: Versioned prompts for the requirement atomizer node (`v1.0.yaml`, `v1.0_retry.yaml`)
- `schema_discovery/`: Versioned prompts for the schema discovery node (`v1.0.yaml`)
- `grc_extractor/`: Versioned prompts for the GRC extractor node (`v1.0.yaml`)
- `registry.yaml`: Maps prompt names to active versions

The atomizer node loads prompts automatically from these YAML files at runtime.

### Data Models API

#### ContentChunk

```python
@dataclass
class ContentChunk:
    """
    Represents a parsed document chunk.
    
    Attributes:
        chunk_id: Unique identifier (e.g., "chunk_001")
        chunk_type: "prose" | "heading" | "list" | "table"
        text: Actual content text
        metadata: Dict with page, heading, table_data, etc.
    """
    chunk_id: str
    chunk_type: str
    text: str
    metadata: Dict[str, Any]
```

#### SchemaMap

```python
@dataclass
class SchemaMap:
    """
    Document structure schema.
    
    Attributes:
        structural_pattern: Overall document structure type
        entities: List[Entity] - discovered entities
        relationships: List[Relationship] - connections between entities
        anomalies: List[str] - detected issues
        confidence_avg: Average confidence across all fields
    """
    structural_pattern: str
    entities: List[Entity]
    relationships: List[Relationship]
    anomalies: List[str]
    confidence_avg: float
```

#### RegulatoryRequirement

```python
@dataclass
class RegulatoryRequirement:
    """
    Atomic regulatory requirement.
    
    Attributes:
        requirement_id: Unique ID with type prefix (e.g., "DQ-001")
        rule_type: RuleType enum value
        category: "rule" | "control" | "risk"
        description: Human-readable requirement text
        grounded_in: Source text excerpt
        confidence: Score from 0.0 to 1.0
        attributes: Dict of extracted attributes
        metadata: Dict with extraction metadata
    """
    requirement_id: str
    rule_type: RuleType
    category: str
    description: str
    grounded_in: str
    confidence: float
    attributes: Dict[str, Any]
    metadata: Dict[str, Any]
```

## Configuration Guide

### Complete Configuration Options

#### Environment Variables Reference

```bash
# === LLM Provider Configuration ===
ANTHROPIC_API_KEY=sk-ant-...             # Required
ANTHROPIC_VERIFY_SSL=false               # Set true outside corporate proxy

# === Output Configuration ===
KRATOS_OUTPUT_DIR=outputs                # Default output directory
KRATOS_LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

The LLM model and most pipeline parameters are configured in `src/config/pipeline_config.yaml`. The default model is `claude-sonnet-4-20250514`.

#### YAML Configuration Files

##### Gate Configuration (`config/gate_config.yaml`)

```yaml
# Confidence gate thresholds (document-type-specific)
thresholds:
  grc_export:
    auto_accept: 0.85
    human_review: 0.50
    min_schema_compliance: 0.50
    min_coverage: 0.60
  regulatory_docx:
    auto_accept: 0.80
    human_review: 0.40
    min_schema_compliance: 0.50
    min_coverage: 0.60
  default:
    auto_accept: 0.85
    human_review: 0.50
    min_schema_compliance: 0.50
    min_coverage: 0.60
```

##### Prompt Registry (`src/prompts/registry.yaml`)

```yaml
# Active prompt versions (managed by PromptRegistry)
requirement_atomizer: "v1.0"
schema_discovery: "v1.0"
grc_extractor: "v1.0"
```

### Configuration Profiles

Create different configuration profiles for different use cases:

#### Development Profile (`.env.dev`)

```bash
ANTHROPIC_API_KEY=sk-ant-...
KRATOS_LOG_LEVEL=DEBUG
```

Adjust pipeline parameters in `src/config/pipeline_config.yaml`:
```yaml
llm:
  model: "claude-haiku-4-20250514"   # Faster, cheaper for development
preprocessing:
  max_chunk_chars: 2000              # Smaller for testing
```

#### Production Profile (`.env.prod`)

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_VERIFY_SSL=true
KRATOS_LOG_LEVEL=INFO
KRATOS_OUTPUT_DIR=/data/outputs
```

### Using Configuration Profiles

```bash
# Load specific .env file
python -m src.cli atomize --input document.docx --dotenv .env.prod

# Override log level at runtime
python -m src.cli atomize --input document.docx --log-level DEBUG
```

## Advanced Usage

### Custom Extraction Workflows

#### Batch Processing Multiple Documents

```python
from pathlib import Path
from nodes.preprocessor import parse_and_chunk
from nodes.atomizer import RequirementAtomizerNode

# Initialize atomizer once
atomizer = RequirementAtomizerNode()

# Process multiple documents
documents = Path("data/").glob("*.docx")
all_requirements = []

for doc in documents:
    print(f"Processing {doc.name}...")
    
    # Preprocess
    result = parse_and_chunk(doc, "docx")
    
    # Extract requirements using full pipeline via CLI
    # (or use atomizer directly with state dict)
    requirements = []
    all_requirements.extend(requirements)
    
    print(f"  Processed {result.total_chunks} chunks")
```

#### Custom Confidence Threshold Filtering

```python
from eval.eval_node import eval_quality

# Extract requirements
requirements = atomizer.atomize(chunks, schema)

# Evaluate quality
eval_report = eval_quality(requirements, chunks, schema)

# Filter by confidence and quality
high_quality = [
    req for req in requirements
    if req.confidence >= 0.85
    and req.requirement_id not in [f.requirement_id for f in eval_report.detailed_failures if f.severity in ["critical", "high"]]
]

medium_quality = [
    req for req in requirements
    if 0.70 <= req.confidence < 0.85
]

needs_review = [
    req for req in requirements
    if req.confidence < 0.70
]

print(f"High quality: {len(high_quality)}")
print(f"Medium quality: {len(medium_quality)}")
print(f"Needs review: {len(needs_review)}")
```

#### Custom Rule Type Detection

```python
from models.shared import RuleType, RULE_TYPE_CODES

# Add custom rule type logic
def classify_requirement(requirement: RegulatoryRequirement) -> RuleType:
    """Custom classification logic"""
    text = requirement.rule_description.lower()
    
    # Check for quantitative thresholds
    if any(keyword in text for keyword in ["must be", "≥", ">=", "%", "threshold"]):
        return RuleType.DATA_QUALITY_THRESHOLD
    
    # Check for documentation keywords
    elif any(keyword in text for keyword in ["document", "record", "maintain", "file"]):
        return RuleType.DOCUMENTATION_REQUIREMENT
    
    # Check for timeline keywords
    elif any(keyword in text for keyword in ["within", "days", "annual", "monthly", "deadline"]):
        return RuleType.UPDATE_TIMELINE
    
    # Default
    return RuleType.UPDATE_REQUIREMENT

# Apply to requirements
for req in requirements:
    if not req.rule_type:
        req.rule_type = classify_requirement(req)
```

### Integration with External Systems

#### Export to CSV for Excel

```python
import csv
from pathlib import Path

def export_to_csv(requirements: List[RegulatoryRequirement], output_path: Path):
    """Export requirements to CSV format."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "ID", "Type", "Description", 
            "Confidence", "Source Text", "Attributes"
        ])
        
        # Data rows
        for req in requirements:
            writer.writerow([
                req.requirement_id,
                req.rule_type.value,
                req.rule_description,
                f"{req.confidence:.2f}",
                req.grounded_in[:200],  # Truncate long text
                str(req.attributes)
            ])

# Usage
export_to_csv(requirements, Path("outputs/requirements.csv"))
```

#### Integration with GRC Platform APIs

```python
import requests
from typing import List

def upload_to_grc_platform(
    requirements: List[RegulatoryRequirement],
    api_url: str,
    api_key: str
):
    """Upload requirements to external GRC platform."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Convert to platform format
    payload = {
        "requirements": [
            {
                "external_id": req.requirement_id,
                "title": req.rule_description[:100],
                "description": req.rule_description,
                "type": req.rule_type.value,
                "confidence_score": req.confidence,
                "source_reference": req.grounded_in,
                "custom_attributes": req.attributes,
                "metadata": req.metadata.model_dump() if req.metadata else {}
            }
            for req in requirements
        ]
    }
    
    # Upload
    response = requests.post(
        f"{api_url}/api/v1/requirements/bulk",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✓ Uploaded {len(requirements)} requirements")
    else:
        print(f"✗ Upload failed: {response.status_code}")
        print(response.text)

# Usage
upload_to_grc_platform(
    requirements,
    api_url="https://grc-platform.example.com",
    api_key=os.getenv("GRC_API_KEY")
)
```

#### Database Integration

```python
import sqlite3
from datetime import datetime

def save_to_database(requirements: List[RegulatoryRequirement], db_path: str):
    """Save requirements to SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_id TEXT UNIQUE,
            rule_type TEXT,
            rule_description TEXT,
            grounded_in TEXT,
            confidence REAL,
            attributes TEXT,
            metadata TEXT,
            created_at TIMESTAMP
        )
    """)
    
    # Insert requirements
    for req in requirements:
        cursor.execute("""
            INSERT OR REPLACE INTO requirements 
            (requirement_id, rule_type, rule_description, grounded_in, 
             confidence, attributes, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.requirement_id,
            req.rule_type.value,
            req.rule_description,
            req.grounded_in,
            req.confidence,
            str(req.attributes),
            str(req.metadata),
            datetime.utcnow()
        ))
    
    conn.commit()
    conn.close()
    print(f"✓ Saved {len(requirements)} requirements to {db_path}")

# Usage
save_to_database(requirements, "outputs/requirements.db")
```

## Performance Optimization

### Chunking Strategy Optimization

#### Choosing Optimal Chunk Size

```python
# For dense regulatory text with short requirements
MAX_CHUNK_SIZE = 2000  # Smaller chunks, more precise extraction
MIN_CHUNK_SIZE = 100

# For narrative documents with long requirements
MAX_CHUNK_SIZE = 4000  # Larger chunks, preserve context
MIN_CHUNK_SIZE = 200

# For tables and structured data
MAX_CHUNK_SIZE = 5000  # Very large chunks, preserve table structure
MIN_CHUNK_SIZE = 50
```

#### Performance vs. Cost Trade-offs

```python
import time

def benchmark_extraction(
    file_path: Path,
    chunk_sizes: List[int],
    provider: str
):
    """Benchmark different chunk sizes."""
    results = []
    
    for max_size in chunk_sizes:
        start = time.time()
        
        # Preprocess with specific chunk size
        result = parse_and_chunk(file_path, "docx", max_chunk_chars=max_size)
        
        elapsed = time.time() - start
        
        results.append({
            "chunk_size": max_size,
            "num_chunks": result.total_chunks,
            "num_requirements": len(requirements),
            "time_seconds": elapsed,
            "cost_estimate": result.total_chunks * 0.015  # $0.015 per chunk est.
        })
    
    return results

# Run benchmark
results = benchmark_extraction(
    Path("data/document.docx"),
    chunk_sizes=[1000, 2000, 3000, 4000],
    provider="anthropic"
)

for r in results:
    print(f"Chunk Size: {r['chunk_size']}")
    print(f"  Chunks: {r['num_chunks']}, Requirements: {r['num_requirements']}")
    print(f"  Time: {r['time_seconds']:.1f}s, Est. Cost: ${r['cost_estimate']:.2f}")
```

### Caching Strategies

#### Schema Caching for Similar Documents

```python
from cache.schema_cache import SchemaCache

# Initialize cache
cache = SchemaCache(cache_dir=Path(".cache"))

# Check cache before discovery
schema = cache.get(document_hash)
if schema is None:
    # Not in cache, discover
    schema = schema_discovery_agent(chunks, llm)
    
    # Save to cache
    cache.set(document_hash, schema, ttl=3600)
    print("Schema discovered and cached")
else:
    print("Schema loaded from cache")
```

#### LLM Response Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=128)
def cached_llm_call(prompt_hash: str) -> str:
    """Cache LLM responses for identical prompts (by hash)."""
    from utils.llm_client import call_anthropic
    response, _, _ = call_anthropic(prompt_hash, model="claude-haiku-4-20250514", max_tokens=1000)
    return response

# Usage
prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
response = cached_llm_call(prompt_hash)
```

### Parallel Processing

#### Process Multiple Documents in Parallel

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def process_document(file_path: Path) -> List[RegulatoryRequirement]:
    """Process single document (thread-safe)."""
    # LLM is configured via environment variables (ANTHROPIC_API_KEY)
    result = parse_and_chunk(file_path, "docx")
    # Use the CLI pipeline for full extraction; this is a preprocessing-only example
    return []

def process_batch(file_paths: List[Path], max_workers: int = 4):
    """Process multiple documents in parallel."""
    all_requirements = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_document, path): path
            for path in file_paths
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            path = futures[future]
            try:
                requirements = future.result()
                all_requirements.extend(requirements)
                print(f"✓ {path.name}: {len(requirements)} requirements")
            except Exception as e:
                print(f"✗ {path.name}: {str(e)}")
    
    return all_requirements

# Usage
documents = list(Path("data/").glob("*.docx"))
requirements = process_batch(documents, max_workers=4)
print(f"Total: {len(requirements)} requirements")
```

### Model Selection Guidelines

| Use Case | Recommended Model | Rationale |
|----------|-------------------|-----------|
| **Development/Testing** | `claude-haiku-4-20250514` | Fastest, cheapest, good for iteration |
| **Production (Quality)** | `claude-opus-4-20250805` | Best accuracy, grounding, reasoning |
| **Production (Balanced)** | `claude-sonnet-4-20250514` | Good balance of speed/cost/quality (default) |

The model is configured in `src/config/pipeline_config.yaml` under `llm.model`.

### Cost Optimization

```python
# Calculate estimated cost
def estimate_cost(
    num_chunks: int,
    model: str,
    avg_chunk_size: int = 2000
) -> float:
    """Estimate processing cost."""
    # Cost per 1M tokens (approximate pricing - check Anthropic docs for current rates)
    costs = {
        "claude-opus-4-20250805": {"input": 15.00, "output": 75.00},
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    }
    
    # Estimate tokens (rough: 1 token ≈ 4 chars)
    input_tokens = (num_chunks * avg_chunk_size) / 4
    output_tokens = num_chunks * 500  # Estimate 500 tokens per output
    
    model_cost = costs.get(model, costs["claude-sonnet-4-20250514"])
    
    total_cost = (
        (input_tokens / 1_000_000) * model_cost["input"] +
        (output_tokens / 1_000_000) * model_cost["output"]
    )
    
    return total_cost

# Usage
num_chunks = 150
print(f"Estimated costs for {num_chunks} chunks:")
for model in ["claude-opus-4-20250805", "claude-sonnet-4-20250514", "claude-haiku-4-20250514"]:
    cost = estimate_cost(num_chunks, model)
    print(f"  {model}: ${cost:.2f}")
```

## Integration Patterns

### Webhook Integration

```python
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract_endpoint():
    """Webhook endpoint for document extraction."""
    # Get uploaded file
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    file_path = Path(f"/tmp/{file.filename}")
    file.save(file_path)
    
    try:
        # Process document
        result = parse_and_chunk(file_path, "docx")
        schema = schema_discovery_agent(result.chunks, llm)
        requirements = atomizer.atomize(result.chunks, schema)
        eval_report = eval_quality(requirements, result.chunks, schema)
        
        # Return results
        return jsonify({
            "success": True,
            "total_requirements": len(requirements),
            "quality_score": eval_report.quality_score,
            "requirements": [req.dict() for req in requirements],
            "eval_report": eval_report.dict()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Cleanup
        if file_path.exists():
            file_path.unlink()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### Message Queue Integration (Celery)

```python
from celery import Celery
from pathlib import Path

app = Celery('kratos', broker='redis://localhost:6379/0')

@app.task
def process_document_async(file_path: str, callback_url: str = None):
    """Async task for document processing."""
    # Process
    result = parse_and_chunk(Path(file_path), "docx")
    schema = schema_discovery_agent(result.chunks, llm)
    requirements = atomizer.atomize(result.chunks, schema)
    
    # Save results
    output_path = Path(f"outputs/{Path(file_path).stem}_requirements.json")
    with open(output_path, 'w') as f:
        json.dump([req.dict() for req in requirements], f, indent=2)
    
    # Callback if provided
    if callback_url:
        requests.post(callback_url, json={
            "status": "complete",
            "output_file": str(output_path),
            "num_requirements": len(requirements)
        })
    
    return str(output_path)

# Usage
result = process_document_async.delay(
    file_path="/data/document.docx",
    callback_url="https://api.example.com/webhook"
)
print(f"Task ID: {result.id}")
```

### REST API Integration

```python
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid

app = FastAPI(title="Kratos-Discover API")

# In-memory task store (use Redis in production)
tasks = {}

@app.post("/api/v1/extract")
async def extract_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload document for extraction."""
    # Generate task ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "processing", "progress": 0}
    
    # Save file
    file_path = Path(f"/tmp/{task_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Start background processing
    background_tasks.add_task(process_in_background, task_id, file_path)
    
    return JSONResponse({
        "task_id": task_id,
        "status": "processing",
        "status_url": f"/api/v1/status/{task_id}"
    })

@app.get("/api/v1/status/{task_id}")
def get_status(task_id: str):
    """Check extraction status."""
    if task_id not in tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse(tasks[task_id])

@app.get("/api/v1/results/{task_id}")
def get_results(task_id: str):
    """Get extraction results."""
    if task_id not in tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    task = tasks[task_id]
    if task["status"] != "complete":
        return JSONResponse({"error": "Task not complete"}, status_code=400)
    
    return JSONResponse(task["results"])

def process_in_background(task_id: str, file_path: Path):
    """Background processing task."""
    try:
        tasks[task_id]["progress"] = 20
        result = parse_and_chunk(file_path, "docx")
        
        tasks[task_id]["progress"] = 40
        schema = schema_discovery_agent(result.chunks, llm)
        
        tasks[task_id]["progress"] = 70
        requirements = atomizer.atomize(result.chunks, schema)
        
        tasks[task_id]["progress"] = 90
        eval_report = eval_quality(requirements, result.chunks, schema)
        
        tasks[task_id] = {
            "status": "complete",
            "progress": 100,
            "results": {
                "requirements": [req.dict() for req in requirements],
                "eval_report": eval_report.dict()
            }
        }
    
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "error": str(e)
        }
    
    finally:
        file_path.unlink()  # Cleanup

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Best Practices

### Document Preparation

#### Optimize Documents for Extraction

1. **Clean Formatting**:
   - Remove unnecessary formatting
   - Use consistent heading styles (Heading 1, 2, 3)
   - Avoid manual line breaks and spacing

2. **Table Structure**:
   - Use proper Word tables, not tabs/spaces
   - Include clear headers
   - Avoid merged cells when possible

3. **Text Quality**:
   - Fix OCR errors if document was scanned
   - Ensure text is selectable (not images)
   - Remove boilerplate headers/footers

#### Document Quality Checklist

```python
def check_document_quality(file_path: Path) -> Dict[str, Any]:
    """Pre-check document quality."""
    from docx import Document
    
    doc = Document(file_path)
    
    checks = {
        "has_headings": any(p.style.name.startswith("Heading") for p in doc.paragraphs),
        "has_tables": len(doc.tables) > 0,
        "has_text": any(p.text.strip() for p in doc.paragraphs),
        "page_count": len(doc.sections),
        "table_count": len(doc.tables),
        "word_count": sum(len(p.text.split()) for p in doc.paragraphs),
        "issues": []
    }
    
    # Check for issues
    if not checks["has_headings"]:
        checks["issues"].append("No heading styles detected - may impact segmentation")
    
    if checks["word_count"] < 100:
        checks["issues"].append("Document is very short - may not have enough content")
    
    if checks["word_count"] > 100000:
        checks["issues"].append("Document is very large - consider splitting")
    
    return checks

# Usage
quality = check_document_quality(Path("document.docx"))
if quality["issues"]:
    print("⚠️  Quality issues:")
    for issue in quality["issues"]:
        print(f"  - {issue}")
```

### Prompt Engineering

#### Effective Prompt Design

1. **Be Specific**:
   ```yaml
   # Bad
   instructions: "Extract rules from the document"
   
   # Good
   instructions: |
     Extract regulatory rules that:
     1. Specify measurable requirements (e.g., ≥95% accuracy)
     2. Include clear action verbs (must, shall, will)
     3. Define specific entities (customers, accounts, records)
     4. Contain compliance obligations
   ```

2. **Provide Examples**:
   ```yaml
   examples: |
     Example 1:
     Input: "Banks must maintain customer records with ≥95% accuracy."
     Output:
     {
       "rule_id": "DQ-001",
       "rule_type": "data_quality_threshold",
       "description": "Customer records must have ≥95% accuracy",
       "attributes": {"threshold": "95%", "metric": "accuracy", "applies_to": "customer records"}
     }
   ```

3. **Define Anti-Patterns**:
   ```yaml
   anti_patterns: |
     DO NOT extract:
     - Examples or illustrations ("e.g., ...", "for example")
     - Definitions or explanations
     - Background information
     - Aspirational statements ("should consider", "may want to")
   ```

### Error Handling

#### Robust Error Handling Pattern

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_extract(
    file_path: Path,
    max_retries: int = 3
) -> Optional[List[RegulatoryRequirement]]:
    """Extract with error handling and retries."""
    for attempt in range(max_retries):
        try:
            # Preprocess
            result = parse_and_chunk(file_path, "docx")
            logger.info(f"Preprocessed: {result.total_chunks} chunks")
            
            # Discover schema
            schema = schema_discovery_agent(result.chunks, llm)
            logger.info(f"Discovered schema: confidence={schema.confidence_avg:.2f}")
            
            # Check confidence gate
            gate_decision = check_confidence(schema)
            if gate_decision.decision == "reject":
                logger.error(f"Schema rejected: {gate_decision.rationale}")
                return None
            
            # Extract
            requirements = atomizer.atomize(result.chunks, schema)
            logger.info(f"Extracted {len(requirements)} requirements")
            
            # Evaluate
            eval_report = eval_quality(requirements, result.chunks, schema)
            logger.info(f"Quality score: {eval_report.quality_score:.2%}")
            
            # Filter critical failures
            if eval_report.failures_by_severity.get("critical", 0) > 0:
                logger.warning("Critical quality failures detected")
            
            return requirements
        
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying ({attempt + 2}/{max_retries})...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error("Max retries exceeded")
                return None
    
    return None
```

### Quality Assurance

#### Automated Quality Checks

```python
def validate_extraction_quality(
    requirements: List[RegulatoryRequirement],
    eval_report: EvalReport,
    min_quality_score: float = 0.75
) -> Tuple[bool, List[str]]:
    """Validate extraction meets quality standards."""
    issues = []
    
    # Check overall quality score
    if eval_report.quality_score < min_quality_score:
        issues.append(
            f"Quality score {eval_report.quality_score:.2%} below minimum {min_quality_score:.2%}"
        )
    
    # Check for critical failures
    if eval_report.failures_by_severity.get("critical", 0) > 0:
        issues.append(
            f"{eval_report.failures_by_severity['critical']} critical failures detected"
        )
    
    # Check minimum requirements extracted
    if len(requirements) < 5:
        issues.append(
            f"Only {len(requirements)} requirements extracted - may be incomplete"
        )
    
    # Check average confidence
    avg_confidence = sum(r.confidence for r in requirements) / len(requirements)
    if avg_confidence < 0.70:
        issues.append(
            f"Average confidence {avg_confidence:.2%} is low"
        )
    
    # Check coverage
    if eval_report.coverage_metrics.get("coverage_percentage", 0) < 60:
        issues.append(
            f"Coverage {eval_report.coverage_metrics['coverage_percentage']:.1f}% is low"
        )
    
    is_valid = len(issues) == 0
    return is_valid, issues

# Usage
is_valid, issues = validate_extraction_quality(requirements, eval_report)

if not is_valid:
    print("⚠️  Quality validation failed:")
    for issue in issues:
        print(f"  - {issue}")
    print("\nRecommendations:")
    print("  1. Try using Claude Opus for better quality")
    print("  2. Review document quality and formatting")
    print("  3. Adjust chunk sizes if needed")
    print("  4. Check prompt versions")
else:
    print("✓ Quality validation passed")
```

### Testing and Validation

#### Unit Test Example

```python
import pytest
from pathlib import Path

def test_parse_and_chunk():
    """Test document parsing."""
    result = parse_and_chunk(
        file_path=Path("tests/fixtures/sample.docx"),
        file_type="docx",
        max_chunk_chars=2000
    )
    
    assert result.total_chunks > 0
    assert len(result.chunks) == result.total_chunks
    assert all(chunk.chunk_id for chunk in result.chunks)
    assert all(chunk.chunk_type in ["prose", "heading", "list", "table"] 
               for chunk in result.chunks)

def test_schema_discovery():
    """Test schema discovery."""
    chunks = [...]  # Load test chunks
    state = {"chunks": chunks, "prompt_versions": {}, "errors": []}
    
    result = schema_discovery_agent(state)
    schema = result.get("schema_map")
    
    assert 0.0 <= schema.confidence_avg <= 1.0
    assert len(schema.entities) > 0
    assert schema.structural_pattern in [
        "vertical_table", "horizontal_table", "prose_with_tables", 
        "spreadsheet", "mixed"
    ]

def test_confidence_gate():
    """Test confidence gate logic."""
    # High confidence schema
    schema_high = SchemaMap(
        structural_pattern="vertical_table",
        entities=[...],
        confidence_avg=0.90
    )
    decision = check_confidence(schema_high)
    assert decision.decision == "auto_accept"
    
    # Low confidence schema
    schema_low = SchemaMap(
        structural_pattern="mixed",
        entities=[],
        confidence_avg=0.30
    )
    decision = check_confidence(schema_low)
    assert decision.decision == "reject"
```

#### Integration Test Example

```python
def test_end_to_end_extraction():
    """Test complete extraction pipeline."""
    # Setup
    file_path = Path("tests/fixtures/test_document.docx")
    
    # Preprocess
    result = parse_and_chunk(file_path, "docx")
    assert result.total_chunks > 0
    
    # Discover schema
    state = {"chunks": result.chunks, "prompt_versions": {}, "errors": []}
    schema_result = schema_discovery_agent(state)
    schema = schema_result.get("schema_map")
    assert schema.confidence_avg > 0.5
    
    # Extract requirements
    atomizer = RequirementAtomizerNode()
    state["schema_map"] = schema
    atomizer_result = atomizer(state)
    requirements = atomizer_result.get("requirements", [])
    assert len(requirements) > 0
    
    # Evaluate quality
    eval_report = eval_quality(requirements, result.chunks, schema)
    assert eval_report.quality_score > 0.5
    
    # Validate output format
    for req in requirements:
        assert req.requirement_id
        assert req.rule_type
        assert req.rule_description
        assert 0.0 <= req.confidence <= 1.0
```

### LLM Provider Selection

#### Choosing the Right Model

Kratos-Discover uses Anthropic Claude exclusively. Choose the right model size based on your needs:

**`claude-opus-4-20250805` (Best Quality)**:
- ✅ Best accuracy for regulatory text
- ✅ Better at following complex instructions
- ✅ Excellent for schema discovery
- ✅ Handles long documents well
- ❌ Slower and higher cost per token

**`claude-sonnet-4-20250514` (Default — Balanced)**:
- ✅ Strong balance of speed, cost, and quality
- ✅ Recommended for production workloads
- ✅ Good for schema discovery and atomization

**`claude-haiku-4-20250514` (Development/Testing)**:
- ✅ Fastest response times
- ✅ Lowest cost per token
- ✅ Good for rapid iteration
- ❌ May miss subtle requirements in complex documents

**Recommendations by Use Case**:
- **Development/Testing**: Use `claude-haiku-4-20250514` for speed and cost
- **Production**: Use `claude-sonnet-4-20250514` (default) or `claude-opus-4-20250805`
- **Complex/Critical Documents**: Use `claude-opus-4-20250805`

### Document Structure Optimization

**For Best Results**:

1. **Use Clear Headings**: Documents with clear heading hierarchy parse better
   ```
   ✅ Good:
   Heading 1: Data Requirements
     Heading 2: Quality Standards
       Heading 3: Accuracy Threshold
   
   ❌ Poor:
   All text with bold formatting, no heading styles
   ```

2. **Structure Tables Properly**: Use actual table elements, not formatted text
   ```
   ✅ Good: Word table with proper rows/columns
   ❌ Poor: Text formatted to look like a table using spaces/tabs
   ```

#### Full Pipeline (Recommended)

Run the complete extraction pipeline:
```bash
python cli.py atomize --input data/document.docx
```

With custom output path:
```bash
python cli.py atomize --input data/document.docx --output results.json
```

#### Preprocessing Only

Parse document into chunks without LLM processing:
```bash
python cli.py preprocess --input data/document.docx
```

#### Schema Discovery

Run preprocessing and schema discovery:
```bash
python cli.py discover-schema --input data/document.docx
```

### Programmatic API

```python
from pathlib import Path
from nodes.preprocessor import parse_and_chunk
from nodes.schema_discovery import schema_discovery_agent
from nodes.confidence_gate import check_confidence
from nodes.grc_extractor import GRCComponentExtractorNode
from nodes.atomizer import RequirementAtomizerNode
from eval.eval_node import eval_quality

# Node 1: Parse document
preprocessor_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx",
    max_chunk_chars=3000,
    min_chunk_chars=50,
)

# Build state for pipeline
state = {
    "chunks": preprocessor_output.chunks,
    "preprocessor_stats": preprocessor_output.document_stats,
}

# Node 2: Schema Discovery
schema_result = schema_discovery_agent(state)
state["schema_map"] = schema_result["schema_map"]

# Node 3: Confidence Gate
gate_result = check_confidence(state)
print(f"Gate decision: {gate_result.decision}")

# Node 3.5: GRC Extraction
grc_extractor = GRCComponentExtractorNode()
grc_result = grc_extractor(state)
state.update(grc_result)

# Node 4: Atomizer
atomizer = RequirementAtomizerNode()
atomizer_result = atomizer(state)
state.update(atomizer_result)

# Node 5: Eval
eval_result = eval_quality(state)
print(f"Quality score: {eval_result['eval_report']['overall_quality_score']}")
3. **Be Explicit**: Regulatory language should be clear and unambiguous
   ```
   ✅ Good: "Institutions must maintain 95% accuracy"
   ❌ Poor: "Institutions should aim for high accuracy"
   ```

4. **Include Context**: Provide section numbers and references
   ```
   ✅ Good: "Section 2.3: Customer name accuracy must be ≥95%"
   ❌ Poor: "Accuracy must be high"
   ```

### Tuning Extraction Parameters

**Adjust Chunk Sizes**:
```bash
# Smaller chunks (better for dense documents with short requirements)
python -m src.cli preprocess --input doc.docx --max-chunk-chars 2000 --min-chunk-chars 100

# Larger chunks (better for narrative documents with long requirements)
python -m src.cli preprocess --input doc.docx --max-chunk-chars 5000 --min-chunk-chars 200
```

**Use Appropriate Modes**:
- Use `atomize` command for production-quality extraction with full evaluation

**Enable Verbose Logging for Troubleshooting**:
```bash
# See intermediate outputs and what the LLM actually returns
python -m src.cli atomize --input document.docx --log-level DEBUG
```

## Understanding the Workflow

This section explains how Kratos-discover processes documents from start to finish, helping you understand when to use each component.

### Workflow 1: Document Preprocessing Only

**Use Case**: Parse document structure without LLM costs, for inspection or debugging.

**Steps**:
1. You provide a DOCX document
2. Agent1 preprocessor parses document deterministically
3. Document is split into chunks (headings, prose, lists, tables)
4. Each chunk gets a unique ID
5. Table structures are preserved
6. Document statistics are calculated
7. Chunks and stats are returned

**When to Use**: 
- Inspecting document structure before extraction
- Debugging parsing issues
- Creating input for custom processing
- Avoiding LLM costs for initial analysis

**Command**:
```bash
python -m src.cli preprocess --input doc.docx --output chunks.json
```

### Workflow 2: Schema Discovery

**Use Case**: Understand document structure before extraction.

**Steps**:
1. Document is preprocessed into chunks
2. Sample chunks are sent to LLM (Claude recommended)
3. LLM analyzes structure and identifies entities/fields
4. Schema map is created with confidence scores
5. Structural pattern is identified (vertical_table, prose_with_tables, etc.)
6. Relationships and anomalies are detected
7. Schema map is returned

**When to Use**:
- Before running full extraction on unfamiliar documents
- Understanding document organization
- Debugging extraction issues
- Validating document format

**Command**:
```bash
python -m src.cli discover-schema --input doc.docx --output schema.json
```

### Workflow 3: Advanced Atomization (Full Pipeline)

**Use Case**: Extract requirements with comprehensive quality assurance.

**Steps**:
1. **Node 1 - Preprocessing**: Document parsed into chunks (deterministic)
2. **Node 2 - Schema Discovery**: Structure inferred with LLM
3. **Node 3 - Confidence Gate**: Schema quality validated
   - If confidence < 0.50: Pipeline stops (reject)
   - If confidence 0.50-0.85: Proceeds with warning (human_review)
   - If confidence ≥ 0.85: Proceeds automatically (auto_accept)
4. **Node 4 - Atomization**: Requirements extracted with confidence scoring
   - Each requirement scored on 6 factors
   - Requirements below threshold filtered out
5. **Node 5 - Quality Evaluation**: Six quality checks run
   - Grounding check (hallucination prevention)
   - Testability check (vague language detection)
   - Hallucination check (fabricated data detection)
   - Deduplication check (duplicate detection)
   - Schema compliance check (schema validation)
   - Coverage analysis (extraction completeness)
6. Results returned with quality report

**When to Use**:
- Production extraction with quality guarantees
- Processing mission-critical compliance documents
- When you need detailed quality metrics
- When hallucination prevention is essential

**Command**:
```bash
python -m src.cli atomize --input doc.docx --output-dir ./results/
```

**Output Files**:
- `results/requirements.json`: Extracted requirements
- `results/evaluation.json`: Quality assessment report
- `results/schema.json`: Discovered document schema

### Workflow Comparison

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | Yes |

### Gate Thresholds

Confidence gate thresholds are configured in `src/config/gate_config.yaml`:

```yaml
auto_accept: 0.85      # Auto-accept above this
human_review: 0.70     # Human review between this and auto_accept
auto_reject: 0.50      # Auto-reject below this
```
| Feature | Preprocessing | Schema Discovery | Atomization |
|---------|---------------|------------------|-------------|
| **LLM Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Speed** | Very Fast | Fast | Slower |
| **Quality Checks** | None | N/A | Comprehensive |
| **Confidence Scoring** | N/A | Yes | Multi-factor |
| **Grounding Verification** | N/A | N/A | Yes + Extra Checks |
| **Deduplication** | N/A | N/A | Yes |
| **Schema Validation** | N/A | Yes | Yes + Compliance Check |
| **Quality Report** | No | No | ✅ Yes |
| **Best For** | Inspection | Structure analysis | Production use |

### Choosing the Right Workflow

**Choose Preprocessing when**:
- Inspecting document structure first
- Debugging parsing issues
- Building custom processing pipeline
- Avoiding LLM costs for exploration

**Choose Schema Discovery when**:
- Working with unfamiliar document formats
- Need to understand structure before extraction
- Planning extraction strategy
- Validating document format

**Choose Advanced Atomization when**:
- Processing production/critical documents
- Need comprehensive quality assurance
- Hallucination prevention is essential
- Want detailed quality metrics
- Budget allows for thorough processing

### Common Patterns

#### Pattern 1: Exploration → Extraction
```bash
# Step 1: Explore structure (no LLM cost)
python -m src.cli preprocess --input doc.docx --output chunks.json

# Step 2: Understand schema (small LLM cost)
python -m src.cli discover-schema --input doc.docx --output schema.json

# Step 3: Extract with full pipeline (higher cost, highest quality)
python -m src.cli atomize --input doc.docx --output-dir ./results/
```

#### Pattern 2: Quick Iteration
```bash
# Start with schema discovery to understand structure
python -m src.cli discover-schema --input doc.docx --output schema.json

# Review schema, then run full pipeline for production
python -m src.cli atomize --input doc.docx --output-dir ./production/
```

#### Pattern 3: Inspect Intermediate Outputs
```bash
# Step 1: Preprocess to inspect chunks
python -m src.cli preprocess --input doc.docx --output chunks.json
cat chunks.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Chunks: {d[\"total_chunks\"]}')"

# Step 2: Discover schema to inspect structure
python -m src.cli discover-schema --input doc.docx --output schema.json
cat schema.json
```

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
pytest tests/test_cli.py
pytest tests/test_agent1_preprocessor.py
```

## Quick Start Examples

### Example 1: Preprocess a Document (No LLM)

```bash
# Parse DOCX into structured chunks
python -m src.cli preprocess --input data/document.docx --output chunks.json

# Configure chunk sizes
python -m src.cli preprocess \
  --input data/document.docx \
  --max-chunk-chars 5000 \
  --min-chunk-chars 100 \
  --output chunks.json
```

### Example 2: Discover Document Schema

```bash
# Infer document structure using LLM
python -m src.cli discover-schema \
  --input data/document.docx \
  --output schema.json
```

### Example 3: Run Full Advanced Pipeline

```bash
# Execute complete 6-stage pipeline with quality evaluation and insights
python -m src.cli atomize \
  --input data/document.docx \
  --output-dir ./results/
```

## Project Structure
This creates output files in the results directory:
- `results/requirements_*.json`: Extracted requirements with quality report

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
- **XLSX/CSV/PDF/HTML**: ❌ Not supported (raises `ValueError`)

### Text Normalization

Agent1 applies minimal whitespace normalization:
- Trims trailing spaces per line
- Collapses repeated blank lines (max 2 consecutive)
- **Does NOT**: Remove punctuation, change capitalization, or alter words

### Package Layout

```
src/
├── __init__.py
├── cli.py               # CLI entry point (3 commands)
├── exceptions.py        # Custom exceptions
│
├── models/              # Data models (Pydantic)
│   ├── chunks.py        # ContentChunk, PreprocessorOutput
│   ├── schema_map.py    # SchemaMap, DiscoveredEntity, DiscoveredField
│   ├── requirements.py  # RegulatoryRequirement, ExtractionMetadata
│   ├── grc_components.py# PolicyComponent, RiskComponent, ControlComponent
│   ├── state.py         # Phase1State (pipeline state)
│   ├── shared.py        # RuleType, RuleCategory, RULE_TYPE_CODES
│   └── control_metadata/# Control enrichment logic
│
├── nodes/               # Processing nodes (pipeline stages)
│   ├── preprocessor.py  # Node 1: Deterministic parsing
│   ├── schema_discovery.py # Node 2: Structure inference
│   ├── confidence_gate.py  # Node 3: Quality gate
│   ├── grc_extractor.py    # Node 3.5: GRC component extraction
│   ├── insights_generator.py # Post-processing insights
│   └── atomizer/           # Node 4: Requirement extraction
│       ├── node.py
│       ├── batch_processor.py
│       ├── prompt_builder.py
│       ├── response_parser.py
│       └── schema_repair.py
│
├── parsers/             # Format-specific parsers
│   └── docx_parser.py  # DOCX → chunks (full support)
│
├── scoring/             # Confidence scoring system
│   ├── confidence_scorer.py
│   ├── grounding.py
│   ├── verb_replacer.py
│   └── features.py
│
├── eval/                # Node 5: Quality evaluation
│   ├── eval_node.py
│   ├── classifier.py
│   ├── models.py
│   └── checks/
│       ├── grounding.py
│       ├── testability.py
│       ├── hallucination.py
│       ├── deduplication.py
│       ├── schema_compliance.py
│       └── coverage.py
│
├── utils/               # Utility functions
│   ├── chunking.py      # Chunk ID generation
│   ├── llm_client.py    # Anthropic client factory
│   └── error_handler.py # APIError, exit_with_error
│
├── cache/               # Caching for performance
│   └── schema_cache.py  # SchemaMap caching by document hash
│
├── config/              # Configuration files
│   ├── pipeline_config.yaml  # LLM, pipeline, scoring parameters
│   ├── gate_config.yaml      # Confidence gate thresholds
│   └── loader.py             # Config loader utility
│
└── prompts/             # Versioned prompt YAML files
    ├── registry.yaml
    ├── requirement_atomizer/
    │   ├── v1.0.yaml
    │   └── v1.0_retry.yaml
    ├── schema_discovery/
    │   └── v1.0.yaml
    └── grc_extractor/
        └── v1.0.yaml
```

### Programmatic Usage

#### Example 1: Basic Preprocessing

```python
from pathlib import Path
from nodes.preprocessor import parse_and_chunk

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
from nodes.preprocessor import parse_and_chunk
from nodes.schema_discovery import schema_discovery_agent
from nodes.confidence_gate import check_confidence

# Step 1: Preprocess document
prep_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx"
)

# Step 2: Discover schema (via state dict)
state = {
    "file_path": str(prep_output.file_path),
    "chunks": prep_output.chunks,
    "prompt_versions": {},
    "errors": [],
}
schema_result = schema_discovery_agent(state)
schema = schema_result.get("schema_map")

print(f"Discovered {len(schema.entities)} entities")
print(f"Average confidence: {schema.avg_confidence:.2f}")
print(f"Structural pattern: {schema.structural_pattern}")

# Step 3: Check schema confidence
state["schema_map"] = schema
gate_decision = check_confidence(state)

if gate_decision.decision == "accept":
    print("✅ Schema quality is high, proceeding with extraction")
elif gate_decision.decision == "human_review":
    print("⚠️  Schema quality is medium, recommend human review")
else:
    print("❌ Schema quality is low, cannot proceed")
    
print(f"Confidence score: {gate_decision.score:.2f}")
print(f"Rationale: {gate_decision.rationale}")
```

#### Example 3: Extract Requirements with Atomizer

```python
from pathlib import Path
from nodes.preprocessor import parse_and_chunk
from nodes.schema_discovery import schema_discovery_agent
from nodes.atomizer import RequirementAtomizerNode

# Run preprocessing
prep_output = parse_and_chunk(
    file_path=Path("data/document.docx"),
    file_type="docx"
)

# Run schema discovery
state = {
    "file_path": str(prep_output.file_path),
    "chunks": prep_output.chunks,
    "prompt_versions": {},
    "errors": [],
}
schema_result = schema_discovery_agent(state)
schema = schema_result.get("schema_map")

# Extract requirements with atomizer
state["schema_map"] = schema
atomizer = RequirementAtomizerNode()
atomizer_result = atomizer(state)
requirements = atomizer_result.get("requirements", [])

print(f"Extracted {len(requirements)} requirements")

# Show first requirement
if requirements:
    req = requirements[0]
    print(f"ID: {req.requirement_id}")
    print(f"Type: {req.rule_type}")
    print(f"Description: {req.rule_description}")
    print(f"Confidence: {req.confidence:.2f}")
    print(f"Grounded in: {req.grounded_in[:200]}...")
```

#### Example 4: Quality Evaluation

```python
from eval.eval_node import eval_quality

# After extraction, evaluate quality (pass the state dict)
state["requirements"] = requirements
state["extraction_metadata"] = atomizer_result.get("extraction_metadata")
eval_result = eval_quality(state)
eval_report = eval_result.get("eval_report", {})

print(f"Quality Score: {eval_report.get('overall_quality_score', 0):.2%}")
print(f"Failure type: {eval_report.get('failure_type', 'none')}")
print(f"Severity: {eval_report.get('failure_severity', 'low')}")
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

Agent1 has comprehensive test coverage across all modules. Tests are located in `tests/`.

**Test Strategy**:
- **No Binary Fixtures**: Tests generate `.docx` files at runtime (no committed binary files)
- **Deterministic**: Tests verify that same input produces same output
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test full pipeline flows

**Running Agent1 Tests**:

```bash
# Run all agent1 tests
pytest tests/

# Run specific test file
pytest tests/test_agent1_preprocessor.py

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

**Test Files**:
- `test_agent1_preprocessor.py`: Preprocessing and chunking tests
- `test_schema_discovery.py`: Schema discovery tests
- `test_atomizer.py`: Requirement extraction tests
- `test_confidence_gate.py`: Gate decision tests
- `test_eval_node.py`: Quality evaluation tests

**Example Test Output**:
```
tests/test_atomizer.py::test_atomizer_extracts_requirements PASSED
tests/test_atomizer.py::test_atomizer_confidence_scoring PASSED
tests/test_schema_discovery.py::test_schema_discovery_vertical_table PASSED
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
├── cli.py                      # CLI wrapper
├── README.md                   # Project documentation
├── pyproject.toml              # Python package configuration
├── requirements.txt            # Python dependencies
│
├── src/                        # Source code
│   ├── cli.py                  # Main CLI implementation
│   ├── exceptions.py           # Custom exceptions
│   │
│   ├── nodes/                  # Pipeline nodes
│   │   ├── preprocessor.py    # Node 1: Parse & Chunk
│   │   ├── schema_discovery.py # Node 2: Schema Discovery
│   │   ├── confidence_gate.py # Node 3: Confidence Gate
│   │   ├── grc_extractor.py   # Node 3.5: GRC Extraction
│   │   └── atomizer/          # Node 4: Atomizer
│   │
│   ├── eval/                   # Node 5: Quality Evaluation
│   │   ├── eval_node.py
│   │   ├── classifier.py
│   │   └── checks/            # Individual quality checks
│   │
│   ├── models/                 # Data models
│   │   ├── chunks.py
│   │   ├── requirements.py
│   │   ├── grc_components.py
│   │   ├── schema_map.py
│   │   └── state.py
│   │
│   ├── scoring/                # Confidence scoring
│   │   ├── confidence_scorer.py
│   │   ├── grounding.py
│   │   └── features.py
│   │
│   ├── parsers/                # Document parsers
│   ├── prompts/                # LLM prompt templates
│   ├── config/                 # Configuration files
│   ├── cache/                  # Caching utilities
│   └── utils/                  # Utility functions
│
├── tests/                      # Test suite
├── wiki/                       # Documentation
├── dashboard/                  # React compliance dashboard
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
│   ├── shared/                 # Shared models and utilities
│   └── nodes/           # Pipeline nodes
│       ├── __init__.py
│       ├── exceptions.py
│       ├── models/             # Data models
│       ├── nodes/              # Processing nodes
│       ├── parsers/            # Document parsers
│       └── utils/              # Utility functions
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
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

## Quality Assurance

### Confidence Scoring
### Debug Mode

Use verbose logging to get visibility into the extraction pipeline:

```bash
python -m src.cli atomize --input doc.docx --log-level DEBUG
```

Use `preprocess` and `discover-schema` separately to inspect intermediate outputs:
```bash
python -m src.cli preprocess --input doc.docx --output chunks.json
python -m src.cli discover-schema --input doc.docx --output schema.json
```

Multi-dimensional confidence scoring with features:
- **Grounding Match**: Jaccard similarity with source text
- **Completeness**: Required field coverage
- **Quantification**: Presence of measurable values
- **Schema Compliance**: Schema validation status
- **Coherence**: Internal consistency
- **Domain Signals**: Domain-specific indicators

### Grounding Classification

Each extraction is classified:
- **EXACT**: Direct quote from source (Jaccard > 0.70)
- **PARAPHRASE**: Rephrased content (Jaccard 0.30-0.70)
- **INFERENCE**: Inferred content (Jaccard < 0.30) - requires human review

### Quality Evaluation

The eval node performs comprehensive checks:
- Testability assessment
- Hallucination detection
- Deduplication analysis
- Schema compliance verification
- Coverage analysis

## Troubleshooting

### Common Issues and Solutions

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'` or similar import errors

**Solutions**:
```bash
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # Unix/Mac
# 1. Ensure virtual environment is activated
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 2. Reinstall dependencies
pip install -r requirements.txt

# 3. Install in editable mode
pip install -e .

# 4. Verify Python version (requires 3.10+)
python --version

# 5. Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### API Key Errors

**Problem**: `AuthenticationError: Invalid API key` or `API key not found`

**Solutions**:
```bash
# 1. Verify environment variable is set
echo $ANTHROPIC_API_KEY

# On Windows
echo %ANTHROPIC_API_KEY%

# 2. Check .env file exists and is loaded
cat .env

# 3. Test Anthropic key:
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"

# 4. Reload environment variables
source .env  # or restart terminal
```

#### File Not Found Errors

**Problem**: `FileNotFoundError: [Errno 2] No such file or directory`

**Solutions**:
```bash
# 1. Check file exists
ls -la data/document.docx

# 2. Use absolute paths
python -m src.cli atomize --input /full/path/to/document.docx

# 3. Check current directory
pwd  # Should be in kratos-discover root

# 4. Verify file permissions
chmod +r data/document.docx
```

#### LLM Timeout Errors

**Problem**: `TimeoutError: Request timed out` or `ReadTimeout`

**Solutions**:
```bash
# 1. Adjust timeout in pipeline_config.yaml or check network
# The Anthropic client uses httpx defaults; for slow networks increase batch delays

# 2. Process smaller chunks (preprocess first to check chunk sizes)
python -m src.cli preprocess \
  --input document.docx \
  --max-chunk-chars 2000

# 3. Use faster model (update pipeline_config.yaml)
# Change: llm.model: "claude-haiku-4-20250514"
python -m src.cli atomize \
  --input document.docx

# 4. Enable verbose logging to see where it hangs
python -m src.cli atomize --input document.docx --log-level DEBUG
```

#### Rate Limiting Errors

**Problem**: `RateLimitError: Rate limit exceeded` or `429 Too Many Requests`

**Solutions**:
```python
# 1. Add retry logic with exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def call_llm_with_retry(llm, prompt):
    return llm.invoke(prompt)

# 2. Reduce batch size
export ATOMIZER_BATCH_SIZE=5  # Default is 10

# 3. Add delays between batches
import time
for batch in batches:
    process_batch(batch)
    time.sleep(2)  # 2 second delay

# 4. Use different API key or upgrade plan
```

#### Memory Errors

**Problem**: `MemoryError` or system becomes unresponsive

**Solutions**:
```bash
# 1. Process in smaller chunks (preprocess first to check sizes)
python -m src.cli preprocess \
  --input large_document.docx \
  --max-chunk-chars 1500

# 2. Disable caching if memory constrained
export ENABLE_CACHING=false

# 3. Process documents individually instead of batch
for file in data/*.docx; do
    python -m src.cli atomize --input "$file"
done

# 4. Increase system memory or use swap
# Monitor memory usage:
watch -n 1 free -h
```

#### JSON Parsing Errors

**Problem**: `JSONDecodeError: Expecting value` or malformed JSON

**Solutions**:
```python
# 1. Enable schema repair
# This is enabled by default in atomizer

# 2. Check LLM response with verbose logging
python -m src.cli atomize --input document.docx --log-level DEBUG
# Then inspect outputs/*.json

# 3. Try different model (Claude often produces better JSON)
# Set ANTHROPIC_API_KEY in your .env and use CLAUDE_MODEL env var

# 4. Validate JSON manually
import json
with open("outputs/raw_extraction.json") as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON error at line {e.lineno}, column {e.colno}")
        print(f"Error: {e.msg}")
```

#### Low Quality Extractions

**Problem**: Low confidence scores, many failures in quality report

**Diagnostics**:
```python
# Check quality report
cat outputs/*_eval.json | grep -A5 "quality_score"

# Identify failure patterns
cat outputs/*_eval.json | jq '.failures_by_check'
```

**API Key Errors**: Verify environment variable is set
```bash
echo $ANTHROPIC_API_KEY
```

**File Not Found**: Check that input document path is correct
```bash
ls data/
```

### Logging

The system uses `structlog` for structured logging. Key events:
- `parse_started`: Document parsing begins
- `parse_completed`: Chunk counts and statistics
- `schema_discovery_complete`: Schema inference results
- `gate_decision`: Accept/review/reject decision
- `atomizer_complete`: Extraction statistics
**Solutions by Failure Type**:

1. **High Grounding Failures**:
   ```bash
   # Document may have poor formatting or OCR issues
   # Solutions:
   # - Clean document formatting
   # - Use smaller chunk sizes to preserve context
   python -m src.cli preprocess --input doc.docx --max-chunk-chars 2000
   ```

2. **High Testability Failures**:
   ```bash
   # Document has vague language ("should", "may", "could")
   # Solutions:
   # - This is often correct - document IS vague
   # - Flag for human review
   # - Use verb replacement utility
   python -c "
   from scoring.verb_replacer import VerbReplacer
   replacer = VerbReplacer()
   text = 'Banks should maintain records'
   fixed = replacer.strengthen(text)
   print(fixed)  # 'Banks must maintain records'
   "
   ```

3. **High Hallucination Failures**:
   ```bash
   # LLM is fabricating content
   # Solutions:
   # - Use a larger Claude model (update pipeline_config.yaml)
   # - Change: llm.model: "claude-opus-4-20250805"
   python -m src.cli atomize --input doc.docx
   
   # - Use stricter prompts
   # - Lower temperature (already 0.0 by default)
   ```

4. **High Deduplication Failures**:
   ```bash
   # Document has repetitive content (often normal)
   # Solutions:
   # - This is usually correct - document IS repetitive
   # - Adjust deduplication threshold if too aggressive
   export EVAL_DEDUP_THRESHOLD=0.90  # Default is 0.85
   ```

5. **Low Coverage**:
   ```bash
   # Not extracting from all chunks
   # Solutions:
   # - Document may have non-regulatory content (normal)
   # - Check if chunks are appropriate size
   python -m src.cli preprocess --input doc.docx
   # Review chunk types and content
   ```

#### Schema Discovery Failures

**Problem**: Schema confidence too low, gate rejects

**Solutions**:
```bash
# 1. Check schema output
python -m src.cli discover-schema --input document.docx
# Review entity structure

# 2. Use Claude Opus for better schema discovery (update pipeline_config.yaml)
# Change: llm.model: "claude-opus-4-20250805"
python -m src.cli atomize \
  --input document.docx

# 3. Lower gate threshold (if acceptable)
# Edit config/gate_config.yaml:
thresholds:
  default:
    auto_accept: 0.75  # Was 0.85
    human_review: 0.40  # Was 0.50

# 4. Check document structure
# - Does it have clear tables or structure?
# - Is text clear and well-formatted?
# - Try restructuring document for clarity
```

#### Performance Issues

**Problem**: Extraction is very slow

**Diagnostics**:
```bash
# Time the extraction
time python -m src.cli atomize --input document.docx
```

**Solutions**:
```bash
# 1. Use faster model (update pipeline_config.yaml)
# Change: llm.model: "claude-haiku-4-20250514"
python -m src.cli atomize --input doc.docx

# 2. Enable caching (schema results are cached by document hash automatically)

# 3. Process in parallel (for multiple documents)
# See "Parallel Processing" section in Performance Optimization

# 4. Profile the code
python -m cProfile -o profile.stats -m src.cli atomize --input doc.docx
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# 5. Check network latency
ping api.anthropic.com
```

#### Debugging Techniques

##### Enable Verbose Logging

```bash
# Set log level to DEBUG
export KRATOS_LOG_LEVEL=DEBUG
python -m src.cli atomize --input document.docx

# Or use CLI flag (on any subcommand)
python -m src.cli atomize --log-level DEBUG --input document.docx
```

##### Inspect Intermediate Outputs

```bash
# Run preprocessing separately to inspect chunks
python -m src.cli preprocess --input document.docx --output chunks.json
cat chunks.json | jq '.chunks[0:3]'

# Run schema discovery to inspect structure
python -m src.cli discover-schema --input document.docx --output schema.json
cat schema.json | jq '.schema_map.entities'
```

##### Test Components Individually

```python
# Test preprocessing only
python -m src.cli preprocess --input document.docx --output test_chunks.json

# Test schema discovery only
python -m src.cli discover-schema --input document.docx

# Test extraction on specific chunk
from nodes.preprocessor import parse_and_chunk
result = parse_and_chunk(Path("document.docx"), "docx")
print(result.chunks[0])  # Inspect first chunk
```

##### Check LLM Responses

```python
# Make direct LLM call to test
from utils.llm_client import call_anthropic

response, input_tokens, output_tokens = call_anthropic(
    prompt="Extract one regulatory rule from this text: 'Banks must maintain customer records with 95% accuracy.'",
    model="claude-haiku-4-20250514",
    max_tokens=1000
)
print(response)
```

### Error Messages Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `ModuleNotFoundError: No module named 'src'` | Python can't find src package | `pip install -e .` |
| `AuthenticationError: Invalid API key` | API key missing/invalid | Set `ANTHROPIC_API_KEY` |
| `FileNotFoundError: document.docx` | File doesn't exist | Check path, use absolute path |
| `TimeoutError: Request timed out` | LLM request too slow | Use faster model (`claude-haiku-4-20250514`) |
| `RateLimitError: Rate limit exceeded` | Too many API requests | Add delays, reduce batch size |
| `JSONDecodeError: Expecting value` | Invalid JSON from LLM | Enable repair, try different model |
| `ValidationError: confidence must be between 0.5 and 0.99` | Invalid confidence value | Check scoring logic |
| `MemoryError: Unable to allocate` | Out of memory | Smaller chunks, process individually |
| `SchemaRejectedException: Schema confidence too low` | Poor schema quality | Better document structure, lower threshold |

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Review debug logs for detailed error information
2. **Search Issues**: Check [GitHub Issues](https://github.com/sumitasthana/kratos-discover/issues)
3. **Enable Verbose Logging**: Run with `--log-level DEBUG` flag to see detailed outputs
4. **Minimal Reproduction**: Create smallest example that reproduces the issue
5. **Report Bug**: Open issue with:
   - Full error message and stack trace
   - Steps to reproduce
   - Python version, OS, package versions
   - Sample document (if possible, non-sensitive)
   - Debug artifacts (if applicable)

### Performance Benchmarks

Typical performance on a standard document (50 pages, 150 chunks):

| Pipeline | Model | Time | Cost | Quality Score |
|----------|-------|------|------|---------------|
| Agent1 | claude-opus-4-20250805 | ~8 min | ~$2.50 | 0.85-0.92 |
| Agent1 | claude-sonnet-4-20250514 | ~5 min | ~$0.60 | 0.80-0.88 |
| Agent1 | claude-haiku-4-20250514 | ~3 min | ~$0.10 | 0.75-0.83 |

*Note: Performance varies based on document complexity and server load. Costs are estimates — check Anthropic pricing for current rates.*

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
  atomize --input data/document.docx
```

### Using Docker Compose

```bash
# Start services
docker-compose up

# Run extraction
docker-compose run kratos-discover \
  atomize --input data/document.docx
```

For detailed deployment instructions, see the [Deployment Guide](wiki/Deployment-Guide.md).

## Documentation

Comprehensive documentation is available in the [wiki](wiki/) directory:

- **[Home](wiki/Home.md)** - Overview and quick start
- **[Architecture](wiki/Architecture.md)** - System design and folder structure
- **[Usage Guide](wiki/Usage-Guide.md)** - CLI and API usage
- **[Phase1-Parse-and-Chunk](wiki/Phase1-Parse-and-Chunk.md)** - Preprocessor node
- **[Phase1-Schema-Discovery-Agent](wiki/Phase1-Schema-Discovery-Agent.md)** - Schema discovery
- **[Phase1-Confidence-Scorer](wiki/Phase1-Confidence-Scorer.md)** - Confidence gate
- **[Phase1-GRC-Extractor](wiki/Phase1-GRC-Extractor.md)** - GRC extraction
- **[Phase1-Atomizer-Agent](wiki/Phase1-Atomizer-Agent.md)** - Requirement atomization
- **[Phase1-Eval](wiki/Phase1-Eval.md)** - Quality evaluation

## License

This project is provided as-is for regulatory compliance document processing. See `pyproject.toml` for license details (MIT).

## Technology Stack

- **Python 3.10+**: Primary language (3.11+ recommended)
- **Pydantic v2**: Data validation and models
- **structlog**: Structured logging
- **Anthropic SDK** (`anthropic`): LLM provider (Claude Sonnet 4 by default)
- **python-docx**: DOCX document parsing
- **PyYAML**: Prompt and configuration loading
- **python-dotenv**: Environment variable management
- **httpx**: HTTP client with SSL proxy support
