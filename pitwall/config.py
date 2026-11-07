"""Project-wide settings."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("PITWALL_DATA_DIR", ROOT / "data"))
SQL_DIR = ROOT / "sql"

JOLPICA_BASE = os.getenv("JOLPICA_BASE", "https://api.jolpi.ca/ergast/f1")
OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1")

# First season of the history tables (start of the turbo-hybrid era).
HISTORY_START = int(os.getenv("PITWALL_HISTORY_START", "2014"))

# Seconds of lap time gained per lap as fuel burns off. A common rule of thumb;
# used to fuel-correct lap times before estimating tyre degradation.
FUEL_CORRECTION_S_PER_LAP = float(os.getenv("PITWALL_FUEL_CORRECTION", "0.035"))

# Points available per race and per sprint for the winner (title-math calculations).
MAX_RACE_POINTS = 25
MAX_SPRINT_POINTS = 8


def current_season() -> int:
    return int(os.getenv("PITWALL_SEASON", datetime.now(timezone.utc).year))
