"""
Tests for the grok CLI backend, using a fake `grok` executable that records its calls.
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from lib.grok_cli_client import GrokCliClient, GrokCliError
from lib.grok_client import create_client
from lib.tools import AskTool

FAKE_GROK = '''#!{python}
import json, os, sys
args = sys.argv[1:]
mode = os.environ.get("FAKE_GROK_MODE", "ok")
if args[:1] == ["models"]:
    print("You are logged in with grok.com.\\n\\nAvailable models:\\n  * grok-4.7 (default)\\n  - grok-4.6")
    sys.exit(0)
prompt = open(args[args.index("--prompt-file") + 1]).read()
with open(os.environ["FAKE_GROK_LOG"], "a") as log:
    log.write(json.dumps({{"args": args, "prompt": prompt, "cwd": os.getcwd(), "pid": os.getpid(),
                          "env": {{k: v for k, v in os.environ.items() if k.startswith("GROK_") or k == "HOME"}}}}) + "\\n")
if mode == "error":
    print(json.dumps({{"type": "error", "message": "Not signed in"}}))
    sys.exit(1)
if mode == "list":
    print("[]"); sys.exit(0)
if mode == "hang":
    import time; time.sleep(30)
print(json.dumps({{"text": "cli answer", "usage": {{"total_tokens": 123}},
                  "modelUsage": {{"grok-4.7": {{}}}}}}))
'''


@pytest.fixture
def fake_grok(tmp_path, monkeypatch):
    script = tmp_path / "grok"
    script.write_text(FAKE_GROK.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("GROK_CLI_PATH", str(script))
    monkeypatch.setenv("FAKE_GROK_LOG", str(log))
    monkeypatch.delenv("GROK_CLI_MODEL", raising=False)
    GrokCliClient._available_models = None
    yield lambda: [json.loads(line) for line in log.read_text().splitlines()]
    GrokCliClient._available_models = None


def flag(args, name):
    return args[args.index(name) + 1] if name in args else None


class TestBackendSelection:
    def test_auto_uses_api_when_key_set(self, monkeypatch):
        monkeypatch.setenv("GROK_BACKEND", "auto")
        assert type(create_client()).__name__ == "FakeGrokClient"  # patched GrokClient

    def test_auto_uses_cli_without_key(self, fake_grok, monkeypatch):
        monkeypatch.setenv("GROK_BACKEND", "auto")
        monkeypatch.delenv("XAI_API_KEY")
        assert isinstance(create_client(), GrokCliClient)

    def test_explicit_cli_wins_over_key(self, fake_grok, monkeypatch):
        monkeypatch.setenv("GROK_BACKEND", "cli")
        assert isinstance(create_client(), GrokCliClient)

    def test_unknown_backend(self, monkeypatch):
        monkeypatch.setenv("GROK_BACKEND", "carrier-pigeon")
        with pytest.raises(ValueError, match="carrier-pigeon"):
            create_client()

    def test_missing_binary(self, monkeypatch):
        monkeypatch.setenv("GROK_CLI_PATH", "")
        monkeypatch.setenv("PATH", "")
        with pytest.raises(ValueError, match="grok CLI not found"):
            GrokCliClient()


class TestGrokCliClient:
    @pytest.mark.asyncio
    async def test_ask_runs_headless_without_tools(self, fake_grok):
        client = GrokCliClient()
        response = await client.ask("What is MCP?")

        assert response.content == "cli answer"
        assert response.model == "grok-4.7"
        assert response.tokens_used == 123
        assert client.get_total_tokens_used() == 123

        call, = fake_grok()
        assert call["prompt"] == "What is MCP?"
        assert flag(call["args"], "--output-format") == "json"
        assert flag(call["args"], "--sandbox") == "strict"
        assert flag(call["args"], "--permission-mode") == "dontAsk"
        assert flag(call["args"], "--tools") == "no_tools"
        removed = flag(call["args"], "--disallowed-tools").split(",")
        assert {"run_terminal_cmd", "read_file", "grep", "write", "web_fetch", "Agent"} <= set(removed)
        assert {"--no-subagents", "--no-plan"} <= set(call["args"])
        # The user's Claude Code setup must not leak into the prompt
        assert call["env"]["GROK_CLAUDE_AGENTS_ENABLED"] == "false"
        assert call["env"]["GROK_CLAUDE_RULES_ENABLED"] == "false"
        assert call["env"]["GROK_CLAUDE_SKILLS_ENABLED"] == "false"
        # Throwaway HOME hides ~/.claude entirely; GROK_HOME keeps the real login
        assert Path(call["env"]["HOME"]).name.startswith("grok-mcp-home-")
        assert call["env"]["HOME"] != str(Path.home())
        assert call["env"]["GROK_HOME"] == str(Path.home() / ".grok")
        assert flag(call["args"], "--rules").startswith("You are answering through an API bridge")
        # Runs in a throwaway directory, never the server's working directory
        assert Path(call["cwd"]).name.startswith("grok-mcp-")
        assert not Path(call["cwd"]).exists()

    @pytest.mark.asyncio
    async def test_api_only_model_falls_back_to_cli_default(self, fake_grok):
        await GrokCliClient(model="grok-code-fast").ask("hi")
        assert "-m" not in fake_grok()[0]["args"]

    @pytest.mark.asyncio
    async def test_listed_model_is_passed_through(self, fake_grok):
        await GrokCliClient(model="grok-4.6").ask("hi")
        assert flag(fake_grok()[0]["args"], "-m") == "grok-4.6"

    @pytest.mark.asyncio
    async def test_cli_model_override(self, fake_grok, monkeypatch):
        monkeypatch.setenv("GROK_CLI_MODEL", "grok-4.5")
        await GrokCliClient(model="grok-code-fast").ask("hi")
        assert flag(fake_grok()[0]["args"], "-m") == "grok-4.5"

    @pytest.mark.asyncio
    async def test_history_becomes_transcript(self, fake_grok):
        await GrokCliClient().ask_with_history([
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "First?"},
            {"role": "assistant", "content": "One."},
            {"role": "user", "content": "Second?"},
        ])
        call, = fake_grok()
        assert flag(call["args"], "--rules").endswith("\n\nBe terse.")
        prompt = call["prompt"]
        assert prompt.index("First?") < prompt.index("One.") < prompt.index("Second?")
        assert "final user message" in prompt

    @pytest.mark.asyncio
    async def test_error_object_raises(self, fake_grok, monkeypatch):
        monkeypatch.setenv("FAKE_GROK_MODE", "error")
        with pytest.raises(GrokCliError, match="Not signed in"):
            await GrokCliClient().ask("hi")

    @pytest.mark.asyncio
    async def test_tool_reports_cli_error_as_text(self, fake_grok, monkeypatch):
        monkeypatch.setenv("FAKE_GROK_MODE", "error")
        result = await AskTool(GrokCliClient()).execute(question="hi")
        assert result.startswith("Error") and "Not signed in" in result

    @pytest.mark.asyncio
    async def test_non_object_json_is_an_error(self, fake_grok, monkeypatch):
        monkeypatch.setenv("FAKE_GROK_MODE", "list")
        with pytest.raises(GrokCliError, match="exited 0"):
            await GrokCliClient().ask("hi")

    @pytest.mark.asyncio
    async def test_cancellation_kills_the_cli(self, fake_grok, monkeypatch, tmp_path):
        import asyncio
        monkeypatch.setenv("FAKE_GROK_MODE", "hang")
        task = asyncio.create_task(GrokCliClient().ask("hi"))
        while not (tmp_path / "calls.jsonl").exists():
            await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        pid = json.loads((tmp_path / "calls.jsonl").read_text())["pid"]
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

    @pytest.mark.asyncio
    async def test_timeout(self, fake_grok, monkeypatch):
        monkeypatch.setenv("FAKE_GROK_MODE", "hang")
        with pytest.raises(GrokCliError, match="timed out"):
            await GrokCliClient(timeout=1).ask("hi")

    @pytest.mark.asyncio
    async def test_check_connection_uses_models_not_a_prompt(self, fake_grok, tmp_path):
        assert await GrokCliClient().check_connection() is True
        assert not (tmp_path / "calls.jsonl").exists()
