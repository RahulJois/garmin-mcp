"""
LangGraph-based NL→SQL agent.

Graph:  generate_sql → execute_sql → END

Each node receives the full AgentState dict and returns a partial dict
to merge into state.
"""

import re
import json
import sqlite3
from datetime import date
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from . import config


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    query: str            # natural language question
    schema_context: str   # schema string for the relevant domain
    primary_db: str       # path to the primary SQLite DB
    attach_dbs: dict      # {alias: path} for additional DBs to ATTACH
    sql: str              # generated SQL (filled by generate_sql node)
    results: list         # query results (filled by execute_sql node)
    row_count: int        # number of rows returned
    error: str            # error message if something went wrong


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a SQLite expert. Given the database schema below and the user's question, \
generate a single SELECT SQL query that answers the question.

Today's date: {today}

{schema_context}

Important rules:
- Output ONLY the SQL query — no explanation, no markdown, no code fences.
- Use only SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
- Dates are stored as 'YYYY-MM-DD'. Datetimes as 'YYYY-MM-DD HH:MM:SS'.
- TIME columns contain duration strings like '01:30:00' (1 hour 30 minutes).
  To get total minutes: (CAST(SUBSTR(col,1,2) AS INTEGER)*60 + CAST(SUBSTR(col,4,2) AS INTEGER))
  To get total hours:   (CAST(SUBSTR(col,1,2) AS INTEGER) + CAST(SUBSTR(col,4,2) AS INTEGER)/60.0)
- For tables prefixed with an alias (e.g. monitoring.monitoring_hr), \
  the alias refers to an ATTACHed database — use that prefix in your SQL.
- Add LIMIT {max_rows} when the query could return a large number of rows.
- Use strftime() for date arithmetic, e.g.:
    strftime('%Y-%m-%d', 'now', '-7 days')  -- 7 days ago
    strftime('%Y-%m', day) = strftime('%Y-%m', 'now')  -- current month
"""


def _extract_sql(text: str) -> str:
    """Pull the SELECT statement out of the LLM response."""
    # Strip markdown code fences if present
    m = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Find first SELECT ... either to end or to semicolon
    m = re.search(r"(SELECT[\s\S]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(";")
    return text.strip()


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
# Graph nodes
# ---------------------------------------------------------------------------

def generate_sql(state: AgentState) -> dict:
    if not config.GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY environment variable is not set.", "sql": ""}

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GEMINI_API_KEY,
        temperature=0,
    )

    system = _SYSTEM_PROMPT.format(
        today=date.today().isoformat(),
        schema_context=state["schema_context"],
        max_rows=config.MAX_ROWS,
    )

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=state["query"]),
    ]

    try:
        response = llm.invoke(messages)
        sql = _extract_sql(response.content)
        return {"sql": sql, "error": ""}
    except Exception as exc:
        return {"sql": "", "error": f"LLM error: {exc}"}


def execute_sql(state: AgentState) -> dict:
    if state.get("error"):
        return {}  # propagate the error without running SQL

    sql = state.get("sql", "").strip()
    if not sql:
        return {"error": "No SQL was generated."}

    if not _is_safe(sql):
        return {"error": f"Unsafe SQL blocked: {sql[:200]}"}

    conn = None
    try:
        conn = sqlite3.connect(state["primary_db"])
        conn.row_factory = sqlite3.Row

        # Attach additional databases
        for alias, path in (state.get("attach_dbs") or {}).items():
            conn.execute("ATTACH DATABASE ? AS ?", (path, alias))

        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(config.MAX_ROWS)
        results = [dict(zip(columns, row)) for row in rows]

        return {"results": results, "row_count": len(results), "error": ""}

    except sqlite3.Error as exc:
        return {"results": [], "row_count": 0, "error": f"SQL execution error: {exc}"}
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def _build_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.set_entry_point("generate_sql")
    graph.add_edge("generate_sql", "execute_sql")
    graph.add_edge("execute_sql", END)
    return graph.compile()


_graph = None


def run_query(
    query: str,
    schema_context: str,
    primary_db: str,
    attach_dbs: dict | None = None,
) -> dict:
    """
    Run a natural-language query through the NL→SQL LangGraph agent.

    Returns a dict with keys:
      - sql: the generated SQL string
      - results: list of row dicts
      - row_count: number of rows
      - error: error message (empty string if successful)
    """
    global _graph
    if _graph is None:
        _graph = _build_graph()

    initial_state: AgentState = {
        "query": query,
        "schema_context": schema_context,
        "primary_db": primary_db,
        "attach_dbs": attach_dbs or {},
        "sql": "",
        "results": [],
        "row_count": 0,
        "error": "",
    }

    final_state = _graph.invoke(initial_state)

    return {
        "sql": final_state.get("sql", ""),
        "results": final_state.get("results", []),
        "row_count": final_state.get("row_count", 0),
        "error": final_state.get("error", ""),
    }
