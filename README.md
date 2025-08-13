# Grok MCP Server

A standalone Model Context Protocol (MCP) server for Claude Code that enables direct interaction with Grok AI. Simple, reliable implementation that works with Claude Code CLI.

## Installation in Claude Code

### Project-Specific Configuration (Recommended)

Create a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "grok": {
      "type": "stdio",
      "command": "/path/to/.local/bin/uv",
      "args": [
        "--project",
        "/absolute/path/to/discussWithGrokMCP",
        "run",
        "/absolute/path/to/discussWithGrokMCP/simple_mcp.py"
      ],
      "env": {}
    }
  }
}
```

### Global Configuration

Add to your Claude Code configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "grok": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--project",
        "/absolute/path/to/discussWithGrokMCP",
        "run",
        "/absolute/path/to/discussWithGrokMCP/simple_mcp.py"
      ],
      "env": {}
    }
  }
}
```

### Using Python Directly

If you don't have `uv` installed, you can use Python directly:

```json
{
  "mcpServers": {
    "grok": {
      "type": "stdio",
      "command": "python",
      "args": ["/absolute/path/to/discussWithGrokMCP/simple_mcp.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/discussWithGrokMCP"
      }
    }
  }
}
```

### Configuration Options

- **type**: Must be "stdio" for Claude Code compatibility
- **command**: The executable to run (`uv` recommended, or `python`/`python3`)
- **args**: Command arguments to start the server
- **env**: Environment variables (API key is loaded from local .env file)

### Getting Your API Key

1. Visit [console.x.ai](https://console.x.ai)
2. Create an account or sign in
3. Generate an API key
4. Add it to `.env` file in the repository root:
   ```bash
   echo "XAI_API_KEY=your_api_key_here" > .env
   ```

### Verifying Installation

After adding the configuration and restarting Claude Code, you should see the Grok MCP server available with:
- `grok_ask` - Ask Grok a question

## Features

- 🤖 **Direct Grok Integration** - Simple access to Grok-2-1212 model via X.AI API
- 🚀 **Lightweight Implementation** - Minimal, reliable MCP server that just works
- 🔒 **Secure & Standalone** - Local .env configuration, no global dependencies
- ✅ **Claude Code Compatible** - Tested and working with Claude Code CLI

## Quick Start

### Prerequisites

- Python 3.11+
- X.AI API key from [console.x.ai](https://console.x.ai)
- `uv` package manager (recommended) or pip

### Installation Steps

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/discussWithGrokMCP.git
cd discussWithGrokMCP
```

2. **Set up your API key** (choose one method):

   **Option A: Using .env file (for testing)**
   ```bash
   echo "XAI_API_KEY=your_xai_api_key_here" > .env
   ```

   **Option B: In MCP configuration (for Claude Code)**
   Add the key directly in your MCP configuration (see Installation in Claude Code above)

3. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

4. **Configure Claude Code** (see Installation in Claude Code section above)

5. **Restart Claude Code** to load the MCP server

### Running Tests

Test the installation:
```bash
# Test the MCP server
uv run python test_simple.py

# Quick test with direct input
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | uv run ./simple_mcp.py
```

## MCP Tools

### `grok_ask`
Ask Grok a question directly.

**Parameters:**
- `question` (string, required): The question to ask

**Example:**
```json
{
  "name": "grok_ask",
  "arguments": {
    "question": "How do I implement WebSocket in Python?"
  }
}
```

## Project Structure

```
discussWithGrokMCP/
├── lib/                        # Core modules
│   └── grok_client.py         # X.AI API wrapper
├── simple_mcp.py              # MCP server implementation
├── test_simple.py             # Test script
├── simple_mcp.log             # Server logs
├── .env                       # API configuration
└── pyproject.toml             # Dependencies
```

## Architecture

The server (`simple_mcp.py`) implements a minimal MCP server that:
1. Handles MCP protocol initialization 
2. Lists available tools (currently just `grok_ask`)
3. Executes tool calls by forwarding questions to the Grok API
4. Returns responses in MCP-compatible format

### Data Flow

1. **MCP Request** → Claude Code sends JSON-RPC request via stdio
2. **Request Handling** → Server parses and routes the request
3. **API Communication** → For tool calls, forwards to Grok API
4. **Response** → Returns JSON-RPC response to Claude Code

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
XAI_API_KEY=your_api_key_here

# Optional (defaults shown)
GROK_MODEL=grok-2-1212
GROK_TEMPERATURE=0.7
```

## Testing

Test the server directly:

```bash
# Test initialization
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | uv run ./simple_mcp.py

# Test with the test script
uv run python test_simple.py
```

## Security

- API keys stored securely in `.env` file (not in MCP configuration)
- No global configuration dependencies
- Simple, auditable codebase

## Troubleshooting

### Server fails to start
- Check that your API key is correctly set in `.env` file
- Verify key at [console.x.ai](https://console.x.ai)
- Ensure `uv` is installed and in your PATH

### Claude Code shows "failed"
- Restart Claude Code after configuration changes
- Check paths in `.mcp.json` are absolute and correct
- Review `simple_mcp.log` for error messages

### Import Errors
- Install dependencies: `uv sync`
- Ensure Python 3.11+ is installed

## Version History

- **v0.3.0** - Simplified implementation (`simple_mcp.py`) that works reliably with Claude Code CLI
- **v0.2.0** - MCP SDK-based implementation (had compatibility issues with Claude Code)
- **v0.1.x** - Initial custom stdio implementations

## License

MIT

## Contributing

Contributions welcome! Please ensure all tests pass before submitting PRs.

## Support

For issues or questions, please open an issue on GitHub.