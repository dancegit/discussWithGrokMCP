#!/usr/bin/env python3
"""
Monitor the MCP server log for errors and activity.
"""

import time
import sys
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent / "simple_mcp.log"

def tail_file(file_path, last_pos=0):
    """Read new lines from file."""
    with open(file_path, 'r') as f:
        f.seek(last_pos)
        new_lines = f.readlines()
        new_pos = f.tell()
    return new_lines, new_pos

def analyze_line(line):
    """Analyze a log line for issues."""
    issues = []
    
    # Check for errors
    if "ERROR" in line:
        issues.append(("ERROR", line.strip()))
    elif "WARNING" in line:
        issues.append(("WARNING", line.strip()))
    elif "Exception" in line or "Traceback" in line:
        issues.append(("EXCEPTION", line.strip()))
    elif "Failed" in line or "failed" in line:
        issues.append(("FAILURE", line.strip()))
    
    # Track activity
    if "Request:" in line:
        print(f"✓ Request received: {line.strip()}")
    elif "Response:" in line and "error" not in line.lower():
        print(f"✓ Response sent successfully")
    elif "error" in line.lower() and "Response:" in line:
        issues.append(("RESPONSE_ERROR", line.strip()))
    
    return issues

def main():
    print(f"Monitoring {LOG_FILE}")
    print("=" * 50)
    
    # Start from current end of file
    last_pos = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
    print(f"Starting from position {last_pos}")
    
    issues_found = []
    
    try:
        while True:
            if LOG_FILE.exists():
                new_lines, last_pos = tail_file(LOG_FILE, last_pos)
                
                for line in new_lines:
                    issues = analyze_line(line)
                    if issues:
                        for level, msg in issues:
                            print(f"\n⚠️  {level}: {msg}")
                            issues_found.append((datetime.now(), level, msg))
            
            time.sleep(0.5)  # Check every 500ms
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        if issues_found:
            print(f"\nFound {len(issues_found)} issues:")
            for timestamp, level, msg in issues_found[-10:]:  # Show last 10
                print(f"  [{timestamp.strftime('%H:%M:%S')}] {level}: {msg[:100]}")
        else:
            print("No issues found during monitoring.")

if __name__ == "__main__":
    main()