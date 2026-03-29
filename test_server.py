"""
Basic smoke test for the garmin-mcp NL→SQL pipeline.
Run with: .venv/bin/python test_server.py
Requires GEMINI_API_KEY to be set in the environment.
"""

import json
from garmin_mcp import config
from garmin_mcp.nl_to_sql import run_query
from garmin_mcp.schema_context import TOOL_SCHEMA_MAP

DB_MAP = {
    "garmin":            config.GARMIN_DB,
    "garmin_activities": config.ACTIVITIES_DB,
    "garmin_monitoring": config.MONITORING_DB,
    "garmin_summary":    config.SUMMARY_DB,
}

TESTS = [
    ("query_sleep",         "How many hours did I sleep last night?"),
    ("query_heart_rate",    "What was my resting heart rate this week?"),
    ("query_daily_summary", "How many steps did I take yesterday?"),
    ("query_activities",    "What activities did I do in the last 7 days?"),
    ("query_trends",        "What is my average sleep duration per month this year?"),
]


def run_test(tool_name: str, question: str) -> None:
    cfg = TOOL_SCHEMA_MAP[tool_name]
    primary_db = DB_MAP[cfg["primary_db"]]
    attach_dbs = {alias: DB_MAP[key] for alias, key in cfg["attach_dbs"].items()}

    print(f"\n{'='*60}")
    print(f"Tool   : {tool_name}")
    print(f"Query  : {question}")

    result = run_query(
        query=question,
        schema_context=cfg["schema"],
        primary_db=primary_db,
        attach_dbs=attach_dbs,
    )

    if result["error"]:
        print(f"ERROR  : {result['error']}")
        print(f"SQL    : {result.get('sql', '')}")
    else:
        print(f"SQL    : {result['sql']}")
        print(f"Rows   : {result['row_count']}")
        if result["results"]:
            print(f"Sample : {json.dumps(result['results'][0], default=str)}")
        else:
            print("Sample : (no rows returned)")


if __name__ == "__main__":
    print(f"GEMINI_API_KEY set : {bool(config.GEMINI_API_KEY)}")
    print(f"Garmin DB          : {config.GARMIN_DB}")

    if not config.GEMINI_API_KEY:
        print("\nERROR: Set GEMINI_API_KEY before running.")
        raise SystemExit(1)

    for tool_name, question in TESTS:
        run_test(tool_name, question)

    print(f"\n{'='*60}")
    print("All tests complete.")
