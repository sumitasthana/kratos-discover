from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContentChunk(BaseModel):
    chunk_id: str
    chunk_type: Literal["table", "prose", "heading", "list", "mixed"]
    content_text: str
    table_data: list[list[str]] | None = None
    row_count: int | None = None
    col_count: int | None = None
    source_location: str
    parent_heading: str | None = None
    char_count: int = 0

    def model_post_init(self, __context) -> None:
        if not self.char_count:
            self.char_count = len(self.content_text or "")


class PreprocessorOutput(BaseModel):
    file_path: str
    file_type: str
    total_chunks: int
    chunks: list[ContentChunk]
    document_stats: dict = Field(default_factory=dict)
