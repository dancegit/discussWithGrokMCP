#!/bin/bash
cd /home/user/discussWithGrokMCP

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the MCP server
exec /home/user/.local/bin/uv run --project /home/user/discussWithGrokMCP /home/user/discussWithGrokMCP/enhanced_mcp.py