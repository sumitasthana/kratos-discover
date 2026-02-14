from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to path immediately on import - MUST be before any other imports
_src_dir = Path(__file__).resolve().parents[1] / "src"
_src_str = str(_src_dir)
if _src_str not in sys.path:
    sys.path.insert(0, _src_str)

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Ensure src directory is on sys.path so tests can import modules."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


# Also hook into collection to ensure path is set
def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """Ensure path is set during collection."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
