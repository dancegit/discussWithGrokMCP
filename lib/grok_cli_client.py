"""
Grok CLI client - runs prompts through the official `grok` CLI in headless mode.

This lets the server use a signed-in Grok account (`grok login`, OAuth) instead of an
XAI_API_KEY. Requests go through xAI's own client, which also refreshes the OAuth
token, so this module never reads ~/.grok/auth.json itself.

The CLI is an agent with file, shell and web tools, and context files sent through
this server are untrusted input. Every run is therefore locked down in layers:
  1. built-in tools removed (allowlist of a non-existent tool + explicit denylist),
     subagents and plan mode off, permission mode dontAsk with no allow rules loaded;
  2. `--sandbox strict`: kernel-enforced (Landlock/seccomp on Linux) reads limited to an
     empty temp working dir, system paths and ~/.grok, and no child network;
  3. an empty temporary HOME (GROK_HOME still points at the real ~/.grok for the login)
     plus Claude/Cursor compatibility scanning off, so nothing from the user's ~/.claude
     or ~/.cursor - instructions, permission rules, agents, skills, hooks, MCP servers -
     is loaded. Only xAI's built-in agents and bundled skills remain.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from typing import Dict, List, Optional

from .grok_client import GrokResponse

logger = logging.getLogger(__name__)

# Built-in tool IDs removed from every run. The sandbox is the backstop for any tool a
# newer CLI adds; enter/exit_plan_mode stay because the CLI requires them together.
DISALLOWED_TOOLS = ",".join([
    "run_terminal_cmd", "read_file", "write_file", "write", "search_replace", "list_dir",
    "grep", "web_search", "web_fetch", "use_tool", "search_tool", "todo_write",
    "ask_user_question", "send_subagent_message", "get_command_or_subagent_output",
    "kill_command_or_subagent", "update_goal", "scheduler_create", "monitor", "workflow",
    "send_feedback", "image_gen", "image_edit", "image_to_video", "reference_to_video",
    "Agent",
])

LOCKDOWN_ARGS = [
    "--tools", "no_tools",  # allowlist naming no real tool
    "--disallowed-tools", DISALLOWED_TOOLS,
    "--permission-mode", "dontAsk",
    "--no-subagents",
    "--no-plan",
    "--sandbox", "strict",
    "--max-turns", "2",
    "--no-auto-update",
    "--verbatim",
]

# Steers the model away from tool calls it cannot make, so it answers in one turn
BASE_RULES = (
    "You are answering through an API bridge. You have no tools and no file, shell or "
    "network access. Answer directly using only the text in the prompt; any files you "
    "need are already included in it."
)

# Stop the CLI from importing the user's Claude Code / Cursor setup into the prompt
ISOLATION_ENV = {
    f"GROK_{vendor}_{kind}_ENABLED": "false"
    for vendor in ("CLAUDE", "CURSOR")
    for kind in ("AGENTS", "RULES", "SKILLS", "HOOKS", "MCPS")
}


class GrokCliError(RuntimeError):
    """Raised when the grok CLI fails or returns an error object."""


class GrokCliClient:
    """Drop-in replacement for GrokClient that shells out to `grok -p`."""

    _available_models: Optional[List[str]] = None

    def __init__(
        self,
        model: str = "grok-code-fast",
        temperature: float = 0.7,
        binary: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """Initialize the CLI client.

        Args:
            model: Requested model. Passed to the CLI only if the CLI lists it;
                otherwise GROK_CLI_MODEL or the CLI's default model is used.
            temperature: Kept for interface compatibility (the CLI has no flag for it).
            binary: Path to the grok executable (defaults to GROK_CLI_PATH or PATH lookup).
            timeout: Seconds to wait for one response (defaults to GROK_CLI_TIMEOUT or 300).
        """
        self.binary = binary or os.getenv("GROK_CLI_PATH") or shutil.which("grok")
        if not self.binary:
            raise ValueError("grok CLI not found; install it or set GROK_CLI_PATH")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout or float(os.getenv("GROK_CLI_TIMEOUT", "300"))
        self.total_tokens_used = 0

    @staticmethod
    def isolated_env(home: str) -> Dict[str, str]:
        """Environment for one CLI run: throwaway HOME, real GROK_HOME (for the login)."""
        grok_home = os.getenv("GROK_HOME") or os.path.join(os.path.expanduser("~"), ".grok")
        return {**os.environ, **ISOLATION_ENV, "HOME": home, "GROK_HOME": grok_home}

    async def _run(self, *args: str, cwd: str, timeout: float) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory(prefix="grok-mcp-home-") as home:
            proc = await asyncio.create_subprocess_exec(
                self.binary, *args,
                cwd=cwd,
                stdin=asyncio.subprocess.DEVNULL,
                env=self.isolated_env(home),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
            except BaseException as e:
                # Timeout or cancellation: never leave a grok process running
                proc.kill()
                await proc.wait()
                if isinstance(e, asyncio.TimeoutError):
                    raise GrokCliError(f"grok CLI timed out after {timeout:.0f}s") from None
                raise
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")

    async def list_models(self) -> List[str]:
        """Models the signed-in CLI account can use (cached per process)."""
        if GrokCliClient._available_models is None:
            code, out, err = await self._run("models", cwd=tempfile.gettempdir(), timeout=60)
            if code != 0:
                raise GrokCliError(f"`grok models` failed: {(err or out).strip()[:300]}")
            models = []
            for line in out.splitlines():
                line = line.strip()
                if line[:2] in ("* ", "- "):
                    models.append(line[2:].split()[0])
            GrokCliClient._available_models = models
        return GrokCliClient._available_models

    async def _resolve_model(self, model: str) -> Optional[str]:
        try:
            if model in await self.list_models():
                return model
        except GrokCliError as e:
            logger.warning(f"Could not list grok CLI models: {e}")
        return os.getenv("GROK_CLI_MODEL") or None

    async def check_connection(self) -> bool:
        """Cheap health probe: the CLI is installed and signed in."""
        GrokCliClient._available_models = None
        return bool(await self.list_models())

    async def _complete(self, prompt: str, rules: Optional[str], model: str) -> GrokResponse:
        cli_model = await self._resolve_model(model)
        with tempfile.TemporaryDirectory(prefix="grok-mcp-") as workdir:
            prompt_file = os.path.join(workdir, "prompt.md")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

            args = ["--prompt-file", prompt_file, "--output-format", "json", *LOCKDOWN_ARGS]
            if cli_model:
                args += ["-m", cli_model]
            args += ["--rules", f"{BASE_RULES}\n\n{rules}" if rules else BASE_RULES]

            code, out, err = await self._run(*args, cwd=workdir, timeout=self.timeout)

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict):
            raise GrokCliError(f"grok CLI exited {code}: {(err or out).strip()[:300]}")
        if code != 0 or data.get("type") == "error":
            detail = data.get("message") or data.get("text") or err.strip()[-300:]
            raise GrokCliError(f"grok CLI exited {code}: {detail}" if detail else f"grok CLI exited {code}")

        tokens = data.get("usage", {}).get("total_tokens", 0)
        self.total_tokens_used += tokens
        used_model = next(iter(data.get("modelUsage") or {}), cli_model or "grok-cli-default")
        return GrokResponse(content=data.get("text", ""), tokens_used=tokens,
                            model=used_model, timestamp=time.time())

    async def ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        max_tokens: Optional[int] = None,
    ) -> GrokResponse:
        """Send a single question. `stream` and `max_tokens` are accepted but unused."""
        return await self._complete(prompt, system_prompt, self.model)

    async def ask_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> GrokResponse:
        """Send a conversation; history is replayed as a transcript in one prompt."""
        rules = "\n\n".join(m["content"] for m in messages if m["role"] == "system") or None
        turns = [m for m in messages if m["role"] != "system"]
        if len(turns) == 1:
            prompt = turns[0]["content"]
        else:
            transcript = "\n\n".join(f"### {m['role'].capitalize()}\n{m['content']}" for m in turns)
            prompt = (
                "Below is a conversation so far. Reply as the assistant to the final user "
                f"message only.\n\n{transcript}"
            )
        return await self._complete(prompt, rules, model or self.model)

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_total_tokens_used(self) -> int:
        return self.total_tokens_used

    def reset_token_counter(self) -> None:
        self.total_tokens_used = 0
