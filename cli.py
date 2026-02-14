from __future__ import annotations

import sys
from pathlib import Path

# Add src to path so we can import from it
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
