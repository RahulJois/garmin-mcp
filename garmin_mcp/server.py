"""
Garmin Health MCP Server

Exposes 10 domain-specific tools to Claude Desktop.
Each tool accepts a natural language question, runs it through the
NL→SQL LangGraph agent, and returns JSON results.

SCHEMA CONTEXT:
    Each tool is configured with a schema_context that describes the tables,
    columns, and data types available for that domain. This context is passed
    to the LLM to generate appropriate SQL queries.
    
    Example schema:
        "Table: sleep (day TEXT, total_sleep_seconds INTEGER, deep_sleep_seconds INTEGER)
         Table: heart_rate (day TEXT, resting_heart_rate INTEGER)"
    
    The schema_context includes:
    - Primary database: main database for the domain (e.g., "garmin.db" for sleep)
    - Attached databases: secondary databases that can be JOINed (e.g., "monitoring.db")
    - Table and column descriptions: what each field represents and units

USAGE:
    Each tool accepts a single parameter "query" which is a natural language
    question like "How did I sleep last week?" or "What is my average RHR?"
    
    The tool returns a JSON response with:
    - sql: The generated SQL query (for debugging)
    - results: List of result rows as dictionaries
    - row_count: Number of rows returned
    - error: Error message if something went wrong
"""

import asyncio
import json
import logging
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import config
from .nl_to_sql import run_query
from .schema_context import TOOL_SCHEMA_MAP

# Setup logging to file (not stderr, to avoid interfering with MCP stdio protocol)
log_file = Path.home() / ".garmin_mcp.log"
logging.basicConfig(
    level=logging.INFO,
    format='[MCP] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file)]
)
logger = logging.getLogger(__name__)
logger.info("Garmin MCP server starting...")

# ---------------------------------------------------------------------------
# DB path resolver
# ---------------------------------------------------------------------------

_DB_KEY_TO_PATH = {
    "garmin":             config.GARMIN_DB,
    "garmin_activities":  config.ACTIVITIES_DB,
    "garmin_monitoring":  config.MONITORING_DB,
    "garmin_summary":     config.SUMMARY_DB,
}


def _resolve_db_paths(tool_name: str) -> tuple[str, dict]:
    """Return (primary_db_path, {alias: attach_db_path}) for a tool.
    
    Args:
        tool_name: Name of the tool (e.g. "query_sleep").
        
    Returns:
        Tuple of (primary_db_path, attach_dbs_dict) where:
        - primary_db_path: Path to the main database for this tool
        - attach_dbs_dict: Dictionary mapping aliases to paths for databases
          that should be ATTACHed to the connection for JOINs
    """
    cfg = TOOL_SCHEMA_MAP[tool_name]
    primary = _DB_KEY_TO_PATH[cfg["primary_db"]]
    attach = {alias: _DB_KEY_TO_PATH[key] for alias, key in cfg["attach_dbs"].items()}
    return primary, attach


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_QUERY_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Natural language question about the health data.",
        }
    },
    "required": ["query"],
}

