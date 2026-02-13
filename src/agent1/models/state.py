from __future__ import annotations

from typing import TypedDict, Literal
from agent1.models.chunks import ContentChunk, PreprocessorOutput
from agent1.models.schema_map import SchemaMap


class Phase1State(TypedDict, total=False):
    file_path: str
    preprocessor_output: PreprocessorOutput | None
    chunks: list[ContentChunk]
    schema_map: SchemaMap | None
    gate_decision: Literal["accept", "human_review", "reject"] | None
    human_corrections: SchemaMap | None
    requirements: list
    quality_report: dict | None
    prompt_versions: dict[str, str]
    extraction_iteration: int
    errors: list[str]
