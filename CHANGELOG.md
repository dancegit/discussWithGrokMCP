# Changelog

All notable changes to the Grok MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `enhanced_mcp.py` is the single supported entry point; five other server prototypes moved to `archive/legacy_servers/`.
- README rewritten to describe only verified behaviour.
- `.env.example` now lists exactly the variables the server reads.

### Fixed
- Response cache was checked after the tool had already called Grok, so it never saved an API call and could replace a fresh answer with a stale one. It is now checked first, limited to the stateless tools, and errors are not cached.
- `serverInfo.version` now reports the package version instead of a hard-coded `0.8.0`.
- `lib.session_manager.SessionManager` no longer crashes when constructed outside an event loop.
- Test suite passes on a clean checkout (was 46 passed / 14 failed): the xAI client is faked in `tests/conftest.py`, stale assertions updated.

### Added
- `grok_panel`: a panel of 2-6 agents debates a topic over rounds (independent parallel openings, then rebuttals over the transcript) and a moderator writes the synthesis. Panels persist and resume with a user message.
- Panel demo GIF (`scripts/demo_panel.py`, `docs/demo-panel.tape`); demo topics are general-interest examples.
- Agent personas (`lib/agents.py`): 8 presets (plus example `economist` and `data-engineer` files), Markdown agent files in `agents/` or `GROK_AGENTS_DIR`, and inline `{name, instructions}`; per-agent `model`.
- `grok_discuss` accepts `agent` and `system_prompt`; the persona is stored with the session and reapplied by `grok_continue_session`. `expert_mode` is unchanged.
- `cli` backend (`GROK_BACKEND`): use a signed-in Grok account via the official `grok` CLI instead of an API key. Runs are sandboxed (`--sandbox strict`), tool-less, and run with a throwaway `HOME` so none of the user's Claude/Cursor setup (instructions, permission rules, agents, skills, hooks, MCP servers) loads; live tests verify this against the real CLI.
- `grok_health` probes the backend with `check_connection()` (a model list for the CLI, not a billed prompt) and reports which backend is active.
- Second demo GIF (`scripts/demo_discussion.py`, `docs/demo-discussion.tape`): a discussion started in one server process and resumed from another.
- Demo GIF in the README, recorded with `docs/demo.tape` and shortened with `scripts/squash_gif.py`.
- `scripts/demo.py` stdio demo client and `docs/demo.tape` (VHS) for recording the README demo.
- GitHub Actions CI: pytest on Python 3.11-3.13 and a gitleaks scan of full history.
- Tests for `grok_list_sessions` and `grok_continue_session`.
- `live` pytest marker for tests that call the real xAI API (skipped without `XAI_API_KEY`).

### Removed
- Committed logs, saved session/response JSON, `.bak` files, ad-hoc root test scripts, and shell wrappers with hard-coded home-directory paths.

## [0.1.0] - 2025-08-13

### Added
- Initial release of Grok MCP Server
- Core modules for Grok AI integration:
  - `GrokClient` - X.AI API wrapper with streaming and retry logic
  - `StorageManager` - Local persistence for sessions and responses  
  - `SessionManager` - State tracking with checkpointing and recovery
  - `ContextAnalyzer` - NLP-enhanced intelligent context gathering
  - `BaselineGenerator` - Structured document generation
- MCP protocol implementation with JSON-RPC 2.0
- Three main tools:
  - `grok_ask` - Quick single-turn questions with context
  - `grok_discuss` - Multi-iteration discussions with baselines
  - `grok_list_sessions` - Session management and history
- Comprehensive test suite with integration and unit tests
- Documentation and configuration examples
- Session checkpointing every 60 seconds
- Quality scoring for responses
- Token budget management
- File context analysis with relevance scoring

### Security
- API keys stored securely in .env file
- No global configuration dependencies
- File access sandboxed to project directory

### Tested
- Verified with X.AI Grok-2-1212 model
- All integration tests passing (6/6)
- All unit tests passing (14/14)
- Response generation and storage working
- Session management and recovery functional