# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server implementation for intelligent discussions with Grok AI. The project offers two server implementations:

1. **Simple Server** (`simple_mcp.py`) - Lightweight, stable implementation for basic queries
2. **Enhanced Server** (`enhanced_mcp.py`) - Full-featured implementation with advanced capabilities

Both servers are completely standalone, independent of global Claude configurations, with local API key management via `.env` file.

## Development Setup

### Environment Configuration
Create a `.env` file in the project root with:
```env
XAI_API_KEY=your_api_key_here

# Optional for enhanced server
GROK_MODEL=grok-4-0709
GROK_TEMPERATURE=0.7
MAX_CONTEXT_TOKENS=10000
DEFAULT_MAX_ITERATIONS=3
STORAGE_PATH=./grok_discussions
ENABLE_STREAMING=false
MCP_ENABLE_CACHING=true
MCP_CACHE_TTL=3600
```

### Python Requirements
- Python 3.11+ required
- Use `uv` for dependency management
- Key dependencies: `openai>=1.0.0`, `libtmux>=0.15.0`, `pyyaml>=6.0`, `python-dotenv>=1.0.0`, `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`

## Architecture

### Simple Server (`simple_mcp.py`)
- Minimal MCP implementation that works reliably with Claude Code
- Single tool: `grok_ask`
- Direct stdio communication
- No external dependencies beyond core libraries

### Enhanced Server (`enhanced_mcp.py`)
Complete implementation with modular architecture:

#### Core Components

1. **Tools Module** (`lib/tools/`)
   - `ask.py` - Basic question-answer tool (backward compatible)
   - `discuss.py` - Multi-turn conversation management with file context support (includes line ranges)
   - `session.py` - Session persistence and management (includes line ranges)
   - `context.py` - File-aware context handling for single questions (includes line ranges)
   - `health.py` - Server health monitoring

2. **Grok Client** (`lib/grok_client.py`)
   - Async OpenAI-compatible client
   - Retry logic with exponential backoff
   - Streaming support infrastructure
   - Token counting and management

3. **MCP Protocol Implementation**
   - JSON-RPC 2.0 over stdio
   - Standard error codes (32000-32099)
   - Tools: `grok_ask`, `grok_discuss`, `grok_continue`, `grok_list_sessions`, `grok_ask_with_context`, `grok_health`
   - Resources: `grok://sessions`, `grok://config`, `grok://stats`

### Data Flow

1. **Request Processing**: Claude Code → stdio → JSON-RPC parser → Tool router
2. **Tool Execution**: Tool handler → Grok client → X.AI API → Response formatting
3. **Session Management**: Create/update session → Persist to disk → Enable continuation
4. **Resource Access**: Resource request → Data aggregation → JSON response

## Testing Approach

### Test Structure
```
tests/
├── test_tools.py        # Unit tests for all tools
├── test_integration.py  # Integration tests for MCP protocol
└── run_tests.py        # Comprehensive test runner
```

### Running Tests
```bash
# All tests with validation
uv run python run_tests.py

# Unit tests only
uv run pytest tests/test_tools.py -v

# Integration tests
uv run pytest tests/test_integration.py -v

# Quick validation
uv run python test_enhanced.py
```

### Test Coverage
- 15+ unit tests covering all tools
- 11+ integration tests for MCP protocol
- Backward compatibility validation
- Mock Grok API for testing without API calls

## Configuration for Claude Code

### Using Simple Server (Basic)
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

### Using Enhanced Server (Recommended)
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

## File Organization

```
discussWithGrokMCP/
├── simple_mcp.py              # Simple server (stable fallback)
├── enhanced_mcp.py            # Enhanced server (full features)
├── lib/
│   ├── grok_client.py         # X.AI API client
│   └── tools/                 # Tool implementations
│       ├── __init__.py
│       ├── base.py            # Base tool class
│       ├── ask.py             # Basic Q&A
│       ├── discuss.py         # Discussions
│       ├── session.py         # Session management
│       ├── context.py         # Context handling
│       ├── context_loader.py  # Advanced file/directory loading
│       └── health.py          # Health checks
├── tests/                     # Test suite
│   ├── test_tools.py
│   ├── test_integration.py
│   └── test_context_loader.py # Context loader tests
├── sessions/                  # Session storage (auto-created)
├── .env                       # API keys (create this)
├── .gitignore                # Excludes sensitive files
├── pyproject.toml            # Dependencies
└── *.log                     # Server logs (auto-created)
```

