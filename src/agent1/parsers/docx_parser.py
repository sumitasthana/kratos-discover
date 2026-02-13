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
_ENTITY_HEADING_RE = re.compile(r"^([PRC])-(\d{3})\b", re.IGNORECASE)
_STUB_RE = re.compile(r"full\s+control\s+details\s+documented\s+in\s+rsa\s+archer", re.IGNORECASE)


def _extract_entity_from_heading(heading: str) -> tuple[str, str] | None:
    match = _ENTITY_HEADING_RE.match(heading)
    if not match:
        return None
    prefix = match.group(1).upper()
    entity_id = f"{prefix}-{match.group(2)}"
    record_type_map = {"P": "policy", "R": "risk", "C": "control"}
    record_type = record_type_map.get(prefix, "unknown")
    return (record_type, entity_id)


def _extract_entity_from_table_first_row(table_data: list[list[str]]) -> tuple[str, str] | None:
    if len(table_data) < 1:
        return None
    first_row = table_data[0]
    if len(first_row) < 2:
        return None
    key = (first_row[0] or "").strip().lower()
    val = (first_row[1] or "").strip()
    if not val:
        return None
    if key == "policy id" and val.startswith("P-"):
        return ("policy", val)
    if key == "risk id" and val.startswith("R-"):
        return ("risk", val)
    if key == "control id" and val.startswith("C-"):
        return ("control", val)
    return None


def _get_base_annotations_from_table(table_data: list[list[str]]) -> dict:
    annotations: dict = {}
    entity = _extract_entity_from_table_first_row(table_data)
    if entity:
        record_type, entity_id = entity
        annotations["record_type"] = record_type
        annotations["record_id"] = entity_id
    return annotations


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


def _looks_like_kv_entity_table(table_data: list[list[str]]) -> bool:
    if len(table_data) < 2:
        return False

    # Vertical key-value table: 2 columns, first row is entity identifier or header-like row.
    # FDIC 370 policy/control records frequently use a 2-col layout.
    col_count = max((len(r) for r in table_data), default=0)
    if col_count != 2:
        return False

    first_k = (table_data[0][0] or "").strip()
    first_v = (table_data[0][1] or "").strip()
    if not first_k or not first_v:
        return False

    # Prefer: explicit ID row (e.g., "Policy ID" | "P-001", "Control ID" | "C-001").
    key_lower = first_k.lower()
    if key_lower.endswith(" id"):
        return True

    # Or common header row pattern for 2-col kv tables.
    if first_k.lower() in {"field", "attribute", "name"} and first_v.lower() in {"value", "values"}:
        return True

    return False


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
    pending_heading: str | None = None

    def _base_annotations() -> dict:
        annotations: dict = {}
        if pending_heading:
            entity = _extract_entity_from_heading(pending_heading)
            if entity:
                record_type, entity_id = entity
                annotations["record_type"] = record_type
                annotations["record_id"] = entity_id
        return annotations

    def flush_prose(source_location: str) -> None:
        nonlocal prose_buf
        nonlocal pending_heading
        if not prose_buf:
            return

        prose_chunks = chunk_prose_blocks(prose_buf, max_chunk_chars=max_chunk_chars)
        for pc in prose_chunks:
            txt = normalize_text(pc)
            if len(txt) < min_chunk_chars:
                stats["empty_chunks_skipped"] += 1
                logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="prose")
                continue

            annotations = _base_annotations()
            # Stub/incomplete controls: appear as heading + one-line prose with Archer reference.
            if pending_heading and _ENTITY_HEADING_RE.match(pending_heading) and _STUB_RE.search(txt):
                annotations["incomplete_record"] = True
                annotations["incomplete_reason"] = "stub_control_reference_only"

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
                    annotations=annotations,
                )
            )
            stats["prose_sections"] += 1
            stats["total_chars"] += len(txt)

        prose_buf = []
        if pending_heading:
            pending_heading = None

    def flush_list(source_location: str) -> None:
        nonlocal list_buf
        nonlocal pending_heading
        if not list_buf:
            return

        txt = normalize_text("\n".join(list_buf))
        if len(txt) < min_chunk_chars:
            stats["empty_chunks_skipped"] += 1
            logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="list")
            list_buf = []
            return

        annotations = _base_annotations()
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
                annotations=annotations,
            )
        )
        stats["list_sections"] += 1
        stats["total_chars"] += len(txt)
        list_buf = []
        if pending_heading:
            pending_heading = None

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
                    pending_heading = text
                    stats["heading_count"] += 1
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

            table_number = stats["table_count"] + 1

            # For vertical KV entity tables (common in FDIC 370), do not split mid-entity.
            if _looks_like_kv_entity_table(table_data):
                t_txt = normalize_text(table_to_text(table_data))
                if len(t_txt) >= min_chunk_chars:
                    annotations = _get_base_annotations_from_table(table_data)
                    chunks.append(
                        ContentChunk(
                            chunk_id="",
                            chunk_type="table",
                            content_text=t_txt,
                            table_data=table_data,
                            row_count=len(table_data),
                            col_count=2,
                            source_location=f"table {table_number}:rows 1-{max(1, len(table_data) - 1)}",
                            parent_heading=current_heading,
                            char_count=len(t_txt),
                            annotations=annotations,
                        )
                    )
                    stats["total_chars"] += len(t_txt)
                else:
                    stats["empty_chunks_skipped"] += 1
                    logger.warning("empty_chunk_skipped", reason="below_min_chunk_chars", chunk_type="table")
            else:
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
                    annotations = _get_base_annotations_from_table(table_data)
                    chunks.append(
                        ContentChunk(
                            chunk_id="",
                            chunk_type="table",
                            content_text=t_txt,
                            table_data=sub_table,
                            row_count=row_count,
                            col_count=col_count,
                            source_location=f"table {table_number}:rows {start_row}-{end_row}",
                            parent_heading=current_heading,
                            char_count=len(t_txt),
                            annotations=annotations,
                        )
                    )
                    stats["total_chars"] += len(t_txt)

            stats["table_count"] += 1
            if pending_heading:
                pending_heading = None

        except Exception as e:
            logger.warning("chunk_parse_failed", block_index=block_idx, error=str(e))
            stats["empty_chunks_skipped"] += 1
            continue

    flush_prose(source_location=f"block {block_idx}")
    flush_list(source_location=f"block {block_idx}")

    return chunks, stats
