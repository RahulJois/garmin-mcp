"""Configuration: DB paths and server settings."""

import json
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Database paths
# ---------------------------------------------------------------------------

DB_DIR = Path.home() / "HealthData" / "DBs"

GARMIN_DB      = str(DB_DIR / "garmin.db")
ACTIVITIES_DB  = str(DB_DIR / "garmin_activities.db")
MONITORING_DB  = str(DB_DIR / "garmin_monitoring.db")
SUMMARY_DB     = str(DB_DIR / "garmin_summary.db")


# ---------------------------------------------------------------------------
# Query settings
# ---------------------------------------------------------------------------

# Max rows returned per query to cap response size
try:
    MAX_ROWS = int(os.environ.get("MAX_ROWS", "5000"))
except ValueError:
    raise ValueError("MAX_ROWS must be a valid integer")

if MAX_ROWS <= 0:
    raise ValueError("MAX_ROWS must be a positive integer")


# ---------------------------------------------------------------------------
# Unit system
# ---------------------------------------------------------------------------

# Resolved from ~/HealthData/FitFiles/user-settings.json (userData.measurementSystem).
# Any non-"metric" value (e.g. "statute", "statute_us") is treated as imperial.
# Override by setting the GARMIN_UNITS env var to "metric" or "imperial".

_USER_SETTINGS = Path.home() / "HealthData" / "FitFiles" / "user-settings.json"

def _resolve_units() -> str:
    env = os.environ.get("GARMIN_UNITS", "").strip().lower()
    if env in ("metric", "imperial"):
        return env
    try:
        data = json.loads(_USER_SETTINGS.read_text())
        measurement_system = data["userData"]["measurementSystem"]
        return "metric" if measurement_system == "metric" else "imperial"  # statute_us / statute_uk → imperial
    except Exception:
        return "metric"

UNITS = _resolve_units()
