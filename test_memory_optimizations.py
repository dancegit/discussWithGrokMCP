#!/usr/bin/env python3
"""
Test script for memory optimizations in the MCP server.
Tests the various memory management features we've implemented.
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.storage_manager import StorageManager
from lib.session_manager import SessionManager
from lib.tools.discuss import DiscussTool
from lib import GrokClient

# Set test environment variables
os.environ['MAX_SESSION_SIZE_MB'] = '1'  # 1 MB limit for testing
os.environ['MAX_ACTIVE_SESSIONS'] = '3'  # Only 3 sessions in memory
os.environ['MAX_CACHE_SIZE_MB'] = '1'  # 1 MB cache
os.environ['MAX_FILE_SIZE_MB'] = '1'  # 1 MB file limit
os.environ['MAX_CONTEXT_LINES_PER_FILE'] = '10'  # 10 lines max
os.environ['SESSION_INACTIVITY_TIMEOUT_HOURS'] = '0.001'  # Very short for testing

async def test_session_size_limit():
    """Test that large sessions are not loaded."""
    print("\n=== Testing Session Size Limit ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageManager(tmpdir)
        
        # Create a large session file (>1MB)
        large_session = {
            "id": "test_large",
            "data": "x" * (2 * 1024 * 1024)  # 2MB of data
        }
        
        session_path = Path(tmpdir) / "sessions" / "test_large.json"
        session_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(session_path, 'w') as f:
            json.dump(large_session, f)
        
        # Try to load it
        result = await storage.load_session("test_large")
        
        if result is None:
            print("✅ Large session correctly rejected")
        else:
            print("❌ Large session was loaded (should have been rejected)")

async def test_lru_eviction():
    """Test that LRU eviction works for sessions."""
    print("\n=== Testing LRU Session Eviction ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageManager(tmpdir)
        session_manager = SessionManager(storage)
        
        # Create 4 sessions (max is 3)
        sessions = []
        for i in range(4):
            session = await session_manager.create_session(f"Test topic {i}")
            sessions.append(session.id)
            print(f"Created session {i+1}: {session.id}")
            await asyncio.sleep(0.1)  # Small delay to ensure different timestamps
        
        # Check that only 3 sessions are in memory
        active_count = len(session_manager.active_sessions)
        print(f"Active sessions in memory: {active_count}")
        
        if active_count == 3:
            print("✅ LRU eviction working - only 3 sessions in memory")
            
            # Check that the first session was evicted
            if sessions[0] not in session_manager.active_sessions:
                print("✅ Oldest session was evicted")
            else:
                print("❌ Oldest session still in memory")
        else:
            print(f"❌ Expected 3 sessions in memory, got {active_count}")

async def test_file_streaming():
    """Test that file streaming doesn't load entire file into memory."""
    print("\n=== Testing File Streaming ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file with many lines
        test_file = Path(tmpdir) / "test.txt"
        with open(test_file, 'w') as f:
            for i in range(1000):
                f.write(f"Line {i}: {'x' * 100}\n")  # ~100KB file
        
        # Mock GrokClient
        class MockGrokClient:
            async def ask_with_history(self, **kwargs):
                class Response:
                    content = "Test response"
                    tokens_used = 10
                    timestamp = datetime.now().isoformat()
                return Response()
        
        # Create discuss tool
        storage = StorageManager(tmpdir)
        session_manager = SessionManager(storage)
        grok_client = MockGrokClient()
        discuss_tool = DiscussTool(grok_client, session_manager)
        
        # Load context with file
        context = discuss_tool._load_context_files([str(test_file)], max_lines=10)
        
        # Check that only 10 lines were loaded
        lines_loaded = context.count('\n')
        print(f"Lines loaded: {lines_loaded}")
        
        if lines_loaded < 20:  # Should be around 10-15 with headers
            print("✅ File streaming working - limited lines loaded")
        else:
            print(f"❌ Too many lines loaded: {lines_loaded}")

async def test_cache_size_management():
    """Test that cache size is managed properly."""
    print("\n=== Testing Cache Size Management ===")
    
    # Import the enhanced server to test cache
    from enhanced_mcp import EnhancedMCPServer
    
    server = EnhancedMCPServer()
    
    # Add items to cache until it should evict
    for i in range(10):
        key = f"test_key_{i}"
        # Create a large value (~200KB each)
        value = f"Test value {i}: {'x' * 200000}"
        server._add_to_cache(key, value)
    
    # Check cache size
    from enhanced_mcp import cache, cache_size
    
    print(f"Cache entries: {len(cache)}")
    print(f"Cache size: {cache_size / 1024:.1f} KB")
    
    # Should have evicted some entries to stay under 1MB
    if cache_size < 1.2 * 1024 * 1024:  # Allow 20% margin
        print("✅ Cache size management working")
    else:
        print(f"❌ Cache too large: {cache_size / 1024 / 1024:.2f} MB")

async def test_cleanup_task():
    """Test that cleanup task removes inactive sessions."""
    print("\n=== Testing Cleanup Task ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageManager(tmpdir)
        session_manager = SessionManager(storage)
        
        # Create a session
        session = await session_manager.create_session("Test cleanup")
        session_id = session.id
        
        # Mark it as inactive
        session_manager.session_access_times[session_id] = datetime(2020, 1, 1)
        session_manager.active_sessions[session_id].status = "completed"
        
        print(f"Created session: {session_id}")
        print(f"Sessions before cleanup: {len(session_manager.active_sessions)}")
        
        # Run cleanup
        await session_manager.cleanup_inactive_sessions()
        
        print(f"Sessions after cleanup: {len(session_manager.active_sessions)}")
        
        if session_id not in session_manager.active_sessions:
            print("✅ Inactive session was cleaned up")
        else:
            print("❌ Inactive session still in memory")

async def main():
    """Run all tests."""
    print("=" * 50)
    print("Memory Optimization Tests")
    print("=" * 50)
    
    try:
        await test_session_size_limit()
        await test_lru_eviction()
        await test_file_streaming()
        await test_cache_size_management()
        await test_cleanup_task()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())