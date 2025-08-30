from __future__ import annotations

# Ensure the project root (containing logseq_to_obsidian.py) is importable
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
