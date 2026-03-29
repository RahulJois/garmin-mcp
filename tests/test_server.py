"""Tests for MCP server functionality."""

import asyncio
import json
import sys

import pytest


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestConfigValidation:
    """Test configuration validation."""

    def _reload_config(self) -> object:
        if "garmin_mcp.config" in sys.modules:
            del sys.modules["garmin_mcp.config"]
        import garmin_mcp.config
        return garmin_mcp.config

    def test_config_accepts_valid_max_rows(self, monkeypatch) -> None:
        """Should accept valid MAX_ROWS setting."""
        monkeypatch.setenv("MAX_ROWS", "1000")
        cfg = self._reload_config()
        assert cfg.MAX_ROWS == 1000

    def test_config_rejects_invalid_max_rows(self, monkeypatch) -> None:
        """Should reject non-numeric MAX_ROWS."""
        monkeypatch.setenv("MAX_ROWS", "invalid")
        with pytest.raises(ValueError, match="MAX_ROWS must be a valid integer"):
            self._reload_config()

    def test_config_rejects_zero_max_rows(self, monkeypatch) -> None:
        """Should reject MAX_ROWS of 0."""
        monkeypatch.setenv("MAX_ROWS", "0")
        with pytest.raises(ValueError):
            self._reload_config()


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    """Test that TOOLS list is properly configured for the 3-tool architecture."""

    def test_tools_count(self) -> None:
        """Should expose exactly 3 tools."""
        from garmin_mcp.server import TOOLS
        assert len(TOOLS) == 3

    def test_tool_names(self) -> None:
        """Tool names should be list_domains, get_schema, execute_sql."""
        from garmin_mcp.server import TOOLS
        names = [t.name for t in TOOLS]
        assert names == ["list_domains", "get_schema", "execute_sql"]

    def test_all_tools_have_descriptions(self) -> None:
        """All tools should have meaningful descriptions."""
        from garmin_mcp.server import TOOLS
        for tool in TOOLS:
            assert tool.description
            assert len(tool.description) > 20

    def test_list_domains_has_no_required_params(self) -> None:
        """list_domains takes no required parameters."""
        from garmin_mcp.server import TOOLS
        tool = next(t for t in TOOLS if t.name == "list_domains")
        assert tool.inputSchema.get("required", []) == []

    def test_get_schema_requires_domain_param(self) -> None:
        """get_schema must require a 'domain' parameter."""
        from garmin_mcp.server import TOOLS
        tool = next(t for t in TOOLS if t.name == "get_schema")
        assert "domain" in tool.inputSchema.get("properties", {})
        assert "domain" in tool.inputSchema.get("required", [])

    def test_execute_sql_requires_db_and_sql_params(self) -> None:
        """execute_sql must require 'db' and 'sql' parameters."""
        from garmin_mcp.server import TOOLS
        tool = next(t for t in TOOLS if t.name == "execute_sql")
        required = tool.inputSchema.get("required", [])
        assert "db" in required
        assert "sql" in required


# ---------------------------------------------------------------------------
# _is_safe — moved from deleted test_nl_to_sql.py
# ---------------------------------------------------------------------------

class TestIsSafe:
    """Test cases for _is_safe function in garmin_mcp.server."""

    def setup_method(self) -> None:
        from garmin_mcp.server import _is_safe
        self._is_safe = _is_safe

    def test_safe_simple_select(self) -> None:
        assert self._is_safe("SELECT * FROM sleep") is True

    def test_safe_with_where_clause(self) -> None:
        assert self._is_safe("SELECT * FROM heart_rate WHERE day = '2026-03-20'") is True

    def test_safe_with_join(self) -> None:
        sql = "SELECT s.day, h.resting_heart_rate FROM sleep s JOIN heart_rate h ON s.day = h.day"
        assert self._is_safe(sql) is True

    def test_safe_case_insensitive(self) -> None:
        assert self._is_safe("select * from sleep") is True
        assert self._is_safe("SeLeCt * from sleep") is True

    def test_safe_with_leading_whitespace(self) -> None:
        assert self._is_safe("  \n  SELECT * FROM sleep") is True

    def test_unsafe_insert(self) -> None:
        assert self._is_safe("INSERT INTO sleep VALUES (1, '2026-03-20')") is False

    def test_unsafe_update(self) -> None:
        assert self._is_safe("UPDATE sleep SET total_sleep_seconds = 0") is False

    def test_unsafe_delete(self) -> None:
        assert self._is_safe("DELETE FROM sleep WHERE day = '2026-03-20'") is False

    def test_unsafe_drop(self) -> None:
        assert self._is_safe("DROP TABLE sleep") is False

    def test_unsafe_create(self) -> None:
        assert self._is_safe("CREATE TABLE sleep (id INTEGER)") is False

    def test_unsafe_alter(self) -> None:
        assert self._is_safe("ALTER TABLE sleep ADD COLUMN new_col TEXT") is False

    def test_unsafe_replace(self) -> None:
        assert self._is_safe("REPLACE INTO sleep VALUES (1, '2026-03-20')") is False

    def test_unsafe_truncate(self) -> None:
        assert self._is_safe("TRUNCATE TABLE sleep") is False

    def test_unsafe_not_starting_with_select(self) -> None:
        assert self._is_safe("PRAGMA table_info(sleep)") is False
        assert self._is_safe("  DELETE FROM sleep") is False


