"""Configuration loader for Kratos Discover Agent pipeline.

Provides centralized access to all pipeline configuration parameters.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)

CONFIG_FILE = Path(__file__).parent / "pipeline_config.yaml"


class ConfigLoader:
    """Loads and provides access to pipeline configuration."""
    
    _instance: Optional[ConfigLoader] = None
    _config: Optional[dict[str, Any]] = None
    
    def __new__(cls) -> ConfigLoader:
        """Singleton pattern - ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize config loader (only runs once due to singleton)."""
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                self._config = yaml.safe_load(f)
            logger.info("config_loaded", path=str(CONFIG_FILE))
        else:
            logger.warning("config_file_not_found", path=str(CONFIG_FILE))
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.
        
        Examples:
            config.get("llm.model")
            config.get("atomizer.batch_processing.max_batch_chars")
            config.get("nonexistent.key", default=100)
        """
        if not self._config:
            return default
        
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> dict[str, Any]:
        """Get entire configuration section.
        
        Examples:
            config.get_section("llm")
            config.get_section("atomizer")
        """
        return self.get(section, default={})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._config = None
        self._load_config()


# Singleton instance
_config = ConfigLoader()


def get_config() -> ConfigLoader:
    """Get the global config instance."""
    return _config


# Convenience functions for common config access
def get_llm_model() -> str:
    """Get LLM model name."""
    return _config.get("llm.model", "claude-sonnet-4-20250514")


def get_llm_max_tokens() -> int:
    """Get LLM max tokens."""
    return _config.get("llm.max_tokens", 4096)


def get_llm_temperature(retry: bool = False) -> float:
    """Get LLM temperature."""
    key = "llm.temperature_retry" if retry else "llm.temperature"
    return _config.get(key, 0.1 if retry else 0.0)


def get_atomizer_config() -> dict[str, Any]:
    """Get atomizer configuration section."""
    return _config.get_section("atomizer")


def get_batch_config() -> dict[str, Any]:
    """Get batch processing configuration."""
    return _config.get("atomizer.batch_processing", default={})


def get_confidence_thresholds(iteration: int = 1) -> float:
    """Get confidence threshold for extraction iteration.
    
    Args:
        iteration: Extraction iteration (1 or 2)
    
    Returns:
        Confidence threshold value
    """
    key = "atomizer.confidence_thresholds.pass2" if iteration == 2 else "atomizer.confidence_thresholds.pass1"
    return _config.get(key, 0.70 if iteration == 2 else 0.60)


def get_fragment_pronouns() -> list[str]:
    """Get list of fragment detection pronouns."""
    return _config.get("atomizer.fragment_detection.pronouns", default=[])


def get_insights_config() -> dict[str, Any]:
    """Get insights generator configuration."""
    return _config.get_section("insights")


def get_gate_thresholds(doc_format: str = "default") -> dict[str, float]:
    """Get confidence gate thresholds for document format.
    
    Args:
        doc_format: Document format (grc_export, regulatory_docx, data_dictionary, default)
    
    Returns:
        Dictionary with auto_accept, human_review, min_schema_compliance, min_coverage
    """
    thresholds = _config.get(f"confidence_gate.thresholds.{doc_format}")
    if thresholds is None:
        thresholds = _config.get("confidence_gate.thresholds.default", default={})
    return thresholds


def get_schema_discovery_config() -> dict[str, Any]:
    """Get schema discovery configuration."""
    return _config.get_section("schema_discovery")


def get_deduplication_threshold() -> float:
    """Get Jaccard similarity threshold for deduplication."""
    return _config.get("deduplication.jaccard_similarity_threshold", 0.75)


def get_confidence_scoring_weights() -> dict[str, float]:
    """Get confidence scoring feature weights."""
    return _config.get("confidence_scoring.feature_weights", default={})


def get_confidence_ceiling_for_inference() -> float:
    """Get confidence ceiling for INFERENCE grounded requirements."""
    return _config.get("confidence_scoring.confidence_bounds.ceiling_for_inference", 0.70)
