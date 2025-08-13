#!/usr/bin/env python3
"""
Simulate Claude Code environment to test MCP server startup.
"""

import subprocess
import os
import sys
import json
import time

def test_mcp_server():
    """Test MCP server startup simulating Claude Code environment."""
    
    # Configuration from .mcp.json
    config = {
        "command": "uv",
        "args": ["run", "python", "/home/per/gitrepos/discussWithGrokMCP/mcp_stdio_server.py"],
        "cwd": "/home/per/gitrepos/discussWithGrokMCP",
        "env": {
            "XAI_API_KEY": os.getenv("XAI_API_KEY", "test_api_key_placeholder"),
            "PYTHONUNBUFFERED": "1"
        }
    }
    
    # Prepare environment
    env = os.environ.copy()
    env.update(config["env"])
    
    # Prepare command
    command = [config["command"]] + config["args"]
    
    print(f"Testing MCP server startup...")
    print(f"Command: {' '.join(command)}")
    print(f"Working directory: {config['cwd']}")
    print(f"Environment additions: {config['env'].keys()}")
    print("-" * 50)
    
    # Start the process
    try:
        process = subprocess.Popen(
            command,
            cwd=config["cwd"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "1.0.0"},
            "id": 1
        }
        
        print("Sending initialize request...")
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        
        # Wait for response with timeout
        import select
        readable, _, _ = select.select([process.stdout], [], [], 5)
        
        if readable:
            response = process.stdout.readline()
            print(f"Response received: {response}")
            
            # Parse and validate response
            try:
                resp_obj = json.loads(response)
                if "result" in resp_obj:
                    print("✅ Server started successfully!")
                    print(f"Server info: {resp_obj['result'].get('serverInfo', {})}")
                else:
                    print("❌ Unexpected response format")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse response: {e}")
        else:
            print("❌ No response received within 5 seconds")
        
        # Check for stderr output
        readable, _, _ = select.select([process.stderr], [], [], 0.1)
        if readable:
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"\nStderr output:\n{stderr_output}")
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=2)
        
    except subprocess.TimeoutExpired:
        print("Process took too long to terminate")
        process.kill()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_server()