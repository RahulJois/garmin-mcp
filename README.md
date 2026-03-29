# Garmin Health MCP Server

A Model Context Protocol (MCP) server that exposes Garmin health data as natural language query tools to Claude Desktop.

## Overview

This project implements an MCP server that connects Claude to your Garmin health data through 10 specialized tools. Each tool accepts natural language questions and converts them to SQL queries against your Garmin health databases.

**Architecture:**
- **NL→SQL Agent**: Uses Google Gemini to convert natural language to SQLite queries
- **Database Layer**: SQLite databases containing Garmin health data
- **MCP Server**: Exposes 10 domain-specific tools to Claude Desktop

## Features

### 10 Health Query Tools

1. **query_sleep** - Sleep duration, quality, REM/deep/light sleep, SpO2, respiration
2. **query_heart_rate** - Heart rate trends, resting HR, min/max daily rates, intraday readings
3. **query_stress** - Stress levels and patterns (0-100 scale)
4. **query_body_battery** - Garmin Body Battery energy levels
5. **query_weight** - Weight tracking over time (in kilograms)
6. **query_spo2_respiration** - Blood oxygen and respiration rates
7. **query_activities** - Workout summaries: distance, pace, calories, heart rate zones, VO2 max
8. **query_activity_detail** - Per-lap and per-second workout details
9. **query_daily_summary** - Daily steps, calories, activity minutes, hydration
10. **query_trends** - Long-term health trends by day/week/month/year

## Setup

### Prerequisites

- Python 3.10+
- Garmin health SQLite databases
- Google Gemini API key

### Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install project in editable mode
pip install -e .

# Install optional dev dependencies (for testing)
pip install -e .[dev]
```

### Configuration

#### 1. Set Environment Variables

```bash
export GEMINI_API_KEY="your-api-key-here"
export GEMINI_MODEL="gemini-2.5-flash"  # optional, defaults to gemini-2.5-flash
export MAX_ROWS="500"                    # optional, defaults to 500
```

Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

#### 2. Configure Claude Desktop

Update `~/.config/Claude/claude_desktop_config.json` (macOS/Linux) or the Windows equivalent:

```json
{
  "mcpServers": {
    "garmin-health": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "garmin_mcp.server"],
      "env": {
        "GEMINI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

#### 3. Database Setup

Ensure your Garmin health databases are in `~/HealthData/DBs/`:

```
~/HealthData/DBs/
├── garmin.db              # Main health data
├── garmin_activities.db   # Workout details
├── garmin_monitoring.db   # HR monitoring, stress
└── garmin_summary.db      # Daily summaries
```

## Usage

### Example Queries

Once configured, you can ask Claude:

- "How much did I sleep last week?"
- "What is my resting heart rate trend?"
- "Compare my stress levels weekday vs weekend"
- "How many calories did I burn yesterday?"
- "What is my average steps this month?"
- "Show my top 5 activities by training effect"
- "What was my body battery at the start of the day?"

### Query Response Format

Each tool returns a JSON response:

```json
{
  "sql": "SELECT day, total_sleep_seconds FROM sleep WHERE day >= '2026-03-20'",
  "results": [
    {"day": "2026-03-20", "total_sleep_seconds": 28800},
    {"day": "2026-03-21", "total_sleep_seconds": 27900}
  ],
  "row_count": 2,
  "error": ""
}
```

## Testing

### Run Tests

```bash
# Install test dependencies
pip install -e .[dev]

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=garmin_mcp

# Run specific test file
pytest tests/test_nl_to_sql.py -v

# Run tests matching pattern
pytest tests/ -k "extract" -v
```

### Test Coverage

Tests verify:
- ✅ SQL extraction from LLM responses (plain, markdown, with explanation)
- ✅ SQL safety validation (blocks INSERT, UPDATE, DELETE, etc.)
- ✅ Configuration validation (required env vars)
- ✅ Tool definitions (descriptions, input schemas)
- ✅ Database execution (safe query execution)
- ✅ Error handling (graceful degradation)

## Architecture & Implementation

### NL→SQL Agent Flow

```
User Query
    ↓
[generate_sql node]
- Format system prompt with schema & date
- Call Google Gemini API
- Extract SQL from response
    ↓
[execute_sql node]
- Validate SQL safety (_is_safe check)
- Connect to SQLite database
- ATTACH secondary databases if needed
- Execute query
- Return results
    ↓
Response (sql, results, row_count, error)
```

### Key Components

| File | Purpose |
|------|---------|
| `garmin_mcp/server.py` | MCP server entry point, tool definitions |
| `garmin_mcp/nl_to_sql.py` | NL→SQL agent using LangGraph |
| `garmin_mcp/config.py` | Configuration and env var validation |
| `garmin_mcp/schema_context.py` | Database schemas for each tool |
| `tests/` | Comprehensive test suite |

## Configuration Details

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Generative AI API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Model to use for SQL generation |
| `MAX_ROWS` | No | `500` | Maximum rows per query result |

### Database Paths

Configured in `config.py`:

```python
DB_DIR = Path.home() / "HealthData" / "DBs"

GARMIN_DB      = "~/HealthData/DBs/garmin.db"
ACTIVITIES_DB  = "~/HealthData/DBs/garmin_activities.db"
MONITORING_DB  = "~/HealthData/DBs/garmin_monitoring.db"
SUMMARY_DB     = "~/HealthData/DBs/garmin_summary.db"
```

## Error Handling

The system handles errors gracefully:

1. **Configuration Errors**: Missing GEMINI_API_KEY raises ValueError on startup
2. **LLM Errors**: Connection issues return error in response
3. **SQL Safety**: Dangerous SQL is blocked before execution
4. **Database Errors**: SQLite errors are caught and returned in response
5. **Missing Data**: Returns empty results instead of crashing

## Performance Considerations

- **Query Caching**: Each query calls Gemini API (no caching yet)
- **Row Limits**: MAX_ROWS prevents overwhelming Claude with large result sets
- **Database Connections**: New connection per query (no connection pooling yet)
- **LLM Calls**: Single call per query to generate SQL

## Future Improvements

- [ ] Query result caching to reduce API calls
- [ ] Connection pooling for database operations
- [ ] Rate limiting (daily query budgets)
- [ ] Monitoring and analytics (latency, token usage)
- [ ] Support for cached system prompts
- [ ] Additional health data sources

## Troubleshooting

### "GEMINI_API_KEY environment variable is not set"
- Ensure the environment variable is set in Claude Desktop config
- Restart Claude Desktop after updating config

### "No such file or directory: garmin.db"
- Verify databases exist in `~/HealthData/DBs/`
- Check paths in [garmin_mcp/config.py](garmin_mcp/config.py)

### "Unknown tool" error
- Restart Claude Desktop to reload tool definitions
- Check MCP server logs for initialization errors

### Query returns no results
- Check the generated SQL (included in response for debugging)
- Verify data exists for the date range queried
- Try a broader date range

## Development

### Running Tests During Development

```bash
# Watch mode (requires pytest-watch)
ptw tests/

# Verbose output
pytest tests/ -vv

# Stop on first failure
pytest tests/ -x
```

### Adding New Tools

To add a new health query tool:

1. Define tool in `server.py` (add to TOOLS list)
2. Add schema context in `schema_context.py`
3. Map database paths in `server.py` (_DB_KEY_TO_PATH)
4. Add test case in `tests/test_server.py`

## License

This project is part of the garmin-mcp repository.
