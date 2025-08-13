#!/usr/bin/env python3
"""
Integration test for Grok MCP Server components.
Tests actual API connectivity and basic functionality.
"""

import asyncio
import os
import sys
from pathlib import Path
import json
from dotenv import load_dotenv

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    GrokClient,
    StorageManager,
    SessionManager,
    ContextAnalyzer,
    BaselineGenerator,
)

# Load environment variables
load_dotenv()


async def test_grok_client():
    """Test Grok client with actual API."""
    print("\n=== Testing Grok Client ===")
    
    try:
        client = GrokClient()
        print("✓ Grok client initialized with API key")
        
        # Test simple ask
        print("\nTesting simple ask...")
        response = await client.ask(
            prompt="What is 2+2? Please answer with just the number.",
            stream=False
        )
        print(f"Response: {response.content}")
        print(f"Tokens used: {response.tokens_used}")
        print("✓ Simple ask successful")
        
        # Test streaming
        print("\nTesting streaming ask...")
        chunks = []
        async for chunk in client.stream_ask(
            prompt="Count from 1 to 5, one number per line."
        ):
            chunks.append(chunk)
        full_response = "".join(chunks)
        print(f"Streamed response: {full_response}")
        print("✓ Streaming successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Grok client test failed: {e}")
        return False


async def test_storage_manager():
    """Test storage manager."""
    print("\n=== Testing Storage Manager ===")
    
    try:
        storage = StorageManager()
        print("✓ Storage manager initialized")
        
        # Test session save/load
        session_id = "test_session_001"
        session_data = {
            "id": session_id,
            "topic": "Test Topic",
            "status": "active",
            "created": "2024-01-01T00:00:00"
        }
        
        await storage.save_session(session_id, session_data)
        print("✓ Session saved")
        
        loaded = await storage.load_session(session_id)
        assert loaded["id"] == session_id
        print("✓ Session loaded successfully")
        
        # Test response save
        await storage.save_response(
            session_id=session_id,
            response="Test response content",
            iteration=1,
            metadata={"test": True}
        )
        print("✓ Response saved")
        
        # Test listing sessions
        sessions = await storage.list_sessions()
        print(f"✓ Listed {len(sessions)} sessions")
        
        return True
        
    except Exception as e:
        print(f"✗ Storage manager test failed: {e}")
        return False


async def test_session_manager():
    """Test session manager."""
    print("\n=== Testing Session Manager ===")
    
    try:
        storage = StorageManager()
        session_mgr = SessionManager(storage)
        print("✓ Session manager initialized")
        
        # Create session
        session = await session_mgr.create_session(
            topic="Test Discussion",
            max_iterations=3
        )
        print(f"✓ Created session: {session.id}")
        
        # Test quality scoring
        score = session_mgr.calculate_quality_score(
            "This is a test response with # headers and - bullet points"
        )
        print(f"✓ Quality score calculated: {score}")
        
        # Test checkpoint
        checkpoint = await session_mgr.add_checkpoint(session.id)
        print(f"✓ Checkpoint created at: {checkpoint['timestamp']}")
        
        # Test session update
        from lib.grok_client import GrokResponse
        import time
        
        mock_response = GrokResponse(
            content="Test response",
            tokens_used=100,
            model="grok-2-1212",
            timestamp=time.time()
        )
        
        updated = await session_mgr.update_session(
            session_id=session.id,
            response=mock_response,
            iteration_complete=True
        )
        print(f"✓ Session updated, iterations: {updated.iterations_completed}")
        
        return True
        
    except Exception as e:
        print(f"✗ Session manager test failed: {e}")
        return False


