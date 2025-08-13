#!/usr/bin/env python3
"""
Grok MCP Server - Simplified implementation using MCP SDK CLI.
This server can be run directly with: uv run mcp run grok_mcp.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import mcp.server.stdio
import mcp.types as types

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    GrokClient,
    StorageManager,
    SessionManager,
    ContextAnalyzer,
    BaselineGenerator,
)

# Load .env from script directory
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configure logging
log_file = Path(__file__).parent / 'grok_mcp.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
try:
    grok_client = GrokClient()
    storage_manager = StorageManager()
    session_manager = SessionManager(storage_manager)
    context_analyzer = ContextAnalyzer()
    baseline_generator = BaselineGenerator()
    logger.info("Components initialized")
except Exception as e:
    logger.error(f"Failed to initialize: {e}")
    sys.exit(1)

server = mcp.server.Server("grok-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return available tools."""
    return [
        types.Tool(
            name="grok_ask",
            description="Ask Grok a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask"},
                    "include_context": {"type": "boolean", "default": True}
                },
                "required": ["question"]
            }
        ),
        types.Tool(
            name="grok_discuss",
            description="Start a discussion with Grok",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to discuss"},
                    "max_iterations": {"type": "integer", "default": 3}
                },
                "required": ["topic"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""
    if arguments is None:
        arguments = {}
    
    logger.info(f"Tool called: {name}")
    
    try:
        if name == "grok_ask":
            question = arguments.get("question", "")
            include_context = arguments.get("include_context", True)
            
            # Simple implementation for testing
            response = await grok_client.ask(prompt=question, stream=False)
            
            return [
                types.TextContent(
                    type="text",
                    text=response.content
                )
            ]
            
        elif name == "grok_discuss":
            topic = arguments.get("topic", "")
            max_iterations = arguments.get("max_iterations", 3)
            
            # Simple implementation for testing
            response = await grok_client.ask(
                prompt=f"Let's discuss: {topic}",
                stream=False
            )
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Discussion started on: {topic}\n\n{response.content}"
                )
            ]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def main():
    """Run the server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())