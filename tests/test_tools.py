#!/usr/bin/env python3
"""
Unit tests for MCP tools.
"""

import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.tools import AskTool, DiscussTool, SessionManager, ListSessionsTool, ContinueSessionTool, AskWithContextTool, HealthCheckTool
from lib.grok_client import GrokResponse


class TestAskTool:
    """Test the basic ask tool."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Grok client."""
        client = Mock()
        client.model = "grok-code-fast"
        client.temperature = 0.7
        client.ask = AsyncMock(return_value=GrokResponse(
            content="Test response",
            tokens_used=10,
            model="grok-4-0709",
            timestamp=1234567890
        ))
        return client
    
    @pytest.fixture
    def ask_tool(self, mock_client):
        """Create an ask tool with mock client."""
        return AskTool(mock_client)
    
    @pytest.mark.asyncio
    async def test_ask_simple(self, ask_tool, mock_client):
        """Test simple question."""
        result = await ask_tool.execute(question="What is 2+2?")
        assert result == "Test response"
        mock_client.ask.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ask_with_parameters(self, ask_tool, mock_client):
        """Test with custom parameters."""
        result = await ask_tool.execute(
            question="Test question",
            model="grok-beta",
            temperature=0.5
        )
        assert result == "Test response"
    
    def test_tool_metadata(self, ask_tool):
        """Test tool metadata."""
        assert ask_tool.name == "grok_ask"
        assert "question" in ask_tool.description.lower()
        schema = ask_tool.input_schema
        assert schema["type"] == "object"
        assert "question" in schema["properties"]
        assert "question" in schema["required"]


class TestSessionManager:
    """Test session management."""
    
    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a session manager with temp storage."""
        return SessionManager(tmp_path / "sessions")
    
    def test_create_session(self, session_manager):
        """Test creating a session."""
        session_id = session_manager.create_session("Test topic")
        assert session_id
        assert session_id in session_manager.sessions
        assert session_manager.sessions[session_id]["topic"] == "Test topic"
    
    def test_add_message(self, session_manager):
        """Test adding messages to session."""
        session_id = session_manager.create_session("Test")
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi there")
        
        session = session_manager.get_session(session_id)
        assert len(session["messages"]) == 2
        assert session["messages"][0]["role"] == "user"
        assert session["messages"][1]["content"] == "Hi there"
    
    def test_list_sessions(self, session_manager):
        """Test listing sessions."""
        # Create multiple sessions
        id1 = session_manager.create_session("Topic 1")
        id2 = session_manager.create_session("Topic 2")
        session_manager.close_session(id1)
        
        # List all
        all_sessions = session_manager.list_sessions()
        assert len(all_sessions) == 2
        
        # List active only
        active = session_manager.list_sessions(status="active")
        assert len(active) == 1
        assert active[0]["id"] == id2
    
    def test_session_persistence(self, tmp_path):
        """Test that sessions persist to disk."""
        storage = tmp_path / "sessions"
        
        # Create and save session
        manager1 = SessionManager(storage)
        session_id = manager1.create_session("Persistent topic")
        manager1.add_message(session_id, "user", "Test message")
        
        # Load in new manager
        manager2 = SessionManager(storage)
        loaded_session = manager2.get_session(session_id)
        
        assert loaded_session is not None
        assert loaded_session["topic"] == "Persistent topic"
        assert len(loaded_session["messages"]) == 1


class TestDiscussTool:
    """Test the discussion tool."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Grok client."""
        client = Mock()
        client.model = "grok-code-fast"
        client.temperature = 0.7
        client.ask_with_history = AsyncMock(return_value=GrokResponse(
            content="Discussion response",
            tokens_used=20,
            model="grok-4-0709",
            timestamp=1234567890
        ))
        return client
    
    @pytest.fixture
    def discuss_tool(self, mock_client, tmp_path):
        """Create a discuss tool."""
        session_manager = SessionManager(tmp_path / "sessions")
        return DiscussTool(mock_client, session_manager)
    
    @pytest.mark.asyncio
    async def test_discuss_basic(self, discuss_tool):
        """Test basic discussion."""
        result = await discuss_tool.execute(
            topic="Test topic",
            max_turns=2
        )
        
        assert "Test topic" in result
        assert "Session ID:" in result
        assert "Turn 1:" in result
        assert "Discussion response" in result
    
    @pytest.mark.asyncio
    async def test_discuss_with_context(self, discuss_tool):
        """Test discussion with context."""
        result = await discuss_tool.execute(
            topic="Code review",
            context="def add(a, b): return a + b",
            max_turns=1,
            expert_mode=True
        )
        
        assert "Code review" in result
        assert "Session ID:" in result
    
    @pytest.mark.asyncio
    async def test_discuss_with_file_line_ranges(self, discuss_tool, tmp_path):
        """Test discussion with file context using line ranges."""
        # Create a test file
        test_file = tmp_path / "example.py"
        test_file.write_text("""# Line 1: Header comment
def function_a():
    # Line 3
    return "a"

def function_b():
    # Line 7
    return "b"

def function_c():
    # Line 11
    return "c"
""")
        
        result = await discuss_tool.execute(
            topic="Review specific functions",
            context_files=[
                {"path": str(test_file), "from": 6, "to": 9},  # Only function_b
            ],
            context_type="code",
            max_turns=1
        )
        
        assert "Review specific functions" in result
        assert "Session ID:" in result
        assert "Context:" in result


