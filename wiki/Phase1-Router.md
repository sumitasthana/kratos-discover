# Phase 1 Component: Router

**Status**: 🚧 Planned

## Overview

The Router component is the intelligent routing layer that directs document chunks or extraction tasks to the most appropriate processing path based on content type, complexity, quality requirements, and other factors.

## Table of Contents

- [Purpose](#purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Routing Strategies](#routing-strategies)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Next Steps](#next-steps)

## Purpose

*This component is currently in the planning phase. Content will be added as the component is developed.*

The Router component will:
- Analyze incoming chunks to determine optimal processing path
- Route to different LLM providers based on complexity
- Direct to specialized extraction pipelines based on content type
- Implement fallback strategies for failed processing
- Optimize for cost, speed, or quality based on requirements
- Load balance across multiple processing resources

## Key Features

*To be documented upon implementation*

### Planned Capabilities

- Content-based routing
- Multi-provider routing (OpenAI, Anthropic, etc.)
- Quality-based path selection
- Cost optimization routing
- Fallback and retry logic
- Load balancing
- Route analytics and monitoring
- Dynamic routing rule updates

## Architecture

*Architecture details will be added during implementation*

### Planned Module Structure

```
src/router/  (tentative)
  ├── __init__.py
  ├── router.py
  ├── strategies/
  │   ├── __init__.py
  │   ├── content_based.py
  │   ├── quality_based.py
  │   └── cost_optimized.py
  ├── analyzers/
  │   └── chunk_analyzer.py
  └── models/
      └── routing_decision.py
```

## Routing Strategies

*Detailed routing strategies will be defined during implementation*

### Planned Routing Dimensions

#### 1. Content-Based Routing

Route based on content characteristics:
- **Simple text** → Fast, cost-effective model
- **Complex tables** → Structured output capable model
- **Legal language** → High-accuracy model
- **Mixed content** → Multi-modal capable model

#### 2. Quality-Based Routing

Route based on quality requirements:
- **High confidence needed** → Premium model (GPT-4, Claude Opus)
- **Standard quality** → Balanced model (GPT-4o-mini, Claude Sonnet)
- **Batch processing** → Cost-optimized model

#### 3. Provider-Based Routing

Distribute across LLM providers:
- **Primary provider** → Default routing
- **Fallback provider** → On failure or rate limiting
- **A/B testing** → Split traffic for comparison
- **Load balancing** → Distribute to available providers

#### 4. Pipeline-Based Routing

Route to specialized pipelines:
- **Rule extraction** → RuleAgent pipeline
- **GRC components** → GRC extraction pipeline
- **Table extraction** → Table-specific pipeline
- **Custom formats** → Specialized processors

## Usage

*Usage examples will be provided once the component is implemented*

### Placeholder API

```python
# Tentative API design (subject to change)
from src.router import Router, RoutingStrategy

router = Router(
    strategies=[
        RoutingStrategy.QUALITY_BASED,
        RoutingStrategy.COST_OPTIMIZED
    ]
)

routing_decision = router.route(chunk)
result = routing_decision.processor.process(chunk)
```

### Example Routing Decision

```python
# Chunk analysis
chunk_complexity = router.analyze_complexity(chunk)

if chunk_complexity == "high":
    # Route to premium model
    processor = GPT4Processor()
elif chunk_complexity == "medium":
    # Route to balanced model
    processor = ClaudeSonnetProcessor()
else:
    # Route to cost-effective model
    processor = GPT4oMiniProcessor()

result = processor.process(chunk)
```

## Configuration

*Configuration options will be documented during development*

### Expected Configuration Parameters

```yaml
router:
  default_strategy: quality_based
  
  providers:
    - name: openai
      models: [gpt-4, gpt-4o-mini]
      priority: 1
    - name: anthropic
      models: [claude-opus, claude-sonnet]
      priority: 2
  
  routing_rules:
    - condition: complexity > 0.8
      route_to: gpt-4
    - condition: has_tables == true
      route_to: claude-opus
    - condition: confidence_required > 0.95
      route_to: gpt-4
    - condition: default
      route_to: gpt-4o-mini
  
  fallback:
    enabled: true
    max_retries: 3
    fallback_sequence: [claude-sonnet, gpt-4o-mini]
  
  cost_limits:
    max_cost_per_document: 0.50
    preferred_cost_per_chunk: 0.01
```

## Output Format

*Output format specifications will be defined during implementation*

### Expected Routing Decision Structure

```python
# Tentative structure
{
    "routing_id": "ROUTE_20260213_001",
    "chunk_id": "chunk_0042",
    "decision": {
        "selected_processor": "gpt-4",
        "selected_provider": "openai",
        "strategy": "quality_based",
        "confidence": 0.92
    },
    "analysis": {
        "complexity_score": 0.85,
        "content_type": "table",
        "estimated_cost": 0.02,
        "estimated_time_ms": 1500
    },
    "fallback_chain": ["claude-opus", "gpt-4o-mini"],
    "metadata": {}
}
```

## Integration Points

### Input

Receives chunks from:
- **[Parse and Chunk Component](Phase1-Parse-and-Chunk.md)**
- **[Schema Discovery Agent](Phase1-Schema-Discovery-Agent.md)**

### Output

Routes to:
- Existing extraction pipelines (RuleAgent)
- Multiple LLM providers
- Specialized processors
- **[Eval Component](Phase1-Eval.md)** (for routing performance analysis)

## Routing Analytics

*Analytics capabilities will be defined during implementation*

### Planned Analytics Features

- Route performance tracking
- Cost analysis per route
- Success rate by routing decision
- Bottleneck identification
- Provider comparison metrics

## Benefits of Routing

### Why Route?

1. **Cost Optimization**: Use expensive models only when necessary
2. **Quality Assurance**: Route high-stakes content to best models
3. **Performance**: Balance speed vs. quality requirements
4. **Reliability**: Automatic fallback on failures
5. **Scalability**: Distribute load across providers
6. **Flexibility**: Easy to add new providers or strategies

## Development Status

**Current Status**: Not yet implemented

**Planned Timeline**: TBD

**Dependencies**: 
- Parse and Chunk component (✅ Complete)
- Multiple extraction pipelines

## Testing Strategy

The Router component will be tested with:
- Diverse chunk types and complexities
- Provider availability simulation
- Cost and performance benchmarking
- Fallback scenario testing
- Load testing with concurrent routes

## Next Steps

This page will be updated with detailed documentation once the Router component is implemented.

## Related Documentation

- [Architecture Overview](Architecture.md)
- [Configuration Guide](Configuration.md)
- [Parse and Chunk Component](Phase1-Parse-and-Chunk.md)
- [Development Guide](Development-Guide.md)

---

**Questions or Feedback?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) to discuss the Router component design.
