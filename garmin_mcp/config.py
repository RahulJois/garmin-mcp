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


# ---------------------------------------------------------------------------
# Garmin Connect credentials & tokens
# ---------------------------------------------------------------------------

GARMIN_CONNECT_CONFIG = Path.home() / ".GarminDb" / "GarminConnectConfig.json"
GARMIN_TOKEN_DIR = str(Path.home() / ".garth")


def get_garmin_credentials() -> tuple[str | None, str | None]:
    """Return (email, password) for Garmin Connect authentication.

    Resolution order:
      1. ``~/.GarminDb/GarminConnectConfig.json``  (credentials.user / .password)
         – also honours the ``password_file`` field when ``password`` is empty.
      2. ``GARMIN_EMAIL`` / ``GARMIN_PASSWORD`` environment variables.
    """
    # --- Try config file first ---
    try:
        data = json.loads(GARMIN_CONNECT_CONFIG.read_text())
        creds = data.get("credentials", {})
        user = (creds.get("user") or "").strip() or None
        password = (creds.get("password") or "").strip() or None

        # Support password_file when password is empty
        if not password:
            pw_file = creds.get("password_file")
            if pw_file:
                password = Path(pw_file).expanduser().read_text().strip() or None

        if user:
            return user, password
    except Exception:
        pass

    # --- Fallback to env vars ---
    email = os.environ.get("GARMIN_EMAIL", "").strip() or None
    password = os.environ.get("GARMIN_PASSWORD", "").strip() or None
    return email, password
