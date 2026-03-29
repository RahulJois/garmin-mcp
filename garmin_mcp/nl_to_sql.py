"""
LangGraph-based NL→SQL agent.

This module implements a two-stage agent that converts natural language health
queries into SQLite queries and executes them against Garmin health databases.

ARCHITECTURE:
    Graph flow: generate_sql → execute_sql → END
    
    - generate_sql: Uses Google Gemini to generate SQL from natural language
    - execute_sql: Safely executes the SQL and returns results
    
    Each node receives the full AgentState dict and returns a partial dict
    to merge into state.

SAFETY:
    All generated SQL is validated using _is_safe() before execution to prevent
    injection attacks or accidental data modification. Only SELECT statements
    are allowed.

DATA FLOW:
    1. User provides natural language query (e.g. "How much did I sleep last week?")
    2. System prompt is constructed with database schema and current date
    3. LLM generates SELECT query based on schema
    4. Generated SQL is validated for safety
    5. SQL is executed against primary DB (with optional attached DBs for joins)
    6. Results are returned as list of row dicts
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
    """State dictionary for the NL→SQL LangGraph agent.
    
    Attributes:
        query: Natural language question about health data.
        schema_context: Schema description for the relevant domain (tables, columns).
        primary_db: Path to the primary SQLite database file.
        attach_dbs: Dict mapping database aliases to paths for databases to ATTACH.
        sql: Generated SQL query string (initially empty, filled by generate_sql).
        results: Query results as list of row dicts (filled by execute_sql).
        row_count: Number of rows returned (filled by execute_sql).
        error: Error message if something went wrong (empty string if successful).
    """
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
    """Extract SELECT statement from LLM response text.
    
    Handles various formats:
    - Plain SELECT statement
    - SELECT wrapped in markdown code fences (```sql ... ```)
    - SELECT with surrounding explanation text
    
    Args:
        text: Raw text response from LLM.
        
    Returns:
        Extracted SELECT statement without markdown or trailing semicolon.
    """
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
    """Validate that SQL is a safe SELECT statement.
    
    Prevents execution of dangerous DML/DDL statements by checking that:
    1. Statement starts with SELECT
    2. No INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, etc. keywords present
    
    Args:
        sql: SQL statement to validate.
        
    Returns:
        True if SQL is a safe SELECT statement, False otherwise.
    """
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
    """LLM node: Generate SQL from natural language query.
    
    Uses Google Generative AI with the system prompt and schema context
    to generate a SELECT query that answers the user's question.
    
    Args:
        state: AgentState dict containing:
            - query: Natural language question
            - schema_context: Database schema description
            
    Returns:
        Dict with keys:
            - sql: Generated SQL query string (empty if error)
            - error: Error message (empty string if successful)
    """
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
    """Database node: Execute generated SQL and return results.
    
    Validates SQL for safety, connects to the database, executes the query,
    and returns results as a list of dictionaries.
    
    Args:
        state: AgentState dict containing:
            - sql: SQL query to execute
            - primary_db: Path to main database
            - attach_dbs: Dict mapping aliases to database paths
            - error: Propagated error from previous node
            
    Returns:
        Dict with keys:
            - results: List of row dicts
            - row_count: Number of rows
            - error: Error message (empty if successful)
    """
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
    """Run a natural-language query through the NL→SQL LangGraph agent.
    
    This is the main public interface. It runs a natural language question through
    the two-stage agent:
    1. LLM generates SQL from the question and schema
    2. SQL is validated and executed against the database
    
    Args:
        query: Natural language question (e.g. "How much did I sleep last week?")
        schema_context: Database schema description for the domain.
        primary_db: Path to the main SQLite database file.
        attach_dbs: Optional dict mapping database aliases to paths for databases
                    that should be ATTACHed and available for JOINs.
                    
    Returns:
        Dict with keys:
            - sql: Generated SQL query string (for debugging)
            - results: List of result rows as dicts
            - row_count: Number of rows returned
            - error: Error message (empty string if successful)
            
    Example:
        >>> result = run_query(
        ...     query="How much did I sleep last week?",
        ...     schema_context="Table: sleep (day TEXT, total_sleep_seconds INTEGER)",
        ...     primary_db="/path/to/garmin.db"
        ... )
        >>> print(f"Found {result['row_count']} days of sleep data")
        >>> for row in result["results"]:
        ...     print(f"{row['day']}: {row['total_sleep_seconds']} seconds")
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
