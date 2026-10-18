#!/usr/bin/env python3
"""
Drive enhanced_mcp.py over stdio exactly as an MCP client (e.g. Claude Code) would,
and print each exchange. Used to record the README demo; needs XAI_API_KEY in .env.

    uv run python scripts/demo.py
"""

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIM, BOLD, CYAN, GREEN, RED, RESET = (
    "\033[2m", "\033[1m", "\033[36m", "\033[32m", "\033[31m", "\033[0m"
)


class StdioClient:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "enhanced_mcp.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, cwd=ROOT,
        )
        self.next_id = 1

    def request(self, method: str, params: dict | None = None) -> dict:
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}}
        self.next_id += 1
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        response = json.loads(self.proc.stdout.readline())
        if "error" in response:
            raise RuntimeError(response["error"]["message"])
        return response["result"]

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        return result["content"][0]["text"]

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def show_call(name: str, arguments: dict) -> None:
    print(f"\n{CYAN}{BOLD}→ {name}{RESET}")
    for key, value in arguments.items():
        shown = value if isinstance(value, str) else json.dumps(value)
        print(f"    {DIM}{key}: {shown}{RESET}")


def show_answer(text: str, started: float, max_lines: int = 14) -> bool:
    if text.startswith("Error"):
        print(f"{RED}✗ {textwrap.shorten(text, 200)}{RESET}")
        return False
    lines = []
    for paragraph in text.strip().splitlines():
        lines.extend(textwrap.wrap(paragraph, 88) or [""])
    for line in lines[:max_lines]:
        print(f"  {line}")
    if len(lines) > max_lines:
        print(f"  {DIM}… {len(lines) - max_lines} more lines{RESET}")
    print(f"{GREEN}✓ {time.time() - started:.1f}s{RESET}")
    return True


def main() -> int:
    client = StdioClient()
    ok = True
    try:
        info = client.request("initialize", {"protocolVersion": "2024-11-05"})["serverInfo"]
        tools = [t["name"] for t in client.request("tools/list")["tools"]]
        print(f"{BOLD}{info['name']} {info['version']}{RESET} {DIM}· {len(tools)} tools{RESET}")
        for line in textwrap.wrap(", ".join(tools), 96):
            print(f"  {DIM}{line}{RESET}")

        args = {"question": "In one sentence: what is the Model Context Protocol?"}
        show_call("grok_ask", args)
        started = time.time()
        answer = client.call_tool("grok_ask", args)
        ok &= show_answer(answer, started)

        print(f"\n{CYAN}{BOLD}→ grok_ask{RESET} {DIM}(same question again){RESET}")
        started = time.time()
        cached = client.call_tool("grok_ask", args) == answer
        print(f"{GREEN}✓ {time.time() - started:.2f}s · served from cache{RESET}" if cached
              else f"{RED}✗ cache miss{RESET}")
        ok &= cached

        args = {
            "question": "Summarise what this function does in 3 short bullet points.",
            "context_files": [{"path": "lib/tools/context_loader.py", "from": 120, "to": 196}],
            "context_type": "code",
        }
        show_call("grok_ask_with_context", args)
        started = time.time()
        ok &= show_answer(client.call_tool("grok_ask_with_context", args), started)
    finally:
        client.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