# ---------------------------------------------------------------------------
# handle_call_tool — handler integration tests
# ---------------------------------------------------------------------------

class TestHandleCallTool:
    """Integration tests for the three MCP tool handlers."""

    def _call(self, name: str, arguments: dict) -> dict:
        from garmin_mcp.server import handle_call_tool
        result = asyncio.run(handle_call_tool(name, arguments))
        return json.loads(result[0].text)

    # --- list_domains ---

    def test_list_domains_returns_all_domains(self) -> None:
        """list_domains should return a key for every domain in DOMAINS."""
        from garmin_mcp.schema_context import DOMAINS
        response = self._call("list_domains", {})
        assert set(response.keys()) == set(DOMAINS.keys())
        assert len(response) == 10

    def test_list_domains_values_are_strings(self) -> None:
        """Each value returned by list_domains should be a non-empty string."""
        response = self._call("list_domains", {})
        for domain, desc in response.items():
            assert isinstance(desc, str) and len(desc) > 0

    # --- get_schema ---

    def test_get_schema_valid_domain(self) -> None:
        """get_schema for a known domain returns schema, db, and attach_dbs."""
        response = self._call("get_schema", {"domain": "sleep"})
        assert "schema" in response
        assert "db" in response
        assert "attach_dbs" in response

    def test_get_schema_unknown_domain(self) -> None:
        """get_schema for an unknown domain returns an error."""
        response = self._call("get_schema", {"domain": "nonexistent"})
        assert "error" in response

    def test_get_schema_missing_domain(self) -> None:
        """get_schema with no domain argument returns an error."""
        response = self._call("get_schema", {})
        assert "error" in response

    # --- execute_sql ---

    def test_execute_sql_select_success(self, sample_sleep_db: str, monkeypatch) -> None:
        """execute_sql runs a SELECT and returns row_count and results."""
        import garmin_mcp.server as srv
        monkeypatch.setitem(srv.DB_PATHS, "garmin", sample_sleep_db)

        response = self._call("execute_sql", {
            "db": "garmin",
            "sql": "SELECT * FROM sleep",
        })
        assert "error" not in response
        assert response["row_count"] == 3
        assert len(response["results"]) == 3

    def test_execute_sql_with_where_clause(self, sample_sleep_db: str, monkeypatch) -> None:
        """execute_sql respects WHERE clause filtering."""
        import garmin_mcp.server as srv
        monkeypatch.setitem(srv.DB_PATHS, "garmin", sample_sleep_db)

        response = self._call("execute_sql", {
            "db": "garmin",
            "sql": "SELECT * FROM sleep WHERE day = '2026-03-20'",
        })
        assert "error" not in response
        assert response["row_count"] == 1

    def test_execute_sql_rejects_insert(self, sample_sleep_db: str, monkeypatch) -> None:
        """execute_sql must reject INSERT statements."""
        import garmin_mcp.server as srv
        monkeypatch.setitem(srv.DB_PATHS, "garmin", sample_sleep_db)

        response = self._call("execute_sql", {
            "db": "garmin",
            "sql": "INSERT INTO sleep VALUES (99, '2026-03-25', NULL, NULL, 0, 0, 0, 0)",
        })
        assert "error" in response

    def test_execute_sql_unknown_db(self) -> None:
        """execute_sql with an unknown db key returns an error."""
        response = self._call("execute_sql", {
            "db": "not_a_real_db",
            "sql": "SELECT 1",
        })
        assert "error" in response

    def test_execute_sql_empty_sql(self) -> None:
        """execute_sql with an empty sql string returns an error."""
        response = self._call("execute_sql", {
            "db": "garmin",
            "sql": "",
        })
        assert "error" in response

    def test_execute_sql_unknown_tool(self) -> None:
        """Calling an unknown tool name returns an error."""
        response = self._call("query_sleep", {"query": "test"})
        assert "error" in response
