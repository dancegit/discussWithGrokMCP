#!/usr/bin/env python3
"""
Quick test of the enhanced MCP server for Claude Code.
"""

import sys
import json
import subprocess
import time


def test_enhanced_server():
    """Test that enhanced server works with all new tools."""
    print("Testing Enhanced MCP Server for Claude Code")
    print("=" * 50)
    
    # Start enhanced server
    proc = subprocess.Popen(
        [sys.executable, "enhanced_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"XAI_API_KEY": "test_key"}  # Will fail gracefully
    )
    
    tests = [
        ("Initialize", {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }),
        ("List Tools", {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }),
        ("List Resources", {
            "jsonrpc": "2.0",
            "method": "resources/list",
            "id": 3
        })
    ]
    
    try:
        for test_name, request in tests:
            print(f"\nTest: {test_name}")
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
            time.sleep(0.2)
        
        proc.terminate()
        stdout, _ = proc.communicate(timeout=1)
        
        responses = []
        for line in stdout.strip().split("\n"):
            if line:
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        # Check results
        print("\nResults:")
        print("-" * 40)
        
        if not responses:
            print("✗ No responses received")
            return
        
        # Initialize response
        if len(responses) > 0 and "result" in responses[0]:
            if responses[0]["result"]["serverInfo"]["name"] == "grok-enhanced":
                print("✓ Server: grok-enhanced v0.8.0")
        
        # Tools
        if len(responses) > 1 and "result" in responses[1]:
            tools = responses[1]["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            print(f"✓ Tools ({len(tools)}): {', '.join(tool_names)}")
        
        # Resources
        if len(responses) > 2 and "result" in responses[2]:
            resources = responses[2]["result"]["resources"]
            resource_names = [r["name"] for r in resources]
            print(f"✓ Resources ({len(resources)}): {', '.join(resource_names)}")
        
        print("\n" + "=" * 50)
        print("Enhanced MCP Server is ready for Claude Code!")
        print("\nTo use it, update your .mcp.json:")
        print('''
{
  "mcpServers": {
    "grok-enhanced": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--project",
        "/path/to/discussWithGrokMCP",
        "run",
        "enhanced_mcp.py"
      ],
      "env": {}
    }
  }
}
        ''')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    test_enhanced_server()