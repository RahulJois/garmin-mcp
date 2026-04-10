#!/usr/bin/env bash
# Pull Garmin data using GarminDB and import/analyze the latest activities.
set -euo pipefail

GARMINDB_CMD="${GARMINDB_CMD:-garmindb_cli.py}"

if ! command -v "$GARMINDB_CMD" >/dev/null 2>&1; then
  echo "Error: '$GARMINDB_CMD' is not installed or not on PATH." >&2
  echo "Activate the virtual environment where GarminDB is installed, or install it with:" >&2
  echo "  pip install garmindb" >&2
  exit 1
fi

echo "Running GarminDB sync: $GARMINDB_CMD --all --download --import --analyze --latest"
exec "$GARMINDB_CMD" --all --download --import --analyze --latest "$@"
