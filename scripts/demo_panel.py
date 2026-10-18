#!/usr/bin/env python3
"""
Demo of grok_panel: a preset, a custom (agents/*.md) and an inline agent debate a topic
over two rounds, then the moderator recommends. Each contribution is shortened on screen
so the run fits in a GIF; the full text is in the tool result.

    uv run python scripts/demo_panel.py
"""

import re
import sys
import tempfile
import textwrap
import time
from pathlib import Path

from demo import BOLD, CYAN, DIM, GREEN, RED, RESET, StdioClient, show_call

ARGS = {
    "topic": "Should a 50-person software company try a four-day work week?",
    "agents": [
        "skeptic",
        "economist",
        {"name": "team-lead", "instructions": "You lead a team of eight engineers. You care "
                                              "about delivery, on-call cover and burnout."},
    ],
    "rounds": 2,
    "max_words": 45,
}
SHOWN = {**ARGS, "agents": ["skeptic (preset)", "economist (agents/economist.md)",
                            "team-lead (inline)"]}
LINES_PER_TURN = 2


def wrapped(text: str, width: int = 92) -> list[str]:
    lines = []
    for paragraph in text.splitlines():
        lines.extend(textwrap.wrap(paragraph.strip(), width) if paragraph.strip() else [])
    return lines


def section(synthesis: str, heading: str) -> str:
    match = re.search(rf"#*\s*{heading}\s*\n(.*?)(?:\n#+ |\Z)", synthesis, re.S | re.I)
    return match.group(1).strip() if match else ""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="grok-demo-") as workdir:
        client = StdioClient(cwd=Path(workdir))
        try:
            client.request("initialize", {"protocolVersion": "2024-11-05"})
            print(f"\n{CYAN}{BOLD}→ grok_panel{RESET}")
            for key, value in SHOWN.items():
                shown = ", ".join(value) if isinstance(value, list) else value
                print(f"    {DIM}{key}: {shown}{RESET}")
            started = time.time()
            result = client.call_tool("grok_panel", ARGS)
        finally:
            client.close()

    if result.startswith("Error"):
        print(f"{RED}✗ {textwrap.shorten(result, 200)}{RESET}")
        return 1

    body, _, synthesis = result.partition("### Synthesis")
    for round_text in re.split(r"\n(?=### Round )", body)[1:]:
        header, *turns = round_text.strip().split("\n**")
        print(f"\n{BOLD}{header.strip('# ')}{RESET}")
        for turn in turns:
            name, _, text = turn.partition(":** ")
            lines = wrapped(text, 92 - len(name))
            more = f" {DIM}…{RESET}" if len(lines) > LINES_PER_TURN else ""
            print(f"  {CYAN}{name}:{RESET} " + f"\n  {' ' * (len(name) + 2)}".join(
                lines[:LINES_PER_TURN]) + more)

    recommendation = section(synthesis, "Recommendation") or synthesis.strip()
    print(f"\n{BOLD}Moderator · recommendation{RESET}")
    lines = wrapped(recommendation.split("\nResume with")[0], 94)
    for line in lines[:4]:
        print(f"  {line}")
    if len(lines) > 4:
        print(f"  {DIM}…{RESET}")
    print(f"{GREEN}✓ {time.time() - started:.0f}s · 6 turns + synthesis · "
          f"{DIM}turns shortened for the GIF{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
