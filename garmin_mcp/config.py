"""Configuration: DB paths and server settings."""

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
    MAX_ROWS = int(os.environ.get("MAX_ROWS", "500"))
except ValueError:
    raise ValueError("MAX_ROWS must be a valid integer")

if MAX_ROWS <= 0:
    raise ValueError("MAX_ROWS must be a positive integer")
