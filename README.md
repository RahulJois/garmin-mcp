# Garmin Health MCP Server

A Model Context Protocol (MCP) server that gives Claude Desktop direct access to your Garmin health data. Claude discovers the schema, writes SQL itself, and executes it — no external LLM API key required.

## Overview

This project implements an MCP server that connects Claude to your Garmin health SQLite databases through three composable tools.

**Architecture:**
- **Schema Discovery**: Claude calls `list_domains` and `get_schema` to learn table/column layouts
- **SQL Generation**: Claude writes the SQL query directly from the schema (no intermediate LLM)
- **Execution**: Claude calls `execute_sql` to run the `SELECT` and receive results
- **Database Layer**: Four SQLite databases containing Garmin health data

## Tools

### `list_domains`
Returns a short description for each of the 10 available health data domains. Call this first to discover what data is available.

```
Input:  (none)
Output: { domain_name: description, ... }
```

### `get_schema`
Returns the full table and column schema for a domain, including the `db` and `attach_dbs` values needed by `execute_sql`.

```
Input:  { "domain": "sleep" }
Output: { "schema": "...", "db": "garmin", "attach_dbs": {} }
```

### `execute_sql`
Executes a `SELECT` statement against the Garmin databases. Only `SELECT` is allowed — any DML or DDL is rejected. Results are capped at `MAX_ROWS` (default 500).

```
Input:  { "db": "garmin", "sql": "SELECT ...", "attach_dbs": { "alias": "db_key" } }
Output: { "row_count": N, "results": [...], "warning"?: "..." }
```

### Supported Domains

| Domain | Description |
|---|---|
| `sleep` | Sleep duration, stages (deep/light/REM), sleep score, SpO2, respiration |
| `heart_rate` | Resting HR, daily min/max, intraday readings (~2-min resolution) |
| `stress` | Stress levels (0-100 scale, ~3-min resolution) and daily averages |
| `body_battery` | Garmin Body Battery: daily max, min, and charged/drained |
| `weight` | Body weight measurements over time (kilograms) |
| `spo2_respiration` | Blood oxygen % and respiration rate (sleep/daily/intraday) |
| `activities` | Workout summaries: distance, pace, calories, HR zones, VO2 max |
| `activity_detail` | Per-lap splits and per-second activity detail |
| `daily_summary` | Daily rollups: steps, calories, floors, intensity minutes |
| `trends` | Aggregated health trends by day/week/month/year |

## Setup

### Prerequisites

- Python 3.10+
- Garmin health SQLite databases (e.g. from [garmindb](https://github.com/tcgoetz/GarminDB))

### Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install project in editable mode
pip install -e .

# Install dev dependencies (for testing)
pip install -e .[dev]
```

### Configuration

#### 1. Set Environment Variables (optional)

```bash
export MAX_ROWS="500"   # optional, defaults to 500
```

#### 2. Configure Claude Desktop

Update `~/.config/Claude/claude_desktop_config.json` (macOS/Linux):

```json
{
  "mcpServers": {
    "garmin-health": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "garmin_mcp.server"]
    }
  }
}
```

#### 3. Database Setup

Ensure your Garmin health databases are in `~/HealthData/DBs/`:

```
~/HealthData/DBs/
├── garmin.db              # Main health data (sleep, HR, stress, weight, body battery)
├── garmin_activities.db   # Workout details
├── garmin_monitoring.db   # Intraday HR, stress, SpO2 monitoring
└── garmin_summary.db      # Daily summaries
```

## Usage

### Pull Garmin Data

Use the included helper script to run GarminDB and sync latest activity data:

```bash
./pull_garmin_data.sh
```

If GarminDB is installed in a virtual environment, activate it first:

```bash
source .venv/bin/activate
./pull_garmin_data.sh
```

You can also pass extra GarminDB options through the script, for example:

```bash
./pull_garmin_data.sh --trace
```

### Example Queries

Once configured, ask Claude naturally:

- "How much did I sleep last week?"
- "What is my resting heart rate trend this year?"
- "How many steps did I average this month?"
- "What was my body battery at the start of each day?"
- "Compare my stress levels weekday vs weekend"
- "Show my top 5 runs by distance"

Claude will call `list_domains`, then `get_schema`, then `execute_sql` automatically.

### Tool Response Format

**`execute_sql`** returns:

```json
{
  "row_count": 2,
  "results": [
    { "day": "2026-03-27", "total_sleep_seconds": 28800 },
    { "day": "2026-03-28", "total_sleep_seconds": 27900 }
  ]
}
```

If results are truncated at `MAX_ROWS`:

```json
{
  "row_count": 500,
  "results": [...],
  "warning": "Results may be truncated at 500 rows. Add a LIMIT or WHERE clause to narrow the query."
}
```

## Testing

### Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=garmin_mcp

# Stop on first failure
python -m pytest tests/ -x
```