TOOLS = [
    types.Tool(
        name="query_sleep",
        description=(
            "Answer questions about sleep data: total sleep duration, deep/light/REM sleep, "
            "sleep score, sleep quality qualifier (GOOD/FAIR/POOR), time to bed/wake time, "
            "sleep events, average SpO2 and respiration during sleep, and stress during sleep. "
            "Use for questions like: 'How did I sleep last week?', "
            "'What is my average REM sleep this month?', 'When did I wake up most often?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_heart_rate",
        description=(
            "Answer questions about heart rate: resting heart rate (RHR), min/max heart rate "
            "by day, and intraday heart rate readings (~2-minute resolution from the monitoring DB). "
            "Use for: 'What is my resting heart rate trend?', "
            "'When was my heart rate highest today?', 'What is my average RHR this year?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_stress",
        description=(
            "Answer questions about stress levels: raw stress readings (~3-minute resolution) "
            "and daily average stress. Stress is scored 0-100 "
            "(0-25 resting, 26-50 low, 51-75 medium, 76-100 high). "
            "Use for: 'What are my most stressful days?', "
            "'How does my stress compare weekday vs weekend?', 'Average stress this month?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_body_battery",
        description=(
            "Answer questions about Garmin Body Battery energy levels: "
            "daily max, min, and charged amounts (all 0-100 scale). "
            "Use for: 'What was my body battery at the start of the day?', "
            "'Which days did I end with low body battery?', 'Body battery trend this week?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_weight",
        description=(
            "Answer questions about body weight over time. Weight is stored in kilograms. "
            "Use for: 'What is my weight trend this year?', "
            "'How much weight have I lost in the last 3 months?', 'My heaviest recorded weight?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_spo2_respiration",
        description=(
            "Answer questions about blood oxygen saturation (SpO2, %) and respiration rate "
            "(breaths per minute). Covers both daytime spot readings and overnight sleep averages. "
            "Use for: 'What is my average SpO2 during sleep?', "
            "'Did my blood oxygen drop last night?', 'Respiration rate trend this week?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_activities",
        description=(
            "Answer questions about workout activity summaries: runs, rides, walks, swims, "
            "paddle sports, etc. Includes distance, duration, pace, cadence, calories, "
            "heart rate zones, training effect, VO2 max estimates, ascent/descent, temperature. "
            "Use for: 'How far did I run last week?', 'What is my best 5K time?', "
            "'Average cycling speed this month?', 'How many activities did I do in March?', "
            "'Which runs had the highest training effect?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_activity_detail",
        description=(
            "Answer questions about per-lap or per-second detail within a specific activity. "
            "Use this when you need split data, heart rate curves, elevation profiles, "
            "or GPS traces for a particular workout. "
            "Use for: 'What were my lap splits in my last run?', "
            "'Show heart rate during my long run on Saturday', "
            "'What was my pace in each lap of my bike ride?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_daily_summary",
        description=(
            "Answer questions about daily health summaries: steps, distance, floors climbed, "
            "calories (total/active/BMR/consumed), hydration, sweat loss, "
            "moderate and vigorous activity minutes, and intensity time vs goal. "
            "Use for: 'Did I hit my step goal this week?', "
            "'How many calories did I burn yesterday?', 'Average daily steps this month?', "
            "'How hydrated was I last week?', 'Active minutes this week?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
    types.Tool(
        name="query_trends",
        description=(
            "Answer questions about long-term health trends aggregated by day, week, month, "
            "or year. Covers HR, RHR, weight, steps, sleep, stress, calories, activities, "
            "SpO2, body battery, and intensity time. Best for trend analysis and comparisons "
            "across longer time periods. "
            "Use for: 'How has my resting heart rate changed over the past year?', "
            "'Compare my sleep this month vs last month', "
            "'Which month did I exercise the most?', 'Year-over-year step count comparison?'"
        ),
        inputSchema=_QUERY_INPUT_SCHEMA,
    ),
]

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("garmin-health")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available health data query tools.
    
    Returns:
        List of Tool definitions for Claude Desktop to display.
    """
    return TOOLS


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    """Execute a health data query tool.
    
    Args:
        name: Name of the tool to call (e.g. "query_sleep").
        arguments: Dictionary containing "query" parameter with natural language question.
        
    Returns:
        List containing single TextContent with JSON result or error message.
        
    JSON Response Structure:
        {
            "sql": "generated SQL query (for debugging)",
            "results": [list of row dicts],
            "row_count": int,
            "error": "error message or empty string if successful"
        }
    """
    logger.info(f"Tool called: {name}")
    logger.info(f"Query: {arguments.get('query', '')}")
    
    if name not in TOOL_SCHEMA_MAP:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]

    query = arguments.get("query", "").strip()
    if not query:
        error_msg = "Error: 'query' parameter is required."
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]

    cfg = TOOL_SCHEMA_MAP[name]
    primary_db, attach_dbs = _resolve_db_paths(name)

    result = run_query(
        query=query,
        schema_context=cfg["schema"],
        primary_db=primary_db,
        attach_dbs=attach_dbs,
    )

    if result["error"]:
        logger.error(f"Query error: {result['error']}")
        output = {
            "error": result["error"],
            "sql": result.get("sql", ""),
        }
    else:
        logger.info(f"Query successful: {result['row_count']} rows returned")
        logger.info(f"Generated SQL: {result['sql']}")
        output = {
            "sql": result["sql"],
            "row_count": result["row_count"],
            "results": result["results"],
        }

    response_text = json.dumps(output, indent=2, default=str)
    logger.info(f"Sending response ({len(response_text)} bytes):")
    logger.info(f"Response content:\n{response_text}")
    
    return [types.TextContent(type="text", text=response_text)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
