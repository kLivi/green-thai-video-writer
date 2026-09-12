"""Test path setup.

The citation modules (citations.py, verify_citations.py, citation_gate.py) are
shared by all three GET pipelines and live at ../../shared/, not in this repo's
scripts/. Put that directory on sys.path so tests import them the same way the
runtime scripts do (`from citations import ...`), rather than through a
repo-local `scripts.` package path that no longer exists.
"""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