class TestContextTool:
    """Test context-aware asking."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Grok client."""
        client = Mock()
        client.model = "grok-code-fast"
        client.temperature = 0.7
        client.ask = AsyncMock(return_value=GrokResponse(
            content="Context response",
            tokens_used=30,
            model="grok-4-0709",
            timestamp=1234567890
        ))
        return client
    
    @pytest.fixture
    def context_tool(self, mock_client):
        """Create a context tool."""
        return AskWithContextTool(mock_client)
    
    @pytest.mark.asyncio
    async def test_ask_without_context(self, context_tool):
        """Test asking without context files."""
        result = await context_tool.execute(question="Test question")
        assert result == "Context response"
    
    @pytest.mark.asyncio
    async def test_ask_with_file_context(self, context_tool, tmp_path):
        """Test with file context."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'")
        
        result = await context_tool.execute(
            question="What does this function do?",
            context_files=[str(test_file)],
            context_type="code"
        )
        
        assert result == "Context response\n\n[Context: 1 files, 2 lines]"
    
    @pytest.mark.asyncio
    async def test_nonexistent_file(self, context_tool):
        """Test with non-existent file."""
        result = await context_tool.execute(
            question="Test",
            context_files=["/nonexistent/file.txt"]
        )
        
        # Should still work, just with error in context
        assert result.startswith("Context response")
    
    @pytest.mark.asyncio
    async def test_file_with_line_range(self, context_tool, tmp_path):
        """Test with file context and line ranges."""
        # Create a test file with multiple lines
        test_file = tmp_path / "test.py"
        test_file.write_text("""def function1():
    return 1

def function2():
    return 2

def function3():
    return 3

def function4():
    return 4""")
        
        # Test with line range specification
        result = await context_tool.execute(
            question="What does this code do?",
            context_files=[{
                "path": str(test_file),
                "from": 4,
                "to": 6
            }],
            context_type="code"
        )
        
        assert result == "Context response\n\n[Context: 1 files, 3 lines]"
    
    @pytest.mark.asyncio
    async def test_mixed_file_specifications(self, context_tool, tmp_path):
        """Test with mixed string and object file specifications."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("# File 1 content\nline 2\nline 3\nline 4\nline 5")
        
        file2 = tmp_path / "file2.py"
        file2.write_text("# File 2 content\nline 2\nline 3")
        
        result = await context_tool.execute(
            question="Analyze these files",
            context_files=[
                str(file1),  # Simple string path
                {
                    "path": str(file2),
                    "from": 2,
                    "to": 3
                }
            ]
        )
        
        assert result == "Context response\n\n[Context: 2 files, 7 lines]"


