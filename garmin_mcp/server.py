"""
Garmin Health MCP Server

Exposes 4 tools to Claude Desktop:
  - list_domains   : list available health data domains with short descriptions
  - get_schema     : return full table/column schema for a domain
  - execute_sql    : run a SELECT query against the health databases
  - push_workout   : push a structured running workout to Garmin Connect

Claude reads the schema and writes SQL directly, eliminating any external
LLM API dependency.
"""

import asyncio
import json
import logging
import re
import sqlite3
from datetime import date
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import config
from .push_workout import PUSH_WORKOUT_TOOL, handle_push_workout
from .schema_context import DOMAINS, _unit_note

# Setup logging to file (not stderr, to avoid interfering with MCP stdio)
log_file = Path.home() / ".garmin_mcp.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="[MCP] %(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file)],
)
logger = logging.getLogger(__name__)
logger.info("Garmin MCP server starting...")

# ---------------------------------------------------------------------------
# DB path map
# ---------------------------------------------------------------------------

DB_PATHS = {
    "garmin":            config.GARMIN_DB,
    "garmin_activities": config.ACTIVITIES_DB,
    "garmin_monitoring": config.MONITORING_DB,
    "garmin_summary":    config.SUMMARY_DB,
}

# ---------------------------------------------------------------------------
# SQL safety
# ---------------------------------------------------------------------------

def _is_safe(sql: str) -> bool:
    """Allow only SELECT statements; block any DML/DDL."""
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return False
    dangerous = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|REPLACE|TRUNCATE)\b"
    )
    return not dangerous.search(normalized)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    PUSH_WORKOUT_TOOL,
    types.Tool(
        name="list_domains",
        description=(
            "List all available Garmin health data domains with short descriptions. "
            "Call this to discover what data is available, then call get_schema on "
            "the relevant domain before writing SQL."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_schema",
        description=(
            "Get the full table and column schema for a Garmin health data domain. "
            "Returns table definitions, column names, types, units, and the db/attach_dbs "
            "values to pass to execute_sql. Call this before writing any SQL query."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain name as returned by list_domains (e.g. 'sleep', 'activities').",
                }
            },
            "required": ["domain"],
        },
    ),
    types.Tool(
        name="execute_sql",
        description=(
            "Execute a SELECT SQL query against the Garmin health databases. "
            "Only SELECT statements are allowed — no INSERT, UPDATE, DELETE, DROP, etc. "
            "Use the 'db' and 'attach_dbs' values returned by get_schema. "
            "Dates are stored as 'YYYY-MM-DD', datetimes as 'YYYY-MM-DD HH:MM:SS', "
            "TIME columns as 'HH:MM:SS' strings (e.g. '01:30:00' = 90 min). "
            f"{_unit_note}. "
            f"Today's date is {date.today().isoformat()}."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "db": {
                    "type": "string",
                    "description": "Primary database key.",
                    "enum": ["garmin", "garmin_activities", "garmin_monitoring", "garmin_summary"],
                },
                "sql": {
                    "type": "string",
                    "description": "The SELECT SQL query to execute.",
                },
                "attach_dbs": {
                    "type": "object",
                    "description": (
                        "Optional mapping of alias to db key for ATTACH DATABASE. "
                        "Example: {\"monitoring\": \"garmin_monitoring\"}"
                    ),
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["db", "sql"],
        },
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
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    logger.info(f"Tool called: {name}")

    def respond(data: dict) -> list[types.TextContent]:
        payload = json.dumps(data, indent=2, default=str)
        logger.debug(f"Response for '{name}':\n{payload}")
        return [types.TextContent(type="text", text=payload)]

    # --- push_workout ---
    if name == "push_workout":
        return respond(handle_push_workout(arguments))

    # --- list_domains ---
    if name == "list_domains":
        logger.debug("list_domains: returning all domain descriptions")
        return respond({domain: info["description"] for domain, info in DOMAINS.items()})

    # --- get_schema ---
    if name == "get_schema":
        domain = arguments.get("domain", "").strip()
        logger.debug(f"get_schema: domain='{domain}'")
        if domain not in DOMAINS:
            return respond({"error": f"Unknown domain '{domain}'. Call list_domains to see available domains."})
        info = DOMAINS[domain]
        return respond({
            "schema": info["schema"],
            "db": info["primary_db"],
            "attach_dbs": info["attach_dbs"],
        })

    # --- execute_sql ---
    if name == "execute_sql":
        sql = arguments.get("sql", "").strip()
        db_key = arguments.get("db", "").strip()
        attach_dbs = arguments.get("attach_dbs") or {}

        if not sql:
            return respond({"error": "'sql' parameter is required."})
        if db_key not in DB_PATHS:
            return respond({"error": f"Unknown db '{db_key}'. Must be one of: {list(DB_PATHS.keys())}"})
        if not _is_safe(sql):
            logger.warning(f"execute_sql: rejected unsafe SQL: {sql!r}")
            return respond({"error": "Only SELECT statements are allowed."})

        logger.info(f"execute_sql: db={db_key} attach_dbs={list(attach_dbs.keys())}")
        logger.debug(f"execute_sql SQL:\n{sql}")

        conn = None
        try:
            conn = sqlite3.connect(DB_PATHS[db_key])
            conn.row_factory = sqlite3.Row

            for alias, key in attach_dbs.items():
                if key not in DB_PATHS:
                    return respond({"error": f"Unknown attach db '{key}'."})
                conn.execute("ATTACH DATABASE ? AS ?", (DB_PATHS[key], alias))
                logger.debug(f"execute_sql: attached '{key}' as '{alias}'")

            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchmany(config.MAX_ROWS)
            results = [dict(zip(columns, row)) for row in rows]
            row_count = len(results)

            output: dict = {"row_count": row_count, "results": results}
            if row_count == config.MAX_ROWS:
                output["warning"] = f"Results may be truncated at {config.MAX_ROWS} rows. Add a LIMIT or WHERE clause to narrow the query."

            logger.info(f"execute_sql: {row_count} rows returned")
            if results:
                logger.debug(f"execute_sql first row: {results[0]}")
            return respond(output)

        except sqlite3.Error as exc:
            logger.error(f"SQL error: {exc}")
            logger.debug(f"execute_sql failed SQL:\n{sql}")
            return respond({"error": f"SQL error: {exc}"})
        finally:
            if conn:
                conn.close()

    return respond({"error": f"Unknown tool: {name}"})


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
