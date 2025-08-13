#!/usr/bin/env python3
"""
Test the MCP server through JSON-RPC interface.
"""

import json
import asyncio
import subprocess
import sys
from pathlib import Path


async def test_mcp_server():
    """Test the MCP server with JSON-RPC commands."""
    
    print("🚀 Testing Grok MCP Server")
    print("=" * 50)
    
    # Start the server as a subprocess
    server_process = await asyncio.create_subprocess_exec(
        sys.executable,
        "mcp_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    async def send_request(request):
        """Send a JSON-RPC request and get response."""
        request_str = json.dumps(request) + "\n"
        server_process.stdin.write(request_str.encode())
        await server_process.stdin.drain()
        
        # Read response
        response_line = await server_process.stdout.readline()
        if response_line:
            return json.loads(response_line.decode())
        return None
    
    try:
        # Test 1: Initialize
        print("\n1. Testing initialize...")
        response = await send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        })
        
        if response and "result" in response:
            print(f"✅ Initialize successful")
            print(f"   Server: {response['result']['serverInfo']['name']} v{response['result']['serverInfo']['version']}")
        else:
            print(f"❌ Initialize failed: {response}")
        
        # Send initialized notification
        await send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Test 2: List tools
        print("\n2. Testing tools/list...")
        response = await send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        
        if response and "result" in response:
            tools = response["result"]["tools"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:50]}...")
        else:
            print(f"❌ List tools failed: {response}")
        
        # Test 3: Call grok_ask tool
        print("\n3. Testing grok_ask tool...")
        response = await send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "grok_ask",
                "arguments": {
                    "question": "What is 5 + 3? Answer with just the number.",
                    "include_context": False
                }
            }
        })
        
        if response and "result" in response:
            result = json.loads(response["result"]["content"][0]["text"])
            print(f"✅ Grok answered: {result['response']}")
            print(f"   Tokens used: {result['tokens_used']}")
        else:
            print(f"❌ Tool call failed: {response}")
        
        # Test 4: List resources
        print("\n4. Testing resources/list...")
        response = await send_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {}
        })
        
        if response and "result" in response:
            resources = response["result"]["resources"]
            print(f"✅ Found {len(resources)} resources")
            for res in resources[:3]:  # Show first 3
                print(f"   - {res['name']}")
        else:
            print(f"❌ List resources failed: {response}")
        
        print("\n" + "=" * 50)
        print("✅ All MCP server tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        
    finally:
        # Terminate server
        server_process.terminate()
        await server_process.wait()
        print("Server terminated")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())