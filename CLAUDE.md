# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

MCP server that exposes xAI Grok to Claude Code. One supported entry point:
`enhanced_mcp.py` (JSON-RPC 2.0 over stdio). Older prototypes live in `archive/` and are
not maintained. Do not add new entry points.

- `lib/grok_client.py` - async OpenAI-compatible xAI client, retry with backoff;
  `create_client()` picks the backend from `GROK_BACKEND` (auto/api/cli)
- `lib/grok_cli_client.py` - backend that runs the signed-in `grok` CLI headless. Every
  run is locked down (tools removed, `--sandbox strict`, Claude/Cursor compat scanning off).
  Never loosen `LOCKDOWN_ARGS` / `ISOLATION_ENV` without re-running the live_cli tests.
- `lib/agents.py` - agent personas: presets, `agents/*.md` + `GROK_AGENTS_DIR` files, inline
  specs; used by `grok_panel` and the `agent` param of `grok_discuss`
- `lib/tools/` - one module per tool (`ask`, `discuss`, `panel`, `session`, `context`, `health`),
  `context_loader.py` resolves files/dirs/globs/line ranges, `base.py` is the tool base class
- `lib/session_manager.py`, `storage_manager.py`, `baseline_generator.py`,
  `context_analyzer.py` - used by the archived servers; covered by `tests/test_components.py`
- `scripts/repair_session.py` - fixes sessions saved before model/context settings existed
- `scripts/demo.py`, `scripts/demo_discussion.py`, `scripts/demo_panel.py` - stdio demo clients
  behind the README GIFs; keep their topics general (no personal projects)
  (`docs/*.tape`, post-processed by `scripts/squash_gif.py`)

Tools: `grok_ask`, `grok_ask_with_context`, `grok_discuss`, `grok_panel`, `grok_continue_session`,
`grok_list_sessions`, `grok_health`. Resources: `grok://sessions`, `grok://config`,
`grok://stats`. Configuration is environment variables; `.env.example` lists every one the
server reads - keep it in sync when adding a variable.

## Development

Python 3.11-3.13 (`.python-version` pins 3.12; 3.14 cannot build the locked pydantic-core).

```bash
uv sync
uv run pytest            # offline suite, xAI client faked
uv run pytest -m live    # real API, needs XAI_API_KEY
RUN_GROK_CLI_TESTS=1 uv run pytest -m live_cli   # containment checks on the real grok CLI
```

Construct clients with `create_client()`, never `GrokClient(...)` directly, so the backend
setting is honoured.

`tests/conftest.py` replaces `lib.grok_client.GrokClient` with `FakeGrokClient` and sets a
dummy key for every test not marked `live`. New tests must not need network access; use
the `fake_client` fixture. Anything that genuinely calls xAI gets `@pytest.mark.live`.

CI (`.github/workflows/ci.yml`) runs pytest on 3.11/3.12/3.13 and gitleaks over full history.

## Rules

- Never commit `.env`, `.mcp.json`, logs, session JSON, or `*.bak` files (all git-ignored).
- No absolute machine paths in code, scripts, or examples.
- Tool handlers return error strings rather than raising.
- Context files are read with the server's own permissions; there is no path sandbox on
  the server side. Treat their contents as untrusted when they reach the model.
- Add tests for new behaviour and update README.md when tools or settings change.
