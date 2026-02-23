from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Literal

from models.chunks import ContentChunk, PreprocessorOutput
from models.schema_map import SchemaMap

if TYPE_CHECKING:
    from models.requirements import RegulatoryRequirement, ExtractionMetadata
    from models.grc_components import GRCComponentsResponse


class Phase1State(TypedDict, total=False):
    """State object passed through the LangGraph pipeline."""
    file_path: str
    preprocessor_output: PreprocessorOutput | None
    chunks: list[ContentChunk]
    schema_map: SchemaMap | None
    gate_decision: Literal["accept", "human_review", "reject"] | None
    human_corrections: SchemaMap | None
    requirements: list["RegulatoryRequirement"]
    extraction_metadata: "ExtractionMetadata | None"
    quality_report: dict | None
    eval_report: dict | None  # Output from Eval node
    prompt_versions: dict[str, str]
    extraction_iteration: int
    errors: list[str]
    grc_components: "GRCComponentsResponse | None"
    component_index: dict[str, str] | None  # maps source_chunk_id → component_id