## Security Considerations

- API keys stored in `.env` (excluded from git)
- File access sandboxed to project directory
- Input validation on all MCP tool parameters
- No shell command execution
- Sensitive data masking in logs
- Session data stored locally only

## Implementation Guidelines

### When Adding New Features
1. Maintain backward compatibility with `simple_mcp.py`
2. Add comprehensive unit tests
3. Test with Claude Code before merging
4. Update both README.md and CLAUDE.md
5. Use semantic versioning

### Code Style
- Use type hints for all functions
- Follow Python PEP 8 conventions
- Add docstrings to all classes and public methods
- Keep functions focused and testable
- Handle errors gracefully with meaningful messages

### Error Handling
- Return error messages in tool responses (don't raise exceptions)
- Log errors to file for debugging
- Provide helpful error messages to users
- Implement retry logic for transient failures
- Gracefully degrade functionality when possible

## Current State

The project has two working implementations:

1. **Simple Server** (v0.3.x): Proven stable, used as fallback
2. **Enhanced Server** (v0.9.x): Full feature set with all planned capabilities

Both servers have been tested and work correctly with Claude Code CLI. The enhanced server includes:
- 6 powerful tools for various interaction patterns
- 3 resource endpoints for monitoring and configuration
- Comprehensive error handling and logging
- Response caching for improved performance
- Session persistence for context retention
- Line range support for precise file context inclusion

### Enhanced File Context Support

The enhanced server now supports advanced file context capabilities including directories, glob patterns, and intelligent filtering:

#### Supported Input Types

```python
# 1. Single files
context_files = ["file.py"]

# 2. Directories (non-recursive by default when using string)
context_files = ["src/"]

# 3. Glob patterns
context_files = ["**/*.py", "src/**/*.test.js"]

# 4. Files with line ranges
context_files = [{"path": "file.py", "from": 10, "to": 50}]

# 5. Directories with options
context_files = [{
    "path": "src/",
    "recursive": true,  # Traverse subdirectories
    "extensions": [".py", ".js"],  # Only these file types
    "exclude": ["test_*", "*.pyc"],  # Exclude patterns
    "pattern": "**/api/*.py"  # Additional glob filter
}]

# 6. Mixed specifications
context_files = [
    "README.md",  # Single file
    "src/",  # Directory
    "**/*.yaml",  # Pattern
    {"path": "main.py", "from": 1, "to": 100},  # File with range
    {"path": "tests/", "recursive": true, "extensions": [".py"]}  # Filtered directory
]
```

#### Context Type Auto-Detection

When a directory is specified without extensions, the context type determines default extensions:

- **code**: `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.go`, `.rs`, etc.
- **docs**: `.md`, `.txt`, `.rst`, `.adoc`, etc.
- **config**: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, etc.
- **general**: All files (no filtering)

#### Automatic Exclusions

The following are automatically excluded to avoid noise:
- `__pycache__`, `.git`, `.svn`, `node_modules`
- `.venv`, `venv`, `env`, `.env`
- `*.pyc`, `*.pyo`, `*.pyd`, `.DS_Store`
- `.pytest_cache`, `.mypy_cache`, `dist`, `build`

#### Implementation Details

The new `ContextLoader` class (in `lib/tools/context_loader.py`) handles all file resolution:

- Efficiently processes large directories
- Respects line and total line limits
- Provides detailed metadata about loaded files
- Handles errors gracefully
- Supports various text encodings

This feature is available in:
- `grok_discuss` - For comprehensive code reviews
- `grok_ask_with_context` - For targeted questions
- `grok_continue_session` - For adding context to ongoing discussions

## Debugging

### Log Files
- `simple_mcp.log` - Simple server logs
- `enhanced_mcp.log` - Enhanced server logs
- `mcp_errors.log` - Error-specific logging

### Common Issues
1. **Server fails in Claude Code**: Check absolute paths in .mcp.json
2. **API errors**: Verify XAI_API_KEY in .env
3. **Import errors**: Run `uv sync` to install dependencies
4. **Permission errors**: Ensure write access to project directory

### Monitoring
Use the `grok_health` tool to check:
- Server status
- API connectivity
- Response latency
- Token usage
- Cache statistics

## Important Instructions

- **NEVER** commit `.env` file or API keys
- **ALWAYS** test changes with Claude Code before committing
- **MAINTAIN** backward compatibility with simple_mcp.py
- **DOCUMENT** all new features in README.md
- **ADD** tests for any new functionality