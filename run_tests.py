#!/usr/bin/env python3
"""
Test runner for the enhanced MCP server.
Runs all tests and validates the implementation.
"""

import sys
import subprocess
from pathlib import Path
import json


def run_unit_tests():
    """Run unit tests."""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_tools.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests."""
    print("=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)
    
    # Note: Integration tests need mocking to avoid real API calls
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_integration.py", "-v", "--tb=short", "-k", "not server_process"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0


def test_backward_compatibility():
    """Test that simple_mcp.py still works."""
    print("=" * 60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("=" * 60)
    
    # Test simple_mcp.py by calling it directly with echo
    import os
    test_cmd = 'echo \'{"jsonrpc":"2.0","method":"tools/list","id":1}\' | timeout 1 ' + sys.executable + ' simple_mcp.py 2>/dev/null'
    
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        response = json.loads(line)
                        if "result" in response and "tools" in response["result"]:
                            tools = response["result"]["tools"]
                            if any(t["name"] == "grok_ask" for t in tools):
                                print("✓ simple_mcp.py still works - grok_ask tool found")
                                return True
                    except json.JSONDecodeError:
                        continue
        
        print("✗ simple_mcp.py compatibility issue")
        return False
        
    except Exception as e:
        print(f"✗ Error testing simple_mcp.py: {e}")
        return False


def test_enhanced_server():
    """Test the enhanced server."""
    print("=" * 60)
    print("TESTING ENHANCED SERVER")
    print("=" * 60)
    
    # Test enhanced_mcp.py
    test_requests = [
        {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
    ]
    
    proc = subprocess.Popen(
        [sys.executable, "enhanced_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent,
        env={"XAI_API_KEY": "test_key"}  # Mock key for testing
    )
    
    try:
        # Send requests
        for request in test_requests:
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
        
        # Wait for responses
        import time
        time.sleep(1)
        
        proc.terminate()
        stdout, _ = proc.communicate(timeout=1)
        
        if stdout:
            lines = stdout.strip().split("\n")
            responses = [json.loads(line) for line in lines if line]
            
            # Check initialization
            if len(responses) >= 1:
                init_response = responses[0]
                if init_response.get("result", {}).get("serverInfo", {}).get("name") == "grok-enhanced":
                    print("✓ Enhanced server initialization successful")
                    
                    # Check tools
                    if len(responses) >= 2:
                        tools_response = responses[1]
                        tools = tools_response.get("result", {}).get("tools", [])
                        expected_tools = ["grok_ask", "grok_discuss", "grok_health", "grok_list_sessions"]
                        
                        found_tools = [t["name"] for t in tools]
                        for expected in expected_tools:
                            if expected in found_tools:
                                print(f"  ✓ Tool '{expected}' found")
                            else:
                                print(f"  ✗ Tool '{expected}' missing")
                        
                        return len(set(expected_tools) & set(found_tools)) == len(expected_tools)
        
        print("✗ Enhanced server test failed")
        return False
        
    except Exception as e:
        print(f"✗ Error testing enhanced server: {e}")
        return False
    finally:
        proc.terminate()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ENHANCED MCP SERVER TEST SUITE")
    print("=" * 60 + "\n")
    
    results = {
        "Unit Tests": run_unit_tests(),
        "Integration Tests": run_integration_tests(),
        "Backward Compatibility": test_backward_compatibility(),
        "Enhanced Server": test_enhanced_server()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("The enhanced MCP server is ready for use.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("Please review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())