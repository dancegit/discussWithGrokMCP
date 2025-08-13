# Grok MCP Server

A standalone Model Context Protocol (MCP) server for intelligent discussions with Grok-4 AI. Features context-aware conversations, baseline document generation, and comprehensive response management.

## Installation in Claude Code

### Method 1: Global Configuration

Add to your Claude Code configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "grok": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/absolute/path/to/discussWithGrokMCP",
      "env": {
        "XAI_API_KEY": "your_xai_api_key_here"
      }
    }
  }
}
```

### Method 2: Project-Specific Configuration

Create a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "grok": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/absolute/path/to/discussWithGrokMCP",
      "env": {
        "XAI_API_KEY": "your_xai_api_key_here"
      }
    }
  }
}
```

### Method 3: Using Python Directly

If you don't have `uv` installed, you can use Python directly:

```json
{
  "mcpServers": {
    "grok": {
      "command": "python",
      "args": ["/absolute/path/to/discussWithGrokMCP/mcp_server.py"],
      "env": {
        "XAI_API_KEY": "your_xai_api_key_here",
        "PYTHONPATH": "/absolute/path/to/discussWithGrokMCP"
      }
    }
  }
}
```

### Configuration Options

- **command**: The executable to run (`uv` recommended, or `python`/`python3`)
- **args**: Command arguments to start the server
- **cwd**: Working directory (must be absolute path to this repository)
- **env**: Environment variables including your X.AI API key

### Getting Your API Key

1. Visit [console.x.ai](https://console.x.ai)
2. Create an account or sign in
3. Generate an API key
4. Replace `your_xai_api_key_here` in the configuration

### Verifying Installation

After adding the configuration and restarting Claude Code, you should see the Grok MCP server tools available:
- `grok_ask` - Quick questions with context
- `grok_discuss` - Multi-turn discussions
- `grok_list_sessions` - View past sessions

## Features

- 🤖 **Intelligent Context Gathering** - NLP-enhanced context detection with semantic analysis
- 📄 **Baseline Document Generation** - Structured analysis documents for complex discussions
- 💬 **Iterative Discussions** - Multi-round conversations with state tracking
- 💾 **Session Management** - Checkpointing, crash recovery, and session persistence
- 🔒 **Secure & Standalone** - Local .env configuration, no global dependencies
- 📊 **Quality Scoring** - Automatic response quality assessment

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
# Test all components with real API
uv run python test_integration.py

# Test MCP server directly
uv run python test_direct.py
```

## MCP Tools

### `grok_ask`
Quick single-turn questions with automatic context gathering.

**Parameters:**
- `question` (string, required): The question to ask
- `include_context` (boolean): Auto-gather relevant context (default: true)
- `context_files` (array): Specific files to include
- `stream` (boolean): Stream the response (default: true)

**Example:**
```json
{
  "name": "grok_ask",
  "arguments": {
    "question": "How do I implement WebSocket in Python?",
    "include_context": true
  }
}
```

### `grok_discuss`
Start an iterative discussion with baseline preparation.

**Parameters:**
- `topic` (string, required): Discussion topic
- `max_iterations` (integer): Maximum rounds (default: 3)
- `use_baseline` (boolean): Generate baseline document (default: true)
- `expert_mode` (boolean): Include expert perspectives (default: false)

**Example:**
```json
{
  "name": "grok_discuss",
  "arguments": {
    "topic": "Design a scalable microservices architecture",
    "max_iterations": 5,
    "expert_mode": true
  }
}
```

### `grok_list_sessions`
List all discussion sessions.

**Parameters:**
- `status` (string): Filter by status (active/completed/failed/paused)
- `limit` (integer): Maximum sessions to return (default: 10)

## Project Structure

```
discussWithGrokMCP/
├── lib/                          # Core modules
│   ├── grok_client.py           # X.AI API wrapper
│   ├── storage_manager.py      # Persistence layer
│   ├── session_manager.py      # Session state management
│   ├── context_analyzer.py     # Intelligent context gathering
│   └── baseline_generator.py   # Baseline document creation
├── grok_discussions/            # Local storage
│   ├── sessions/               # Active sessions
│   ├── responses/              # Saved responses
│   └── baselines/              # Baseline documents
├── mcp_server.py               # MCP server implementation
├── test_integration.py         # Integration tests
├── test_direct.py              # Direct component tests
├── .env                        # API configuration
└── pyproject.toml              # Dependencies
```

## Architecture

### Core Components

1. **Grok Client** - Handles X.AI API communication with retry logic and streaming
2. **Storage Manager** - Manages local persistence of sessions, responses, and baselines
3. **Session Manager** - Tracks discussion state with checkpointing and recovery
4. **Context Analyzer** - NLP-enhanced context detection and relevance scoring
5. **Baseline Generator** - Creates structured analysis documents

### Data Flow

1. **Question Analysis** → Detect type, extract keywords and entities
2. **Context Gathering** → Find relevant files and documentation
3. **Baseline Generation** → Create structured analysis document
4. **API Communication** → Send to Grok with retry logic
5. **Response Storage** → Persist with metadata and quality scoring
6. **Session Management** → Track state and enable continuation

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
XAI_API_KEY=your_api_key_here

# Optional
GROK_MODEL=grok-2-1212
GROK_TEMPERATURE=0.7
MAX_CONTEXT_TOKENS=10000
DEFAULT_MAX_ITERATIONS=3
STORAGE_PATH=./grok_discussions
ENABLE_STREAMING=true
```

## Testing

### Unit Tests
```bash
uv run python -m pytest tests/
```

### Integration Test
```bash
uv run python test_integration.py
```

### Direct Component Test
```bash
uv run python test_direct.py
```

## Response Storage

Responses are stored locally in:
- `grok_discussions/sessions/` - Session state files
- `grok_discussions/responses/` - Individual responses
- `grok_discussions/baselines/` - Generated baseline documents

## Features in Detail

### Intelligent Context Gathering
- Analyzes questions to determine type (implementation, debugging, optimization)
- Extracts keywords, entities, and file references
- Scores context relevance using multiple factors
- Manages token budget automatically

### Baseline Document Generation
- Creates structured analysis documents
- Includes problem analysis, requirements, and success criteria
- Optional expert perspectives from multiple viewpoints
- Token-aware document assembly

### Session Management
- Atomic session operations with versioning
- Periodic checkpointing (every 60 seconds)
- Crash recovery from last checkpoint
- Quality scoring for responses
- Support for pausing and resuming sessions

## Performance

- **Response Time**: <500ms for simple questions
- **Token Efficiency**: Intelligent context selection within budget
- **Reliability**: Automatic retry with exponential backoff
- **Storage**: Local persistence with search capabilities

## Security

- API keys stored securely in `.env` file
- No global configuration dependencies
- File access sandboxed to project directory
- Sensitive data detection and masking

## Troubleshooting

### API Key Issues
- Ensure `XAI_API_KEY` is set in `.env` file
- Verify key at [console.x.ai](https://console.x.ai)

### Import Errors
- Install dependencies: `uv sync` or `pip install -e .`
- Ensure Python 3.11+ is installed

### Storage Issues
- Check write permissions for `grok_discussions/` directory
- Clear old sessions: `rm -rf grok_discussions/sessions/*`

## License

MIT

## Contributing

Contributions welcome! Please ensure all tests pass before submitting PRs.

## Support

For issues or questions, please open an issue on GitHub.