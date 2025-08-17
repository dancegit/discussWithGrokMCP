#!/usr/bin/env python3
"""
Test script to monitor if the grok_discuss tool is working
"""
import json
import sys

# Create a test request for grok_discuss
request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "grok_discuss",
        "arguments": {
            "topic": "Test discussion monitoring",
            "max_turns": 1,
            "expert_mode": False
        }
    },
    "id": 999
}

# Send to stdout
print(json.dumps(request))
sys.stdout.flush()