### Smoke Test

```bash
python test_server.py
```

Exercises `list_domains`, `get_schema`, and `execute_sql` against each database, with graceful skipping if a DB file doesn't exist locally.

### Test Coverage

Tests verify:
- ✅ `MAX_ROWS` configuration validation
- ✅ Tool count, names, and required input parameters
- ✅ SQL safety validation (`_is_safe` — blocks INSERT, UPDATE, DELETE, DROP, etc.)
- ✅ `list_domains` handler returns all 10 domains
- ✅ `get_schema` handler for valid and unknown domains
- ✅ `execute_sql` handler: SELECT success, WHERE filtering, INSERT rejection, unknown db, empty SQL

## Architecture

### How a Query Works

```
1. Claude calls list_domains
   └─ Server returns { domain: description, ... }

2. Claude calls get_schema(domain)
   └─ Server returns { schema, db, attach_dbs }

3. Claude writes SQL from the schema

4. Claude calls execute_sql(db, sql, attach_dbs?)
   └─ Server validates SQL (SELECT only)
   └─ Opens SQLite, ATTACHes extra DBs if needed
   └─ Executes query, returns up to MAX_ROWS rows
```

### Key Files

| File | Purpose |
|------|---------|
| `garmin_mcp/server.py` | MCP server, tool definitions, `_is_safe`, handlers |
| `garmin_mcp/config.py` | DB paths and `MAX_ROWS` validation |
| `garmin_mcp/schema_context.py` | Schema strings and domain metadata |
| `tests/test_server.py` | Full test suite |
| `tests/conftest.py` | Pytest fixtures (temp SQLite DBs) |
| `tools_playground.ipynb` | Interactive notebook for exploring the 3 tools |
| `test_server.py` | CLI smoke test |

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_ROWS` | No | `500` | Maximum rows returned per `execute_sql` call |

### Database Paths

Configured in `garmin_mcp/config.py`:

```python
DB_DIR = Path.home() / "HealthData" / "DBs"

GARMIN_DB      = str(DB_DIR / "garmin.db")
ACTIVITIES_DB  = str(DB_DIR / "garmin_activities.db")
MONITORING_DB  = str(DB_DIR / "garmin_monitoring.db")
SUMMARY_DB     = str(DB_DIR / "garmin_summary.db")
```

## Error Handling

Errors are returned in the response body rather than raised as exceptions:

| Scenario | Response |
|---|---|
| Unknown domain in `get_schema` | `{ "error": "Unknown domain '...'" }` |
| Non-SELECT SQL in `execute_sql` | `{ "error": "Only SELECT statements are allowed." }` |
| Unknown `db` key | `{ "error": "Unknown db '...'" }` |
| SQLite error | `{ "error": "SQL error: ..." }` |
| Empty `sql` | `{ "error": "'sql' parameter is required." }` |

## Troubleshooting

### "No such file or directory: garmin.db"
Verify databases exist in `~/HealthData/DBs/` and paths in [garmin_mcp/config.py](garmin_mcp/config.py) match.

### "Only SELECT statements are allowed"
The safety check blocks everything except `SELECT`. Make sure the SQL Claude generated starts with `SELECT`.

### Query returns no results
- Verify data exists for the date range queried
- Try a broader `WHERE` clause or remove it entirely
- Check the table name against the schema returned by `get_schema`

### Restart Claude Desktop
After any change to the MCP server config or code, restart Claude Desktop to reload the tool definitions.

## Development

### Adding a New Domain

1. Add an entry to `DOMAINS` in `garmin_mcp/schema_context.py` with `description`, `schema`, `primary_db`, and `attach_dbs`
2. Verify `python -m pytest tests/ -v` still passes (tool count test will need updating)
3. Add a test case in `tests/test_server.py` for the new domain's `get_schema` response

### Running the Playground Notebook

```bash
pip install jupyter pandas nest_asyncio
jupyter lab tools_playground.ipynb
```

## License

This project is part of the garmin-mcp repository.

