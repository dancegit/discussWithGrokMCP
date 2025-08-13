# Grok MCP Server

A powerful Model Context Protocol (MCP) server for Claude Code that enables direct interaction with Grok AI. Features both a simple implementation for basic queries and an enhanced version with advanced capabilities.

## 🚀 Features

### Simple Version (`simple_mcp.py`)
- ✅ **Proven Stable** - Lightweight implementation that just works
- 🤖 **Direct Grok Integration** - Simple access to Grok-4 model
- 🔒 **Secure** - Local .env configuration

### Enhanced Version (`enhanced_mcp.py`) - NEW!
- 💬 **Multi-turn Discussions** - Extended conversations with session management
- 📁 **Context-Aware Questions** - Include files and code in your queries
- 🔄 **Session Management** - Save, list, and resume conversations
- 📊 **Resource Access** - View stats, config, and session history
- 🏥 **Health Monitoring** - Check server and API status
- ⚡ **Advanced Features** - Model selection, temperature control, caching
- 🛡️ **Production Ready** - Comprehensive error handling and logging

## 📋 Prerequisites

- Python 3.11+
- X.AI API key from [console.x.ai](https://console.x.ai)
- `uv` package manager (recommended)

## 🔧 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/discussWithGrokMCP.git
cd discussWithGrokMCP
```

2. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

3. **Set up your API key:**
```bash
echo "XAI_API_KEY=your_api_key_here" > .env
```

## 🎯 Quick Start

### Using the Simple Server

For basic Grok queries, use the simple server in your `.mcp.json`:

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

### Using the Enhanced Server (Recommended)

For full features, use the enhanced server in your `.mcp.json`:

```json
{
  "mcpServers": {
    "grok-enhanced": {
      "type": "stdio",
      "command": "/path/to/.local/bin/uv",
      "args": [
        "--project",
        "/absolute/path/to/discussWithGrokMCP",
        "run",
        "/absolute/path/to/discussWithGrokMCP/enhanced_mcp.py"
      ],
      "env": {}
    }
  }
}
```

## 🛠️ Available Tools

### Basic Tool (Both Versions)
- **`grok_ask`** - Ask Grok a question
  ```
  Parameters:
  - question: The question to ask
  - model: Model to use (enhanced only)
  - temperature: Response creativity (enhanced only)
  ```

### Enhanced Tools (Enhanced Version Only)

- **`grok_discuss`** - Start an extended discussion
  ```
  Parameters:
  - topic: Discussion topic
  - context: Optional context
  - max_turns: Number of conversation rounds
  - expert_mode: Include expert perspectives
  ```

- **`grok_ask_with_context`** - Ask with file context
  ```
  Parameters:
  - question: Your question
  - context_files: List of file paths
  - context_type: "code", "docs", or "general"
  ```

- **`grok_list_sessions`** - View conversation history
  ```
  Parameters:
  - status: Filter by status
  - limit: Maximum results
  ```

- **`grok_continue_session`** - Resume a conversation
  ```
  Parameters:
  - session_id: Session to resume
  - message: Your message
  ```

- **`grok_health`** - Check server status
  ```
  Parameters:
  - verbose: Include detailed diagnostics
  ```

## 📚 Resources (Enhanced Version)

The enhanced server exposes these resources:
- `grok://sessions` - Conversation history
- `grok://config` - Current configuration
- `grok://stats` - Usage statistics

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
XAI_API_KEY=your_api_key_here

# Optional (enhanced server)
GROK_MODEL=grok-4-0709
GROK_TEMPERATURE=0.7
GROK_MAX_TOKENS=4096
MCP_LOG_LEVEL=INFO
MCP_ENABLE_STREAMING=false
MCP_ENABLE_CACHING=true
MCP_CACHE_TTL=3600
```

### Available Models

- `grok-4-0709` (default) - Latest and most capable model
- `grok-2-1212` - Previous generation model
- `grok-2-vision` - Vision-capable model
- `grok-beta` - Experimental features

## 🧪 Testing

Run the test suite:

```bash
# All tests
uv run python run_tests.py

# Unit tests only
uv run pytest tests/test_tools.py

# Integration tests
uv run pytest tests/test_integration.py

# Quick test
uv run python test_enhanced.py
```

## 📁 Project Structure

```
discussWithGrokMCP/
├── simple_mcp.py           # Simple, stable server
├── enhanced_mcp.py         # Full-featured server
├── lib/
│   ├── grok_client.py      # Grok API client
│   └── tools/              # Tool implementations
│       ├── ask.py
│       ├── discuss.py
│       ├── session.py
│       ├── context.py
│       └── health.py
├── tests/                  # Test suite
├── .env                    # API key (create this)
└── .mcp.json              # Claude Code config
```

## 🐛 Troubleshooting

### Server fails to start
- Verify your API key in `.env`
- Check that `uv` is installed
- Ensure absolute paths in `.mcp.json`

### Claude Code shows "failed"
- Restart Claude Code after config changes
- Check `simple_mcp.log` or `enhanced_mcp.log`
- Verify Python 3.11+ is installed

### Import errors
- Run `uv sync` to install dependencies
- Check Python version with `python --version`

## 📊 Performance

- **Simple Server**: <500ms response time, minimal memory
- **Enhanced Server**: 
  - Response caching reduces latency
  - Session persistence for context
  - Automatic retry with backoff
  - Token usage tracking

## 🔒 Security

- API keys stored locally in `.env` (never committed)
- No global dependencies
- File access sandboxed to project directory
- Input validation on all parameters

## 🗺️ Roadmap

- [x] Simple MCP implementation
- [x] Enhanced tools and sessions
- [x] Resource management
- [x] Caching and error handling
- [ ] Streaming responses
- [ ] Web UI dashboard
- [ ] Multi-user support

## 📝 Version History

- **v0.8.1** - Full enhanced implementation with 6 tools
- **v0.3.x** - Simple implementation that works with Claude Code
- **v0.2.0** - MCP SDK implementation (deprecated)
- **v0.1.x** - Initial prototypes

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please ensure all tests pass before submitting PRs.

## 💬 Support

For issues or questions, please open an issue on GitHub.

## 🙏 Acknowledgments

Built for use with [Claude Code](https://claude.ai/code) using the Model Context Protocol.