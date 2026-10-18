#!/usr/bin/env python3
"""
Demo of a discussion that survives a server restart: start it with grok_discuss, stop the
server, then find it with grok_list_sessions and resume it with grok_continue_session from
a fresh server process. Sessions go to a throwaway directory.

    uv run python scripts/demo_discussion.py
"""

import re
import sys
import tempfile
import time
from pathlib import Path

from demo import BOLD, DIM, GREEN, RED, RESET, StdioClient, show_answer, show_call

TOPIC = "Roundabout or traffic lights for a busy four-way junction? At most 3 sentences."
FOLLOW_UP = "Given that choice, name the 3 things the city should measure in year one. One line."


def banner(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")


def turn_text(result: str) -> str:
    """The first turn of a grok_discuss result, without its headers and footer."""
    match = re.search(r"Turn 1:\n(.*?)(?:\n\nFollow-up:|\n={10,}|\Z)", result, re.S)
    return match.group(1).strip() if match else result


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory(prefix="grok-demo-") as workdir:
        banner("① server process 1")
        client = StdioClient(cwd=Path(workdir))
        try:
            client.request("initialize", {"protocolVersion": "2024-11-05"})
            args = {"topic": TOPIC, "max_turns": 2, "turns_per_page": 1}
            show_call("grok_discuss", args)
            started = time.time()
            result = client.call_tool("grok_discuss", args)
            ok &= show_answer(turn_text(result), started, max_lines=6)
            session_id = re.search(r"Session ID: (\S+)", result).group(1)
            print(f"  {DIM}session {session_id[:8]}… saved to sessions/{RESET}")
        finally:
            client.close()
        print(f"{DIM}  server stopped{RESET}")

        banner("② server process 2 (fresh, same sessions directory)")
        client = StdioClient(cwd=Path(workdir))
        try:
            client.request("initialize", {"protocolVersion": "2024-11-05"})
            show_call("grok_list_sessions", {})
            listing = client.call_tool("grok_list_sessions", {})
            for line in listing.splitlines():
                if line.startswith(("ID:", "Topic:", "Messages:")):
                    print(f"  {line[:96]}")
            found = session_id in listing
            print(f"{GREEN}✓ session found{RESET}" if found else f"{RED}✗ session missing{RESET}")
            ok &= found

            args = {"session_id": session_id, "message": FOLLOW_UP}
            show_call("grok_continue_session", {**args, "session_id": session_id[:8] + "…"})
            started = time.time()
            ok &= show_answer(client.call_tool("grok_continue_session", args), started, max_lines=6)
        finally:
            client.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
