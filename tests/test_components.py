"""
Unit tests for Grok MCP Server components.
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.grok_client import GrokResponse
from lib.storage_manager import StorageManager
from lib.session_manager import SessionManager, Session
from lib.context_analyzer import ContextAnalyzer
from lib.baseline_generator import BaselineGenerator


class TestGrokResponse:
    """Test GrokResponse dataclass."""
    
    def test_response_creation(self):
        """Test creating a GrokResponse."""
        response = GrokResponse(
            content="Test response",
            tokens_used=100,
            model="grok-4-0709",
            timestamp=time.time(),
            streaming=False
        )
        
        assert response.content == "Test response"
        assert response.tokens_used == 100
        assert response.model == "grok-4-0709"
        assert not response.streaming
    
    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = GrokResponse(
            content="Test",
            tokens_used=50,
            model="grok-4-0709",
            timestamp=1234567890.0
        )
        
        result = response.to_dict()
        assert result["content"] == "Test"
        assert result["tokens_used"] == 50
        assert result["timestamp"] == 1234567890.0


class TestStorageManager:
    """Test StorageManager."""
    
    @pytest.mark.asyncio
    async def test_session_save_load(self):
        """Test saving and loading sessions."""
        storage = StorageManager(storage_path="./test_storage")
        
        # Save session
        session_data = {
            "id": "test_123",
            "topic": "Test Topic",
            "status": "active"
        }
        
        path = await storage.save_session("test_123", session_data)
        assert path
        
        # Load session
        loaded = await storage.load_session("test_123")
        assert loaded
        assert loaded["id"] == "test_123"
        assert loaded["topic"] == "Test Topic"
    
    @pytest.mark.asyncio
    async def test_response_save(self):
        """Test saving responses."""
        storage = StorageManager(storage_path="./test_storage")
        
        path = await storage.save_response(
            session_id="test_123",
            response="Test response content",
            iteration=1,
            metadata={"test": True}
        )
        
        assert path
        assert Path(path).exists()
    
    def test_storage_stats(self):
        """Test getting storage statistics."""
        storage = StorageManager(storage_path="./test_storage")
        stats = storage.get_storage_stats()
        
        assert "total_sessions" in stats
        assert "total_responses" in stats
        assert "total_files" in stats


class TestSessionManager:
    """Test SessionManager."""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a session."""
        storage = StorageManager(storage_path="./test_storage")
        manager = SessionManager(storage)
        
        session = await manager.create_session(
            topic="Test Discussion",
            max_iterations=3
        )
        
        assert session.topic == "Test Discussion"
        assert session.max_iterations == 3
        assert session.status == "active"
        assert session.iterations_completed == 0
    
    def test_quality_scoring(self):
        """Test quality score calculation."""
        storage = StorageManager(storage_path="./test_storage")
        manager = SessionManager(storage)
        
        # Test with minimal response
        score1 = manager.calculate_quality_score("Short answer")
        assert 0 <= score1 <= 1
        
        # Test with code
        score2 = manager.calculate_quality_score("```python\ncode here\n```")
        assert score2 >= score1  # Code should score at least as high
        
        # Test with structure
        score3 = manager.calculate_quality_score("# Header\n- List item\n## Subheader")
        assert score3 > 0.3
    
    def test_session_id_generation(self):
        """Test session ID generation."""
        storage = StorageManager(storage_path="./test_storage")
        manager = SessionManager(storage)
        
        id1 = manager.generate_session_id("test")
        id2 = manager.generate_session_id("test")
        
        assert id1 != id2
        assert id1.startswith("test_")
        assert len(id1) > 20


class TestContextAnalyzer:
    """Test ContextAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_question_analysis(self):
        """Test analyzing questions."""
        analyzer = ContextAnalyzer()
        
        # Test implementation question
        analysis = await analyzer.analyze_question(
            "How do I implement a REST API with authentication?"
        )
        
        assert analysis["type"] == "implementation"
        assert "implement" in analysis["keywords"]
        assert analysis["requires_code"] == True
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        """Test extracting entities from questions."""
        analyzer = ContextAnalyzer()
        
        analysis = await analyzer.analyze_question(
            "Fix the bug in UserService.authenticate() method in auth.py"
        )
        
        assert "authenticate" in analysis["entities"]["functions"]
        assert "UserService" in analysis["entities"]["classes"]
        assert "auth.py" in analysis["entities"]["files"]
    
    def test_token_estimation(self):
        """Test token estimation."""
        analyzer = ContextAnalyzer()
        
        text = "This is a test text with approximately 10 words here."
        tokens = analyzer.estimate_tokens(text)
        
        # Rough estimate: 1 token per 4 characters
        expected = len(text) // 4
        assert abs(tokens - expected) < 5


class TestBaselineGenerator:
    """Test BaselineGenerator."""
    
    @pytest.mark.asyncio
    async def test_baseline_generation(self):
        """Test generating baseline documents."""
        generator = BaselineGenerator(token_budget=1000)
        
        analysis = {
            "type": "implementation",
            "keywords": ["api", "authentication"],
            "entities": {},
            "requires_code": True
        }
        
        baseline = await generator.generate(
            topic="Implement REST API",
            analysis=analysis,
            context_items=[],
            use_expert_mode=False
        )
        
        assert "Baseline Document" in baseline
        assert "Executive Summary" in baseline
        assert "Problem Analysis" in baseline
        assert len(baseline) > 100
    
    @pytest.mark.asyncio
    async def test_expert_mode(self):
        """Test baseline generation with expert mode."""
        generator = BaselineGenerator()
        
        analysis = {
            "type": "optimization",
            "keywords": ["performance"],
            "entities": {}
        }
        
        baseline = await generator.generate(
            topic="Optimize database queries",
            analysis=analysis,
            context_items=[],
            use_expert_mode=True
        )
        
        assert "Expert Perspectives" in baseline
        assert "Software Architect" in baseline
        assert "Security Expert" in baseline


def test_imports():
    """Test that all modules can be imported."""
    from lib import (
        GrokClient,
        StorageManager,
        SessionManager,
        ContextAnalyzer,
        BaselineGenerator
    )
    
    assert GrokClient is not None
    assert StorageManager is not None
    assert SessionManager is not None
    assert ContextAnalyzer is not None
    assert BaselineGenerator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])