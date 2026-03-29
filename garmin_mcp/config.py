"""Configuration: DB paths and environment settings.

All critical configuration is validated on module import. Missing required
environment variables will raise an error at startup.
"""

import os
import sys
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
# LLM Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Max rows returned per query to cap LLM context size
try:
    MAX_ROWS = int(os.environ.get("MAX_ROWS", "5000"))
except ValueError:
    raise ValueError("MAX_ROWS must be a valid integer")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config() -> None:
    """Validate that all required configuration is present.
    
    Raises:
        ValueError: If required environment variables are not set or invalid.
    """
    missing = []
    
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    
    if MAX_ROWS <= 0:
        raise ValueError("MAX_ROWS must be a positive integer")
    
    if missing:
        error_msg = (
            f"Missing required environment variable(s): {', '.join(missing)}\n"
            "Please set these before running the MCP server."
        )
        print(f"[ERROR] {error_msg}", file=sys.stderr)
        raise ValueError(error_msg)


# Run validation on import
validate_config()
