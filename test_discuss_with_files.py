#!/usr/bin/env python3
"""
Test script for the updated grok_discuss tool with file context support.
"""

import json
import sys
import os

# Test request for grok_discuss with file context
def test_discuss_with_files():
    """Test the discuss tool with file context."""
    
    # Create a test file first
    test_file = "test_example.py"
    with open(test_file, 'w') as f:
        f.write("""def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
print(fibonacci(10))
""")
    
    # Create request with file context
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "grok_discuss",
            "arguments": {
                "topic": "Optimizing this recursive Fibonacci implementation",
                "context_files": [test_file],
                "context_type": "code",
                "max_turns": 2,
                "expert_mode": True
            }
        },
        "id": 1
    }
    
    print("Testing grok_discuss with file context:")
    print(json.dumps(request, indent=2))
    print("\nTo test with the enhanced server, pipe this to enhanced_mcp.py")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return request

def test_discuss_multiple_files():
    """Test with multiple files."""
    
    # Create test files
    files = []
    
    # File 1: Main implementation
    file1 = "calculator.py"
    with open(file1, 'w') as f:
        f.write("""class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
""")
    files.append(file1)
    
    # File 2: Tests
    file2 = "test_calculator.py"
    with open(file2, 'w') as f:
        f.write("""import unittest
from calculator import Calculator

class TestCalculator(unittest.TestCase):
    def test_add(self):
        calc = Calculator()
        self.assertEqual(calc.add(2, 3), 5)
""")
    files.append(file2)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "grok_discuss",
            "arguments": {
                "topic": "Review this calculator implementation and suggest improvements",
                "context_files": files,
                "context_type": "code",
                "max_turns": 1,
                "context": "Focus on code quality, testing, and potential edge cases"
            }
        },
        "id": 2
    }
    
    print("\n\nTesting with multiple files:")
    print(json.dumps(request, indent=2))
    
    # Clean up
    for f in files:
        if os.path.exists(f):
            os.remove(f)
    
    return request

if __name__ == "__main__":
    # Run tests
    test_discuss_with_files()
    test_discuss_multiple_files()
    
    print("\n\nTests created. You can now:")
    print("1. Use these with the enhanced MCP server")
    print("2. Call grok_discuss from Claude Code with context_files parameter")