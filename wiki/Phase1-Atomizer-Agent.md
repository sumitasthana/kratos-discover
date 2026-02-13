# Phase 1 Component: Atomizer Agent

**Status**: 🚧 Planned

## Overview

The Atomizer Agent is responsible for breaking down complex, compound rules and regulatory statements into atomic, indivisible units. This ensures that each extracted item represents a single, testable requirement or control.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Configuration](#configuration)
- [Atomization Strategy](#atomization-strategy)
- [Output Format](#output-format)
- [Next Steps](#next-steps)

## Purpose

*This component is currently in the planning phase. Content will be added as the component is developed.*

The Atomizer Agent will:
- Decompose compound rules into atomic statements
- Identify and separate multiple requirements within single text blocks
- Ensure each output represents a single, testable assertion
- Maintain traceability to source text
- Preserve relationships between related atomic items

## Key Features

*To be documented upon implementation*

### Planned Capabilities

- Compound statement detection
- Logical operator parsing (AND, OR, IF-THEN)
- Atomic unit extraction
- Relationship preservation
- Traceability maintenance
- Validation of atomicity

## Architecture

*Architecture details will be added during implementation*

### Planned Module Structure

```
src/atomizer/  (tentative)
  ├── __init__.py
  ├── atomizer.py
  ├── decomposer.py
  ├── relationship_tracker.py
  └── models/
      └── atomic_units.py
```

## Usage

*Usage examples will be provided once the component is implemented*

### Placeholder API

```python
# Tentative API design (subject to change)
from src.atomizer import AtomizerAgent

atomizer = AtomizerAgent()
atomic_items = atomizer.atomize(compound_rules)
```

## Configuration

*Configuration options will be documented during development*

### Expected Configuration Parameters

- Atomization granularity level
- Relationship preservation strategy
- Compound detection rules
- Validation thresholds

## Atomization Strategy

*Detailed atomization methodology will be defined during implementation*

### Examples of Atomization

#### Before Atomization
```
"All financial institutions must maintain adequate capital reserves 
AND submit quarterly reports to the regulatory authority."
```

#### After Atomization
```
Atomic Rule 1: "All financial institutions must maintain adequate capital reserves"
Atomic Rule 2: "All financial institutions must submit quarterly reports to the regulatory authority"
Relationship: Rule 1 AND Rule 2 (both required)
```

### Planned Decomposition Patterns

1. **Conjunction Splitting**: Breaking AND clauses
2. **Conditional Decomposition**: Separating IF-THEN statements
3. **List Expansion**: Expanding enumerated requirements
4. **Nested Rule Extraction**: Identifying embedded requirements

## Output Format

*Output format specifications will be defined during implementation*

### Expected Output Structure

```python
# Tentative structure
{
    "atomic_id": "ATOM_001",
    "parent_id": "RULE_001",
    "content": "Single atomic requirement",
    "type": "atomic_rule",
    "relationships": [
        {
            "related_to": "ATOM_002",
            "relationship_type": "AND"
        }
    ],
    "source_reference": {
        "original_id": "RULE_001",
        "text_span": [0, 50]
    },
    "metadata": {}
}
```

## Integration Points

### Input

Receives data from:
- **[Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md)**
- Existing extraction pipeline (RuleAgent)

### Output

Provides atomized data to:
- **[Confidence Scorer](Phase1-Confidence-Scorer.md)**
- **[Eval Component](Phase1-Eval.md)**

## Benefits of Atomization

### Why Atomize?

1. **Testability**: Each atomic unit can be independently verified
2. **Traceability**: Clear mapping to source requirements
3. **Reusability**: Atomic units can be composed into different rule sets
4. **Clarity**: Eliminates ambiguity in compound statements
5. **Compliance**: Easier to map to specific regulatory controls

## Development Status

**Current Status**: Not yet implemented

**Planned Timeline**: TBD

**Dependencies**: 
- Parse and Chunk component (✅ Complete)
- Schema Discovery Agent (🚧 Planned)

## Validation

The Atomizer Agent will include validation to ensure:
- Each atomic unit is truly indivisible
- No information is lost during decomposition
- Relationships are accurately preserved
- Source traceability is maintained

## Next Steps

This page will be updated with detailed documentation once the Atomizer Agent is implemented.

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md)
- [Confidence Scorer](Phase1-Confidence-Scorer.md)
- [Development Guide](Development-Guide.md)

---

**Questions or Feedback?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) to discuss the Atomizer Agent design.
