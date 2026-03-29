"""
Garmin Health MCP Server

Exposes 10 domain-specific tools to Claude Desktop.
Each tool accepts a natural language question, runs it through the
NL→SQL LangGraph agent, and returns JSON results.
"""

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import config
from .nl_to_sql import run_query
from .schema_context import TOOL_SCHEMA_MAP

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
    """Return (primary_db_path, {alias: attach_db_path}) for a tool."""
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
    return TOOLS


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    if name not in TOOL_SCHEMA_MAP:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    query = arguments.get("query", "").strip()
    if not query:
        return [types.TextContent(type="text", text="Error: 'query' parameter is required.")]

    cfg = TOOL_SCHEMA_MAP[name]
    primary_db, attach_dbs = _resolve_db_paths(name)

    result = run_query(
        query=query,
        schema_context=cfg["schema"],
        primary_db=primary_db,
        attach_dbs=attach_dbs,
    )

    if result["error"]:
        output = {
            "error": result["error"],
            "sql": result.get("sql", ""),
        }
    else:
        output = {
            "sql": result["sql"],
            "row_count": result["row_count"],
            "results": result["results"],
        }

    return [types.TextContent(type="text", text=json.dumps(output, indent=2, default=str))]


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
