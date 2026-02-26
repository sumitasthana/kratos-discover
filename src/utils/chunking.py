from __future__ import annotations

import hashlib
import re


def normalize_text(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip("\n")


def generate_chunk_id(file_path: str, position: int, content: str) -> str:
    raw = f"{file_path}:{position}:{content[:200]}"
    return f"chunk-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def chunk_prose_blocks(
    blocks: list[str],
    max_chunk_chars: int,
) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for b in blocks:
        add_len = len(b) + (2 if buf else 0)
        if buf and buf_len + add_len > max_chunk_chars:
            chunks.append("\n\n".join(buf))
            buf = [b]
            buf_len = len(b)
            continue
        buf.append(b)
        buf_len += add_len

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def table_to_text(table_data: list[list[str]]) -> str:
    return "\n".join(["\t".join(row) for row in table_data])


def _is_control_table(table_data: list[list[str]]) -> bool:
    """Detect if table is a control table (has Control ID column)."""
    if not table_data or len(table_data[0]) < 1:
        return False
    
    header_lower = [cell.lower().strip() for cell in table_data[0]]
    return any("control id" in cell or "control code" in cell for cell in header_lower)


def split_table_by_rows(
    table_data: list[list[str]],
    max_chunk_chars: int,
) -> list[tuple[list[list[str]], int, int]]:
    """Split table by rows, keeping control records together.
    
    For control tables (with Control ID column), ensures each control record
    (header + one data row) stays in the same chunk to preserve control_id
    co-location with control description.
    """
    if not table_data:
        return []

    header = table_data[0]
    body = table_data[1:]
    out: list[tuple[list[list[str]], int, int]] = []
    
    # Issue 2: For control tables, enforce minimum chunk size of header + 1 row
    is_control = _is_control_table(table_data)
    min_rows = 2 if is_control else 2  # Always keep header + at least 1 data row

    start = 1
    current: list[list[str]] = [header]
    current_chars = len(table_to_text(current))

    for i, row in enumerate(body, start=1):
        candidate = current + [row]
        cand_chars = len(table_to_text(candidate))
        
        # For control tables: only split if we have at least header + 1 row AND exceeds size
        # This ensures each control record has its ID
        if is_control:
            if len(current) >= min_rows and cand_chars > max_chunk_chars:
                end = start + (len(current) - 2)
                out.append((current, start, end))
                current = [header, row]
                current_chars = len(table_to_text(current))
                start = i
                continue
        else:
            # Original logic for non-control tables
            if len(current) > 1 and cand_chars > max_chunk_chars:
                end = start + (len(current) - 2)
                out.append((current, start, end))
                current = [header, row]
                current_chars = len(table_to_text(current))
                start = i
                continue

        current = candidate
        current_chars = cand_chars

    if len(current) >= 1:
        end = start + max(0, len(current) - 2)
        out.append((current, start, end))

    return out
