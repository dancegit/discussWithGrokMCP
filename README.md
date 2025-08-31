# 🤖 Grok MCP Server

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

A powerful Model Context Protocol (MCP) server that enables seamless integration between Claude Code and Grok AI. This project provides both a lightweight implementation for basic queries and an advanced server with enterprise-grade features.

## ✨ Key Features

### 🎯 Two Implementation Options

#### Simple Server (`simple_mcp.py`)
- ✅ **Battle-tested** - Proven stable in production
- 🚀 **Lightweight** - Minimal dependencies, fast startup
- 🔧 **Easy Setup** - Works out of the box

#### Enhanced Server (`enhanced_mcp.py`)
- 💬 **Multi-turn Discussions** - Maintain context across conversations
- 📁 **Context-Aware** - Include files and code in your queries
- 🔄 **Session Management** - Save, resume, and manage conversation history
- 📊 **Resource Monitoring** - Track usage, performance, and health
- ⚡ **Advanced Features** - Model selection, temperature control, response caching
- 🛡️ **Enterprise Ready** - Comprehensive error handling and logging

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- X.AI API key from [console.x.ai](https://console.x.ai)
- [Claude Code](https://claude.ai/code) CLI

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/dancegit/discussWithGrokMCP.git
cd discussWithGrokMCP
```

2. **Install dependencies**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

3. **Configure your API key**
```bash
cp .env.example .env
# Edit .env and add your X.AI API key
```

4. **Configure Claude Code**

Add to your `.mcp.json` file:

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
        "enhanced_mcp.py"
      ],
      "env": {}
    }
  }
}
```

5. **Start using in Claude Code**
```
# Ask a question
grok_ask "What is quantum computing?"

# Start a discussion
grok_discuss "Let's explore machine learning architectures"

# Check health
grok_health
```

## 🛠️ Available Tools

| Tool | Description | Server |
|------|-------------|---------|
| `grok_ask` | Simple Q&A with Grok | Both |
| `grok_discuss` | Multi-turn discussions with file context support | Enhanced |
| `grok_ask_with_context` | Single question with file context | Enhanced |
| `grok_list_sessions` | View conversation history | Enhanced |
| `grok_continue_session` | Resume conversations | Enhanced |
| `grok_health` | Monitor server status | Enhanced |

### File Context with Line Ranges

All context-aware tools (`grok_discuss`, `grok_ask_with_context`, `grok_continue_session`) support specifying specific line ranges from files:

- **String format**: `"path/to/file.py"` - includes the entire file
- **Object format**: `{"path": "file.py", "from": 10, "to": 50}` - includes lines 10-50
- **Mixed**: You can mix both formats in the same `context_files` array

Line numbers are 1-based (matching standard editor line numbers). The `from` and `to` fields are optional - omit them to include the entire file.

### Tool Examples

#### `grok_discuss` with File Context and Line Ranges
```python
# Discuss code with full file context
grok_discuss(
    topic="Review and optimize this implementation",
    context_files=["app.py", "test_app.py"],
    context_type="code",
    max_turns=3,
    expert_mode=True
)

# Discuss specific functions using line ranges
grok_discuss(
    topic="Review the authentication logic",
    context_files=[
        {"path": "auth.py", "from": 45, "to": 120},  # Auth class
        {"path": "middleware.py", "from": 10, "to": 35}  # Auth middleware
    ],
    context_type="code",
    max_turns=2
)

# Mix full files and specific sections
grok_discuss(
    topic="Explain this API design",
    context_files=[
        "api_spec.md",  # Full file
        {"path": "openapi.yaml", "from": 50, "to": 150}  # Specific endpoints
    ],
    context_type="docs",
    max_turns=2
)
```

#### `grok_ask_with_context`
```python
# Ask about specific code sections
grok_ask_with_context(
    question="What design patterns are used here?",
    context_files=[
        {"path": "src/main.py", "from": 100, "to": 200}
    ],
    context_type="code"
)

# Mix full files and line ranges
grok_ask_with_context(
    question="How do these components interact?",
    context_files=[
        "src/config.py",  # Full config file
        {"path": "src/main.py", "from": 1, "to": 50}  # Just imports and setup
    ]
)
```

#### `grok_continue_session` with File Context
```python
# Continue a session with new file context
grok_continue_session(
    session_id="abc-123",
    message="Now let's look at the error handling",
    context_files=[
        {"path": "errors.py", "from": 20, "to": 80}
    ]
)
```

## 📚 Documentation

### Configuration

The server is configured via environment variables in `.env`:

```env
# Required
XAI_API_KEY=your_api_key_here

# Optional
GROK_MODEL=grok-4-0709       # Model selection
GROK_TEMPERATURE=0.7          # Response creativity (0.0-2.0)
MCP_LOG_LEVEL=INFO           # Logging level
MCP_ENABLE_CACHING=true      # Response caching
```

### Available Models

- **`grok-4-0709`** - Latest and most capable (default)
- **`grok-2-1212`** - Previous generation
- **`grok-2-vision`** - Vision-capable model
- **`grok-beta`** - Experimental features

### Resources

The enhanced server exposes MCP resources:

- `grok://sessions` - Conversation history
- `grok://config` - Current configuration
- `grok://stats` - Usage statistics

## 🧪 Testing

```bash
# Run all tests
uv run python run_tests.py

# Unit tests only
uv run pytest tests/test_tools.py -v

# Integration tests
uv run pytest tests/test_integration.py -v

# Quick validation
uv run python test_enhanced.py
```

## 📁 Project Structure

```
discussWithGrokMCP/
├── simple_mcp.py           # Lightweight server
├── enhanced_mcp.py         # Full-featured server
├── lib/
│   ├── grok_client.py      # X.AI API client
│   └── tools/              # Tool implementations
├── tests/                  # Test suite
├── .env.example           # Configuration template
└── .mcp.json              # Claude Code config example
```

## 🔒 Security

- API keys stored locally in `.env` (never committed)
- Sandboxed file access
- Input validation on all parameters
- No sensitive data in logs

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📊 Performance

| Metric | Simple Server | Enhanced Server |
|--------|--------------|-----------------|
| Startup Time | <100ms | <500ms |
| Response Time | <500ms | <500ms (cached: <50ms) |
| Memory Usage | ~50MB | ~100MB |
| Concurrent Sessions | 1 | Unlimited |

## 🐛 Troubleshooting

### Common Issues

**Server fails to start**
- Verify API key in `.env`
- Check Python version: `python --version`
- Ensure absolute paths in `.mcp.json`

**Claude Code shows "failed"**
- Restart Claude Code
- Check logs: `tail -f enhanced_mcp.log`
- Verify `uv` installation

**Import errors**
- Run `uv sync` to install dependencies
- Check virtual environment activation

## 🗺️ Roadmap

- [x] Basic MCP implementation
- [x] Enhanced tools and sessions
- [x] Resource management
- [x] Error handling and caching
- [ ] Streaming responses
- [ ] Web UI dashboard
- [ ] Multi-user support
- [ ] Plugin system

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for [Claude Code](https://claude.ai/code) using the [Model Context Protocol](https://modelcontextprotocol.io)
- Powered by [X.AI's Grok](https://x.ai) models
- Developed with [uv](https://github.com/astral-sh/uv) package manager

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/dancegit/discussWithGrokMCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dancegit/discussWithGrokMCP/discussions)
- **Documentation**: [Wiki](https://github.com/dancegit/discussWithGrokMCP/wiki)

## ⭐ Star History

If you find this project useful, please consider giving it a star!

[![Star History Chart](https://api.star-history.com/svg?repos=dancegit/discussWithGrokMCP&type=Date)](https://star-history.com/#dancegit/discussWithGrokMCP&Date)

---

**Made with ❤️ for the AI development community**