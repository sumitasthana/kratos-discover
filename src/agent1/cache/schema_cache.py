from __future__ import annotations

import json
from pathlib import Path
import structlog

from agent1.models.schema_map import SchemaMap

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "cache" / "schemas"


def get_cached_schema(source_tool: str) -> SchemaMap | None:
    """Retrieve cached schema by source tool name."""
    cache_file = CACHE_DIR / f"{source_tool.lower()}.json"
    if cache_file.exists():
        try:
            return SchemaMap.model_validate_json(cache_file.read_text())
        except Exception as e:
            logger.warning("cache_read_failed", source_tool=source_tool, error=str(e))
            return None
    return None


def cache_schema(source_tool: str, schema_map: SchemaMap) -> None:
    """Store schema in cache for reuse."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{source_tool.lower()}.json"
        cache_file.write_text(schema_map.model_dump_json(indent=2))
        logger.info("schema_cached", source_tool=source_tool, cache_file=str(cache_file))
    except Exception as e:
        logger.warning("cache_write_failed", source_tool=source_tool, error=str(e))
