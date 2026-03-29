"""
Basic smoke test for the garmin-mcp 3-tool MCP server.
Run with: .venv/bin/python test_server.py

Tests list_domains, get_schema, and execute_sql.
execute_sql tests are skipped gracefully if the real DBs don't exist.
"""

import asyncio
import json
from pathlib import Path

from garmin_mcp import config
from garmin_mcp.server import handle_call_tool, DB_PATHS


def call(tool_name: str, arguments: dict) -> dict:
    result = asyncio.run(handle_call_tool(tool_name, arguments))
    return json.loads(result[0].text)


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print(f"Garmin DB : {config.GARMIN_DB}")

    # --- list_domains ---
    section("list_domains")
    domains = call("list_domains", {})
    for name, desc in domains.items():
        print(f"  {name:20s}  {desc[:60]}")
    print(f"\n  → {len(domains)} domains listed")

    # --- get_schema ---
    section("get_schema (sleep)")
    schema_resp = call("get_schema", {"domain": "sleep"})
    if "error" in schema_resp:
        print(f"  ERROR: {schema_resp['error']}")
    else:
        print(f"  primary db : {schema_resp['db']}")
        print(f"  attach_dbs : {schema_resp['attach_dbs']}")
    print(f"  schema snippet: {str(schema_resp['schema'])[:80]} ...")
    err_resp = call("get_schema", {"domain": "not_real"})
    print(f"  error field present: {'error' in err_resp}")

    # --- execute_sql (per DB) ---
    SQL_TESTS = [
        ("garmin",            "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table'"),
        ("garmin_activities", "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table'"),
        ("garmin_monitoring", "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table'"),
        ("garmin_summary",    "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table'"),
    ]

    for db_key, sql in SQL_TESTS:
        section(f"execute_sql ({db_key})")
        db_path = DB_PATHS[db_key]
        if not Path(db_path).exists():
            print(f"  SKIP — DB file not found: {db_path}")
            continue
        result = call("execute_sql", {"db": db_key, "sql": sql})
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  rows   : {result['row_count']}")
            print(f"  result : {result['results']}")

    # --- safety check ---
    section("execute_sql — safety: INSERT is rejected")
    safe_resp = call("execute_sql", {
        "db": "garmin",
        "sql": "INSERT INTO sleep VALUES (1, '2026-03-29', NULL, NULL, 0, 0, 0, 0)",
    })
    print(f"  error returned: {'error' in safe_resp} ({safe_resp.get('error', '')})")

    print(f"\n{'='*60}")
    print("Smoke tests complete.")
