#!/usr/bin/env python3
"""
Test script for MCP SDK server implementation.
"""

import asyncio
import json
import subprocess
import time

def test_mcp_server():
    """Test the MCP server with various requests."""
    
    print("Testing MCP SDK Server Implementation")
    print("=" * 50)
    
    # Test command
    command = [
        "/home/per/.local/bin/uv",
        "--directory",
        "/home/per/gitrepos/discussWithGrokMCP",
        "run",
        "--with",
        "mcp",
        "mcp",
        "run",
        "/home/per/gitrepos/discussWithGrokMCP/grok_mcp.py"
    ]
    
    # Test requests
    requests = [
        {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            },
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "initialized"
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
    ]
    
    print(f"Command: {' '.join(command)}")
    print("\nSending test requests...")
    
    try:
        # Start the server process
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                "XAI_API_KEY": os.getenv("XAI_API_KEY", "test_api_key_placeholder")
            }
        )
        
        # Send requests
        for i, request in enumerate(requests, 1):
            print(f"\n{i}. Sending: {request.get('method', 'notification')}")
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            
            # Read response if not a notification
            if "id" in request:
                time.sleep(0.5)  # Give server time to respond
                # Note: In a real test we'd use non-blocking reads
        
        # Give time for responses
        time.sleep(2)
        
        # Terminate the process
        process.terminate()
        
        # Get any output
        stdout, stderr = process.communicate(timeout=2)
        
        print("\n" + "=" * 50)
        print("Server Output:")
        if stdout:
            # Try to parse JSON responses
            for line in stdout.strip().split('\n'):
                if line:
                    try:
                        response = json.loads(line)
                        print(f"\nResponse: {json.dumps(response, indent=2)}")
                    except:
                        print(f"Raw: {line}")
        
        if stderr:
            print(f"\nStderr: {stderr}")
        
        print("\n✅ Test completed")
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("⚠️ Process timeout - killed")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_server()