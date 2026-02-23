from __future__ import annotations

from pathlib import Path

import structlog
from docx import Document

from exceptions import EmptyDocumentError, FileParseError
from models.chunks import PreprocessorOutput
from parsers.docx_parser import parse_docx_to_chunks
from utils.chunking import generate_chunk_id

logger = structlog.get_logger(__name__)


def parse_and_chunk(
    file_path: Path,
    file_type: str | None = None,
    max_chunk_chars: int = 3000,
    min_chunk_chars: int = 50,
) -> PreprocessorOutput:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    resolved_type = (file_type or file_path.suffix.lstrip(".")).lower()

    logger.info("parse_started", file_path=str(file_path), file_type=resolved_type)

    try:
        if resolved_type == "docx":
            doc = Document(str(file_path))
            chunks, stats = parse_docx_to_chunks(
                doc=doc,
                file_path=str(file_path),
                max_chunk_chars=max_chunk_chars,
                min_chunk_chars=min_chunk_chars,
            )
        else:
            raise ValueError(
                f"Unsupported file type: {resolved_type}. Supported: .docx"
            )
    except EmptyDocumentError:
        raise
    except ValueError:
        raise
    except NotImplementedError:
        raise
    except Exception as e:
        logger.error("parse_failed", file_path=str(file_path), error=str(e))
        raise FileParseError(f"Failed to parse: {file_path}") from e

    if not chunks:
        raise EmptyDocumentError(f"File parsed but produced 0 chunks: {file_path}")

    for pos, chunk in enumerate(chunks):
        chunk.chunk_id = generate_chunk_id(str(file_path), pos, chunk.content_text)

    out = PreprocessorOutput(
        file_path=str(file_path),
        file_type=resolved_type,
        total_chunks=len(chunks),
        chunks=chunks,
        document_stats=stats,
    )

    logger.info(
        "parse_completed",
        total_chunks=len(chunks),
        total_chars=int(stats.get("total_chars", 0)),
    )
    return out
