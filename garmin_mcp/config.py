"""Configuration: DB paths and environment settings."""

import os
from pathlib import Path

DB_DIR = Path.home() / "HealthData" / "DBs"

GARMIN_DB      = str(DB_DIR / "garmin.db")
ACTIVITIES_DB  = str(DB_DIR / "garmin_activities.db")
MONITORING_DB  = str(DB_DIR / "garmin_monitoring.db")
SUMMARY_DB     = str(DB_DIR / "garmin_summary.db")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"

# Max rows returned per query to cap LLM context size
MAX_ROWS = 500