async def test_context_analyzer():
    """Test context analyzer."""
    print("\n=== Testing Context Analyzer ===")
    
    try:
        analyzer = ContextAnalyzer()
        print("✓ Context analyzer initialized")
        
        # Test question analysis
        question = "How do I implement a WebSocket server with error handling?"
        analysis = await analyzer.analyze_question(question)
        
        print(f"✓ Question analyzed:")
        print(f"  - Type: {analysis['type']}")
        print(f"  - Keywords: {analysis['keywords'][:5]}")
        print(f"  - Requires code: {analysis['requires_code']}")
        
        # Test context gathering
        context = await analyzer.gather_context(analysis)
        print(f"✓ Gathered {len(context)} context items")
        
        return True
        
    except Exception as e:
        print(f"✗ Context analyzer test failed: {e}")
        return False


async def test_baseline_generator():
    """Test baseline generator."""
    print("\n=== Testing Baseline Generator ===")
    
    try:
        generator = BaselineGenerator()
        print("✓ Baseline generator initialized")
        
        # Create test analysis
        analysis = {
            "type": "implementation",
            "keywords": ["websocket", "server", "error"],
            "entities": {
                "functions": ["handle_connection"],
                "classes": ["WebSocketServer"]
            }
        }
        
        # Generate baseline
        baseline = await generator.generate(
            topic="Implement WebSocket server",
            analysis=analysis,
            context_items=[],
            use_expert_mode=True
        )
        
        print(f"✓ Generated baseline document ({len(baseline)} chars)")
        print(f"  First 200 chars: {baseline[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Baseline generator test failed: {e}")
        return False


async def test_full_workflow():
    """Test a complete workflow."""
    print("\n=== Testing Full Workflow ===")
    
    try:
        # Initialize all components
        client = GrokClient()
        storage = StorageManager()
        session_mgr = SessionManager(storage)
        analyzer = ContextAnalyzer()
        generator = BaselineGenerator()
        
        print("✓ All components initialized")
        
        # Create a test topic
        topic = "What is the capital of France? Give a brief answer."
        
        # Analyze the question
        analysis = await analyzer.analyze_question(topic)
        print(f"✓ Question analyzed: {analysis['type']}")
        
        # Create session
        session = await session_mgr.create_session(
            topic=topic,
            max_iterations=1
        )
        print(f"✓ Session created: {session.id}")
        
        # Generate baseline (simplified)
        baseline = await generator.generate(
            topic=topic,
            analysis=analysis,
            context_items=[],
            use_expert_mode=False
        )
        print(f"✓ Baseline generated: {len(baseline)} chars")
        
        # Save baseline
        baseline_path = await storage.save_baseline(
            session_id=session.id,
            baseline=baseline,
            topic=topic
        )
        print(f"✓ Baseline saved to: {baseline_path}")
        
        # Ask Grok
        print("\n🤖 Asking Grok...")
        response = await client.ask(
            prompt=f"Based on this analysis:\n{baseline[:500]}...\n\nPlease answer: {topic}",
            stream=False
        )
        print(f"Grok response: {response.content}")
        print(f"Tokens used: {response.tokens_used}")
        
        # Update session
        await session_mgr.update_session(
            session_id=session.id,
            response=response,
            iteration_complete=True
        )
        print(f"✓ Session updated")
        
        # Save response
        response_path = await storage.save_response(
            session_id=session.id,
            response=response.content,
            iteration=1,
            metadata={"topic": topic}
        )
        print(f"✓ Response saved to: {response_path}")
        
        # Get session stats
        stats = session_mgr.get_session_stats(session.id)
        print(f"\n✓ Session stats:")
        print(json.dumps(stats, indent=2))
        
        return True
        
    except Exception as e:
        print(f"✗ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Grok MCP Server Integration Tests")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("XAI_API_KEY"):
        print("❌ Error: XAI_API_KEY not found in environment")
        return
    
    print("✓ API key found")
    
    # Run tests
    results = []
    
    # Test individual components
    results.append(("Grok Client", await test_grok_client()))
    results.append(("Storage Manager", await test_storage_manager()))
    results.append(("Session Manager", await test_session_manager()))
    results.append(("Context Analyzer", await test_context_analyzer()))
    results.append(("Baseline Generator", await test_baseline_generator()))
    
    # Test full workflow
    results.append(("Full Workflow", await test_full_workflow()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! The server is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())