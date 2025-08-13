#!/usr/bin/env python3
"""
Direct test of MCP server components without stdio.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import GrokMCPServer


async def test_direct():
    """Test MCP server methods directly."""
    
    print("🚀 Direct MCP Server Test")
    print("=" * 50)
    
    # Create server instance
    server = GrokMCPServer()
    print("✅ Server created")
    
    # Test initialize
    print("\n1. Testing initialize...")
    result = await server._handle_initialize({})
    print(f"✅ Server info: {result['serverInfo']}")
    
    # Test list tools
    print("\n2. Testing list tools...")
    result = await server._handle_list_tools()
    print(f"✅ Found {len(result['tools'])} tools")
    for tool in result['tools']:
        print(f"   - {tool['name']}")
    
    # Test grok_ask
    print("\n3. Testing grok_ask...")
    result = await server._handle_grok_ask({
        "question": "What is the capital of Japan? One word answer.",
        "include_context": False
    })
    print(f"✅ Response: {result['response']}")
    print(f"   Session: {result['session_id']}")
    print(f"   Tokens: {result['tokens_used']}")
    
    # Test list sessions
    print("\n4. Testing list sessions...")
    result = await server._handle_grok_list_sessions({
        "limit": 5
    })
    print(f"✅ Found {result['total']} sessions")
    for session in result['sessions'][:3]:
        print(f"   - {session['id']}: {session['topic'][:50]}...")
    
    # Test grok_discuss
    print("\n5. Testing grok_discuss...")
    result = await server._handle_grok_discuss({
        "topic": "What are the benefits of async programming in Python? Give 3 bullet points.",
        "max_iterations": 1,
        "use_baseline": False  # Skip baseline for speed
    })
    print(f"✅ Discussion started: {result['session_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Response preview: {result['initial_response'][:200]}...")
    
    print("\n" + "=" * 50)
    print("✅ All direct tests passed!")


if __name__ == "__main__":
    asyncio.run(test_direct())