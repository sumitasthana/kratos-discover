from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class AgentInput(BaseModel):
    file_path: Path
    file_type: Literal["docx", "xlsx", "csv"] | None = None
    institution_name: str | None = None
    source_tool: str | None = None
