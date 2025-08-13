#!/bin/bash
# Wrapper script for MCP server to handle environment setup

# Change to the correct directory
cd /home/user/gitrepos/discussWithGrokMCP

# Run the server with uv
exec uv run python mcp_stdio_server.py