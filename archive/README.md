# Archive

Earlier server implementations, kept for reference only. They are not maintained,
not tested, and not wired into CI. The supported entry point is `enhanced_mcp.py`
in the repository root.

| File | What it was |
|------|-------------|
| `legacy_servers/simple_mcp.py` | Minimal single-tool (`grok_ask`) server |
| `legacy_servers/mcp_server.py` | First JSON-RPC server with storage/baseline managers |
| `legacy_servers/mcp_stdio_server.py` | Stdio variant with extra debug logging |
| `legacy_servers/mcp_sdk_server.py` | Experiment using the official `mcp` Python SDK |
| `legacy_servers/grok_mcp.py` | Smaller SDK-based variant |
| `legacy_servers/server.py` | Early full-featured prototype |

They import from `lib/` and expect to be run from this directory's original
location (the repo root), so moving them back is required to run them.