class TestSessionTools:
    """Test listing and continuing saved sessions."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        return SessionManager(tmp_path / "sessions")

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, fake_client, session_manager):
        tool = ListSessionsTool(fake_client, session_manager)
        assert await tool.execute() == "No sessions found."

    @pytest.mark.asyncio
    async def test_list_sessions_shows_topics(self, fake_client, session_manager):
        session_manager.create_session("Caching strategy")
        tool = ListSessionsTool(fake_client, session_manager)
        result = await tool.execute()
        assert result.startswith("Found 1 session(s)")
        assert "Topic: Caching strategy" in result

    @pytest.mark.asyncio
    async def test_continue_unknown_session(self, fake_client, session_manager):
        tool = ContinueSessionTool(fake_client, session_manager)
        result = await tool.execute(session_id="missing", message="Hello")
        assert result == "Session missing not found"
        assert fake_client.calls == []

    @pytest.mark.asyncio
    async def test_continue_sends_history_and_persists(self, fake_client, session_manager, tmp_path):
        session_id = session_manager.create_session("Topic")
        session_manager.add_message(session_id, "user", "First question")
        session_manager.add_message(session_id, "assistant", "First answer")

        tool = ContinueSessionTool(fake_client, session_manager)
        result = await tool.execute(session_id=session_id, message="Follow-up")

        assert result == fake_client.reply
        sent = fake_client.calls[0]["messages"]
        assert [m["content"] for m in sent] == ["First question", "First answer", "Follow-up"]

        reloaded = SessionManager(tmp_path / "sessions").get_session(session_id)
        assert [m["role"] for m in reloaded["messages"]] == ["user", "assistant", "user", "assistant"]

    @pytest.mark.asyncio
    async def test_continue_with_context_file(self, fake_client, session_manager, tmp_path):
        source = tmp_path / "module.py"
        source.write_text("def answer():\n    return 42\n")
        session_id = session_manager.create_session("Topic")

        tool = ContinueSessionTool(fake_client, session_manager)
        await tool.execute(session_id=session_id, message="Review this", context_files=[str(source)])

        user_message = fake_client.calls[0]["messages"][-1]["content"]
        assert user_message.startswith("Review this")
        assert "return 42" in user_message
        assert "[Loaded 1 files" in user_message

    @pytest.mark.asyncio
    async def test_continue_uses_model_stored_in_session(self, fake_client, session_manager):
        session_id = session_manager.create_session("Topic", {"model": "grok-4-fast-reasoning"})

        tool = ContinueSessionTool(fake_client, session_manager)
        await tool.execute(session_id=session_id, message="Hi")

        # A separate client is built for the stored model; the default one stays unused.
        assert fake_client.calls == []
        assert session_manager.get_session(session_id)["messages"][-1]["role"] == "assistant"


class TestHealthCheckTool:
    """Test health check tool."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Grok client."""
        client = Mock()
        client.model = "grok-code-fast"
        client.temperature = 0.7
        client.ask = AsyncMock(return_value=GrokResponse(
            content="pong",
            tokens_used=1,
            model="grok-4-0709",
            timestamp=1234567890
        ))
        return client
    
    @pytest.fixture
    def health_tool(self, mock_client):
        """Create a health check tool."""
        return HealthCheckTool(mock_client)
    
    @pytest.mark.asyncio
    async def test_health_check_basic(self, health_tool):
        """Test basic health check."""
        result = await health_tool.execute()
        
        assert "Health Status:" in result
        assert "Server: healthy" in result
        assert "API:" in result
        assert "Uptime:" in result
    
    @pytest.mark.asyncio
    async def test_health_check_verbose(self, health_tool):
        """Test verbose health check."""
        result = await health_tool.execute(verbose=True)
        
        assert "Health Status:" in result
        assert "Diagnostics:" in result
        assert "Version:" in result
        assert "Features:" in result
    
    @pytest.mark.asyncio
    async def test_health_check_api_failure(self, health_tool, mock_client):
        """Test health check with API failure."""
        mock_client.ask.side_effect = Exception("API error")
        
        result = await health_tool.execute()
        
        assert "Health Status:" in result
        assert "API: disconnected" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])