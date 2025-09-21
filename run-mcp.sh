#!/bin/bash
cd /home/clauderun/discussWithGrokMCP

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the MCP server
exec /home/clauderun/.local/bin/uv run --project /home/clauderun/discussWithGrokMCP /home/clauderun/discussWithGrokMCP/enhanced_mcp.py