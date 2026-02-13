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


def split_table_by_rows(
    table_data: list[list[str]],
    max_chunk_chars: int,
) -> list[tuple[list[list[str]], int, int]]:
    if not table_data:
        return []

    header = table_data[0]
    body = table_data[1:]
    out: list[tuple[list[list[str]], int, int]] = []

    start = 1
    current: list[list[str]] = [header]
    current_chars = len(table_to_text(current))

    for i, row in enumerate(body, start=1):
        candidate = current + [row]
        cand_chars = len(table_to_text(candidate))
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
