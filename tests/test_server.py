"""Tests for MCP server functionality."""

import pytest


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_config_requires_gemini_api_key(self, monkeypatch) -> None:
        """Should fail if GEMINI_API_KEY is not set."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            # Reimport to trigger validation
            import sys
            if "garmin_mcp.config" in sys.modules:
                del sys.modules["garmin_mcp.config"]
            import garmin_mcp.config
    
    def test_config_accepts_valid_max_rows(self, monkeypatch) -> None:
        """Should accept valid MAX_ROWS setting."""
        monkeypatch.setenv("MAX_ROWS", "1000")
        
        import sys
        if "garmin_mcp.config" in sys.modules:
            del sys.modules["garmin_mcp.config"]
        
        import garmin_mcp.config
        assert garmin_mcp.config.MAX_ROWS == 1000
    
    def test_config_rejects_invalid_max_rows(self, monkeypatch) -> None:
        """Should reject non-numeric MAX_ROWS."""
        monkeypatch.setenv("MAX_ROWS", "invalid")
        
        import sys
        if "garmin_mcp.config" in sys.modules:
            del sys.modules["garmin_mcp.config"]
        
        with pytest.raises(ValueError, match="MAX_ROWS must be a valid integer"):
            import garmin_mcp.config


class TestToolDefinitions:
    """Test that tool definitions are properly configured."""
    
    def test_tools_exist(self) -> None:
        """Should expose exactly 10 tools."""
        from garmin_mcp.server import TOOLS
        assert len(TOOLS) == 10
    
    def test_all_tools_have_descriptions(self) -> None:
        """All tools should have meaningful descriptions."""
        from garmin_mcp.server import TOOLS
        
        for tool in TOOLS:
            assert tool.description
            assert len(tool.description) > 20  # Should be descriptive
    
    def test_all_tools_have_query_input_schema(self) -> None:
        """All tools should accept a 'query' parameter."""
        from garmin_mcp.server import TOOLS
        
        for tool in TOOLS:
            assert tool.inputSchema is not None
            assert "query" in tool.inputSchema.get("properties", {})
            assert "query" in tool.inputSchema.get("required", [])
    
    def test_tool_names_follow_convention(self) -> None:
        """Tool names should start with 'query_'."""
        from garmin_mcp.server import TOOLS
        
        for tool in TOOLS:
            assert tool.name.startswith("query_")


class TestErrorHandling:
    """Test error handling in server."""
    
    def test_missing_query_parameter(self) -> None:
        """Should handle missing query parameter gracefully."""
        # This would be more thorough with actual MCP server testing
        # For now, just verify the tool structure supports it
        from garmin_mcp.server import _QUERY_INPUT_SCHEMA
        
        assert "query" in _QUERY_INPUT_SCHEMA["required"]
