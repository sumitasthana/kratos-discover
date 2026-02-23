"""Requirement Atomizer package - Node 4 in the LangGraph pipeline.

This package extracts RegulatoryRequirement[] from ContentChunk[]
using a resolved SchemaMap for field guidance.

Modules:
- node: Main RequirementAtomizerNode orchestration
- batch_processor: LLM batch processing with retries
- response_parser: JSON parsing and requirement construction
- schema_repair: Auto-repair of schema violations
- prompt_builder: System prompt and context building
"""
from nodes.atomizer.node import (
    RequirementAtomizerNode,
    requirement_atomizer_agent,
    AtomizerFailure,
)

__all__ = [
    "RequirementAtomizerNode",
    "requirement_atomizer_agent",
    "AtomizerFailure",
]
