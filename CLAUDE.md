# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

MCP server that exposes xAI Grok to Claude Code. One supported entry point:
`enhanced_mcp.py` (JSON-RPC 2.0 over stdio). Older prototypes live in `archive/` and are
not maintained. Do not add new entry points.

- `lib/grok_client.py` - async OpenAI-compatible xAI client, retry with backoff
- `lib/tools/` - one module per tool (`ask`, `discuss`, `session`, `context`, `health`),
  `context_loader.py` resolves files/dirs/globs/line ranges, `base.py` is the tool base class
- `lib/session_manager.py`, `storage_manager.py`, `baseline_generator.py`,
  `context_analyzer.py` - used by the archived servers; covered by `tests/test_components.py`
- `scripts/repair_session.py` - fixes sessions saved before model/context settings existed

Tools: `grok_ask`, `grok_ask_with_context`, `grok_discuss`, `grok_continue_session`,
`grok_list_sessions`, `grok_health`. Resources: `grok://sessions`, `grok://config`,
`grok://stats`. Configuration is environment variables; `.env.example` lists every one the
server reads - keep it in sync when adding a variable.

## Development

Python 3.11-3.13 (`.python-version` pins 3.12; 3.14 cannot build the locked pydantic-core).

```bash
uv sync
uv run pytest            # offline suite, xAI client faked
uv run pytest -m live    # real API, needs XAI_API_KEY
```

`tests/conftest.py` replaces `lib.grok_client.GrokClient` with `FakeGrokClient` and sets a
dummy key for every test not marked `live`. New tests must not need network access; use
the `fake_client` fixture. Anything that genuinely calls xAI gets `@pytest.mark.live`.

CI (`.github/workflows/ci.yml`) runs pytest on 3.11/3.12/3.13 and gitleaks over full history.

## Rules

- Never commit `.env`, `.mcp.json`, logs, session JSON, or `*.bak` files (all git-ignored).
- No absolute machine paths in code, scripts, or examples.
- Tool handlers return error strings rather than raising.
- Context files are read with the server's own permissions; there is no path sandbox.
- Add tests for new behaviour and update README.md when tools or settings change.
