"""Make the pure-Python modules importable without Home Assistant installed."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "custom_components" / "live_calendar")
)
