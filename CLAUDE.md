# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server implementation for intelligent discussions with Grok-4 AI. The server is designed to be completely standalone, independent of global Claude configurations, with local API key management via `.env` file.

## Development Setup

### Environment Configuration
Create a `.env` file in the project root with:
```env
XAI_API_KEY=your_api_key_here
GROK_MODEL=grok-2-1212
GROK_TEMPERATURE=0.7
MAX_CONTEXT_TOKENS=10000
DEFAULT_MAX_ITERATIONS=3
STORAGE_PATH=./grok_discussions
ENABLE_STREAMING=true
```

### Python Requirements
- Python 3.11+ required
- Use `uv` for dependency management
- Key dependencies: `openai>=1.0.0`, `libtmux>=0.15.0`, `pyyaml>=6.0`, `python-dotenv>=1.0.0`

## Architecture

### Core Components

The server follows a modular architecture with five main components:

1. **Context Analyzer** (`lib/context_analyzer.py`): Implements NLP-enhanced context detection with semantic similarity, entity recognition, and token budget management. Analyzes questions to determine type (implementation, debugging, optimization) and gathers relevant project files.

2. **Baseline Generator** (`lib/baseline_generator.py`): Creates structured baseline documents for complex discussions. Generates multi-section documents including executive summary, problem analysis, current state, and proposed approaches.

3. **Grok Client** (`lib/grok_client.py`): Wrapper for X.AI API with streaming support, retry logic, and response parsing. Manages API communication and token counting.

4. **Storage Manager** (`lib/storage_manager.py`): Handles local persistence in `grok_discussions/` directory. Manages sessions, responses, baselines with search capabilities.

5. **Session Manager** (`lib/session_manager.py`): Maintains discussion state with checkpointing and crash recovery. Supports concurrent sessions and quality scoring.

### MCP Protocol Implementation

The server implements MCP protocol with:
- JSON-RPC 2.0 message format over stdio transport
- Standard MCP error codes (32000-32099)
- Six core tools: `grok_ask`, `grok_discuss`, `grok_continue`, `grok_export_problem`, `grok_list_sessions`, `grok_get_response`
- Three resource types: `grok://sessions`, `grok://responses/{id}`, `grok://baselines/{id}`

### Data Flow

1. **Initialization**: Client sends `initialize` → Server responds with capabilities
2. **Context Gathering**: Analyzer scans project files, detects patterns, scores relevance
3. **Baseline Creation**: Generator creates structured document for complex topics
4. **API Communication**: Client sends to Grok with retry logic and streaming
5. **Response Storage**: Manager persists responses with metadata in local storage
6. **Session Management**: Manager tracks state, handles checkpoints, enables recovery

## Implementation Phases

Currently in planning phase. Implementation follows four phases:

**Phase 1 (Current Focus)**: Core MCP server with basic ask/respond
**Phase 2**: Advanced discussions with NLP and security
**Phase 3**: Intelligence features and scalability
**Phase 4**: Production readiness with monitoring

## File Organization

```
discussWithGrokMCP/
├── server.py              # Main MCP server entry point
├── .env                   # API keys and configuration
├── lib/                   # Core module implementations
│   ├── context_analyzer.py
│   ├── baseline_generator.py
│   ├── grok_client.py
│   ├── storage_manager.py
│   └── session_manager.py
├── grok_discussions/      # Local storage (auto-created)
│   ├── sessions/
│   ├── responses/
│   ├── baselines/
│   └── metadata.json
├── tests/                 # Test suite
└── outputs/              # Grok response outputs
    └── grok_responses/
        ├── pending/
        └── metadata.json
```

## Security Considerations

- API keys stored in `.env` with encryption support planned
- File access sandboxed to project directory
- Input validation on all MCP tool parameters
- No shell command execution
- Sensitive data detection and masking

## Testing Approach

When implementing:
- Unit test each core module independently
- Integration test MCP message flow
- Mock X.AI API responses for testing
- Test session recovery and error handling
- Validate security boundaries

## Current State

The project has a comprehensive specification (`MCP_GROK_SERVER_SPEC.md`) that has been reviewed and enhanced based on Grok's feedback. No implementation code exists yet - the server needs to be built from scratch following the specification.