from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    # Ensure rule-agent/ is on sys.path so tests can import prompt_registry.py and rule_agent.py.
    base_dir = Path(__file__).resolve().parents[1]
    base_str = str(base_dir)
    if base_str not in sys.path:
        sys.path.insert(0, base_str)
