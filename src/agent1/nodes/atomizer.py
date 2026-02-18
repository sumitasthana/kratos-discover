"""Requirement Atomizer Agent - Node 4 in the LangGraph pipeline.

DEPRECATED: This module file is maintained for backward compatibility only.
The implementation has been refactored into the atomizer/ package:
- atomizer/node.py - Main orchestration
- atomizer/batch_processor.py - LLM batch processing
- atomizer/response_parser.py - JSON parsing
- atomizer/schema_repair.py - Auto-repair logic
- atomizer/prompt_builder.py - Prompt construction

All imports should work as before - this file re-exports from the new package.
"""
from __future__ import annotations

# Re-export everything from the new package for backward compatibility
from agent1.nodes.atomizer.node import (
    RequirementAtomizerNode,
    requirement_atomizer_agent,
    AtomizerFailure,
    DEFAULT_MODEL,
    BATCH_FAILURE_THRESHOLD,
)
from agent1.nodes.atomizer.batch_processor import (
    MAX_BATCH_CHARS,
    MAX_RETRIES_PER_BATCH,
    RETRY_BACKOFF_BASE,
)
from agent1.nodes.atomizer.prompt_builder import PROMPTS_DIR

__all__ = [
    "RequirementAtomizerNode",
    "requirement_atomizer_agent",
    "AtomizerFailure",
    "DEFAULT_MODEL",
    "BATCH_FAILURE_THRESHOLD",
    "MAX_BATCH_CHARS",
    "MAX_RETRIES_PER_BATCH",
    "RETRY_BACKOFF_BASE",
    "PROMPTS_DIR",
]
