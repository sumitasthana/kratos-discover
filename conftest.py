from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to path immediately on import
src_dir = Path(__file__).resolve().parent / "src"
src_str = str(src_dir)
if src_str not in sys.path:
    sys.path.insert(0, src_str)


def pytest_configure() -> None:
    # Ensure src directory is on sys.path so tests can import modules.
    src_dir = Path(__file__).resolve().parent / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
