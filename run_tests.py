#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path before importing pytest
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "tests/agent1/test_schema_discovery.py"]))
