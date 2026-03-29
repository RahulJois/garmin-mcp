"""Tests for NL→SQL transformation and execution logic."""

import pytest
from garmin_mcp.nl_to_sql import _extract_sql, _is_safe


class TestExtractSQL:
    """Test cases for _extract_sql function."""
    
    def test_extract_plain_select(self) -> None:
        """Should extract plain SELECT statement."""
        text = "SELECT * FROM sleep WHERE day = '2026-03-20'"
        assert _extract_sql(text) == text
    
    def test_extract_with_markdown_code_fence(self) -> None:
        """Should extract SELECT from markdown code fence."""
        text = "```sql\nSELECT * FROM sleep\n```"
        expected = "SELECT * FROM sleep"
        assert _extract_sql(text) == expected
    
    def test_extract_with_backticks_no_language(self) -> None:
        """Should extract SELECT from backticks without language specifier."""
        text = "```\nSELECT * FROM heart_rate\n```"
        expected = "SELECT * FROM heart_rate"
        assert _extract_sql(text) == expected
    
    def test_extract_with_extra_text_before(self) -> None:
        """Should skip text before SELECT statement."""
        text = "Here is the query:\n\nSELECT * FROM stress"
        assert _extract_sql(text) == "SELECT * FROM stress"
    
    def test_extract_with_semicolon(self) -> None:
        """Should remove trailing semicolon."""
        text = "SELECT * FROM activities;"
        expected = "SELECT * FROM activities"
        assert _extract_sql(text) == expected
    
    def test_extract_multiline_query(self) -> None:
        """Should handle multiline SELECT statements."""
        text = """SELECT 
            day, 
            total_sleep_seconds 
        FROM sleep 
        WHERE day > '2026-03-01'"""
        result = _extract_sql(text)
        assert result.startswith("SELECT")
        assert "total_sleep_seconds" in result


class TestIsSafe:
    """Test cases for _is_safe function."""
    
    def test_safe_simple_select(self) -> None:
        """Should accept simple SELECT statements."""
        assert _is_safe("SELECT * FROM sleep") is True
    
    def test_safe_with_where_clause(self) -> None:
        """Should accept SELECT with WHERE clause."""
        assert _is_safe("SELECT * FROM heart_rate WHERE day = '2026-03-20'") is True
    
    def test_safe_with_join(self) -> None:
        """Should accept SELECT with JOINs."""
        sql = "SELECT s.day, h.resting_heart_rate FROM sleep s JOIN heart_rate h ON s.day = h.day"
        assert _is_safe(sql) is True
    
    def test_safe_case_insensitive(self) -> None:
        """Should accept SELECT in any case."""
        assert _is_safe("select * from sleep") is True
        assert _is_safe("SeLeCt * from sleep") is True
    
    def test_unsafe_insert(self) -> None:
        """Should reject INSERT statements."""
        assert _is_safe("INSERT INTO sleep VALUES (1, '2026-03-20', ...)") is False
    
    def test_unsafe_update(self) -> None:
        """Should reject UPDATE statements."""
        assert _is_safe("UPDATE sleep SET total_sleep_seconds = 0") is False
    
    def test_unsafe_delete(self) -> None:
        """Should reject DELETE statements."""
        assert _is_safe("DELETE FROM sleep WHERE day = '2026-03-20'") is False
    
    def test_unsafe_drop(self) -> None:
        """Should reject DROP statements."""
        assert _is_safe("DROP TABLE sleep") is False
    
    def test_unsafe_create(self) -> None:
        """Should reject CREATE TABLE statements."""
        assert _is_safe("CREATE TABLE sleep (id INTEGER)") is False
    
    def test_unsafe_alter(self) -> None:
        """Should reject ALTER TABLE statements."""
        assert _is_safe("ALTER TABLE sleep ADD COLUMN new_col") is False
    
    def test_unsafe_replace(self) -> None:
        """Should reject REPLACE statements."""
        assert _is_safe("REPLACE INTO sleep VALUES (1, '2026-03-20')") is False
    
    def test_unsafe_truncate(self) -> None:
        """Should reject TRUNCATE statements."""
        assert _is_safe("TRUNCATE TABLE sleep") is False
    
    def test_unsafe_insert_in_select(self) -> None:
        """Should reject SELECT that contains INSERT keyword."""
        assert _is_safe("SELECT * FROM sleep; INSERT INTO sleep VALUES (1)") is False
    
    def test_unsafe_not_starting_with_select(self) -> None:
        """Should reject statements not starting with SELECT."""
        assert _is_safe("PRAGMA table_info(sleep)") is False
        assert _is_safe("  DELETE FROM sleep") is False
    
    def test_safe_with_leading_whitespace(self) -> None:
        """Should handle leading whitespace."""
        assert _is_safe("  \n  SELECT * FROM sleep") is True


class TestSQLExecution:
    """Test cases for SQL execution with real databases."""
    
    def test_execute_simple_select(self, sample_sleep_db: str) -> None:
        """Should execute simple SELECT query."""
        from garmin_mcp.nl_to_sql import run_query, _build_graph
        
        query = "How much did I sleep on 2026-03-20?"
        schema = "Table: sleep (day, total_sleep_seconds, deep_sleep_seconds)"
        
        # Mock the run_query instead - we'll test the graph separately
        # This is just to verify the function signature works
        result = run_query(
            query=query,
            schema_context=schema,
            primary_db=sample_sleep_db,
            attach_dbs={}
        )
        
        assert isinstance(result, dict)
        assert "sql" in result
        assert "results" in result
        assert "error" in result
        assert "row_count" in result
    
    def test_run_query_returns_correct_structure(self, sample_heart_rate_db: str) -> None:
        """Should return dict with expected keys."""
        from garmin_mcp.nl_to_sql import run_query
        
        result = run_query(
            query="Show all heart rate data",
            schema_context="Table: heart_rate (day, resting_heart_rate, min_heart_rate, max_heart_rate)",
            primary_db=sample_heart_rate_db,
        )
        
        assert set(result.keys()) >= {"sql", "results", "row_count", "error"}
