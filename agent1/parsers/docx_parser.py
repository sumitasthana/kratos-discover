from __future__ import annotations

import re
from typing import Iterable, Iterator, Union

import structlog
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from agent1.models.chunks import ContentChunk
from agent1.utils.chunking import (
    chunk_prose_blocks,
    normalize_text,
    split_table_by_rows,
    table_to_text,
)

logger = structlog.get_logger(__name__)


_PAGE_OF_RE = re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE)


def _iter_block_items(doc: DocxDocument) -> Iterator[Union[Paragraph, Table]]:
    parent_elm = doc.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def _is_toc(par: Paragraph) -> bool:
    try:
        style = par.style
    except Exception:
        return False

    if not style:
        return False

    name = (style.name or "").lower()
    return "toc" in name


def _is_heading(par: Paragraph) -> bool:
    try:
        style = par.style
    except Exception:
        return False

    if not style:
        return False

    name = (style.name or "")
    return name.lower().startswith("heading")


def _is_list_item(par: Paragraph) -> bool:
    try:
        style = par.style
    except Exception:
        style = None

    if style and style.name and "list" in style.name.lower():
        return True

    # Fallback: detect numbering properties.
    try:
        ppr = par._p.pPr  # type: ignore[attr-defined]
        return ppr is not None and ppr.numPr is not None
    except Exception:
        return False


def _clean_paragraph_text(text: str) -> str:
    text = normalize_text(text)
    if not text:
        return ""
    if _PAGE_OF_RE.match(text):
        return ""
    return text


def _extract_table_data(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        row_cells: list[str] = []
        for cell in row.cells:
            cell_text = normalize_text(cell.text or "")
            row_cells.append(cell_text)

        # Skip entirely empty rows.
        if any(c.strip() for c in row_cells):
            rows.append(row_cells)

    return rows


def parse_docx_to_chunks(
    *,
    doc: DocxDocument,
    file_path: str,
    max_chunk_chars: int,
    min_chunk_chars: int,
) -> tuple[list[ContentChunk], dict]:
    chunks: list[ContentChunk] = []
    stats = {
        "table_count": 0,
        "prose_sections": 0,
        "heading_count": 0,
        "list_sections": 0,
        "total_chars": 0,
        "empty_chunks_skipped": 0,
    }

    current_heading: str | None = None
    prose_buf: list[str] = []
    list_buf: list[str] = []

    def flush_prose(source_location: str) -> None:
        nonlocal prose_buf
        if not prose_buf:
            return

        prose_chunks = chunk_prose_blocks(prose_buf, max_chunk_chars=max_chunk_chars)
        for pc in prose_chunks:
            txt = normalize_text(pc)
            if len(txt) < min_chunk_chars:
                stats["empty_chunks_skipped"] += 1
                logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="prose")
                continue

            chunks.append(
                ContentChunk(
                    chunk_id="",
                    chunk_type="prose",
                    content_text=txt,
                    table_data=None,
                    row_count=None,
                    col_count=None,
                    source_location=source_location,
                    parent_heading=current_heading,
                    char_count=len(txt),
                )
            )
            stats["prose_sections"] += 1
            stats["total_chars"] += len(txt)

        prose_buf = []

    def flush_list(source_location: str) -> None:
        nonlocal list_buf
        if not list_buf:
            return

        txt = normalize_text("\n".join(list_buf))
        if len(txt) < min_chunk_chars:
            stats["empty_chunks_skipped"] += 1
            logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="list")
            list_buf = []
            return

        chunks.append(
            ContentChunk(
                chunk_id="",
                chunk_type="list",
                content_text=txt,
                table_data=None,
                row_count=None,
                col_count=None,
                source_location=source_location,
                parent_heading=current_heading,
                char_count=len(txt),
            )
        )
        stats["list_sections"] += 1
        stats["total_chars"] += len(txt)
        list_buf = []

    block_idx = 0

    for block in _iter_block_items(doc):
        block_idx += 1
        try:
            if isinstance(block, Paragraph):
                # Switching between paragraph/table flushes buffers.
                text = _clean_paragraph_text(block.text or "")
                if not text or _is_toc(block):
                    continue

                if _is_heading(block):
                    flush_prose(source_location=f"block {block_idx}")
                    flush_list(source_location=f"block {block_idx}")

                    current_heading = text
                    chunks.append(
                        ContentChunk(
                            chunk_id="",
                            chunk_type="heading",
                            content_text=text,
                            table_data=None,
                            row_count=None,
                            col_count=None,
                            source_location=f"block {block_idx}",
                            parent_heading=None,
                            char_count=len(text),
                        )
                    )
                    stats["heading_count"] += 1
                    stats["total_chars"] += len(text)
                    continue

                if _is_list_item(block):
                    flush_prose(source_location=f"block {block_idx}")
                    list_buf.append(text)
                    continue

                # Regular prose
                flush_list(source_location=f"block {block_idx}")
                prose_buf.append(text)
                continue

            # Table
            flush_prose(source_location=f"block {block_idx}")
            flush_list(source_location=f"block {block_idx}")

            table_data = _extract_table_data(block)
            if not table_data:
                continue

            # Split if needed
            for split_idx, (sub_table, start_row, end_row) in enumerate(
                split_table_by_rows(table_data, max_chunk_chars=max_chunk_chars), start=1
            ):
                t_txt = normalize_text(table_to_text(sub_table))
                if len(t_txt) < min_chunk_chars:
                    stats["empty_chunks_skipped"] += 1
                    logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="table")
                    continue

                row_count = len(sub_table)
                col_count = max((len(r) for r in sub_table), default=0)
                chunks.append(
                    ContentChunk(
                        chunk_id="",
                        chunk_type="table",
                        content_text=t_txt,
                        table_data=sub_table,
                        row_count=row_count,
                        col_count=col_count,
                        source_location=f"table {stats['table_count'] + 1}:rows {start_row}-{end_row}",
                        parent_heading=current_heading,
                        char_count=len(t_txt),
                    )
                )
                stats["total_chars"] += len(t_txt)

            stats["table_count"] += 1

        except Exception as e:
            logger.warning("chunk_parse_failed", block_index=block_idx, error=str(e))
            stats["empty_chunks_skipped"] += 1
            continue

    flush_prose(source_location=f"block {block_idx}")
    flush_list(source_location=f"block {block_idx}")

    return chunks, stats
