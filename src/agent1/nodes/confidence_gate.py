from __future__ import annotations

import yaml
from pathlib import Path
import structlog

from agent1.models.state import Phase1State

logger = structlog.get_logger(__name__)

CONFIG_FILE = Path(__file__).parent.parent / "config" / "gate_config.yaml"


def load_gate_config() -> dict:
    """Load confidence thresholds from config."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    return {
        "thresholds": {
            "default": {
                "auto_accept": 0.85,
                "human_review": 0.50,
            }
        }
    }


def check_confidence(state: Phase1State) -> str:
    """LangGraph conditional edge: routes based on schema confidence."""
    schema_map = state.get("schema_map")
    if schema_map is None:
        logger.warning("confidence_gate_no_schema")
        return "reject"

    avg_conf = schema_map.avg_confidence
    doc_format = schema_map.document_format

    config = load_gate_config()
    thresholds = config.get("thresholds", {}).get(
        doc_format, config.get("thresholds", {}).get("default", {})
    )

    auto_accept = thresholds.get("auto_accept", 0.85)
    human_review = thresholds.get("human_review", 0.50)

    if avg_conf >= auto_accept:
        logger.info("confidence_gate_accept", avg_confidence=avg_conf)
        return "accept"
    elif avg_conf >= human_review:
        logger.info("confidence_gate_review", avg_confidence=avg_conf)
        return "human_review"
    else:
        logger.info("confidence_gate_reject", avg_confidence=avg_conf)
        return "reject"
