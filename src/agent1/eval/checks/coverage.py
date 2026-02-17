"""Coverage analysis for Eval node."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent1.models.chunks import ContentChunk
    from agent1.models.requirements import RegulatoryRequirement


def analyze_coverage(
    chunks: list["ContentChunk"],
    requirements: list["RegulatoryRequirement"],
) -> tuple[int, int, list[str], float]:
    """
    Analyze chunk coverage by extracted requirements.
    
    Returns:
        (total_chunks, chunks_processed, chunks_with_zero, coverage_ratio)
    """
    if not chunks:
        return 0, 0, [], 0.0
    
    chunks_with_zero: list[str] = []
    chunks_with_extractions: set[str] = set()
    
    for req in requirements:
        source_chunk_id = req.metadata.source_chunk_id
        if source_chunk_id:
            chunks_with_extractions.add(source_chunk_id)
    
    for chunk in chunks:
        if chunk.chunk_id not in chunks_with_extractions:
            chunks_with_zero.append(chunk.chunk_id)
    
    coverage_ratio = len(chunks_with_extractions) / len(chunks)
    
    return len(chunks), len(chunks_with_extractions), chunks_with_zero, coverage_ratio
