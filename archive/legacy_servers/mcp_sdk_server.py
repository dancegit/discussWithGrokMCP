#!/usr/bin/env python3
"""
Grok MCP Server - Implementation using official MCP Python SDK.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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
log_file_path = Path(__file__).parent / 'grok_mcp_sdk_server.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("grok-mcp-server")

# Initialize components globally
grok_client = None
storage_manager = None
session_manager = None
context_analyzer = None
baseline_generator = None

def initialize_components():
    """Initialize all components."""
    global grok_client, storage_manager, session_manager, context_analyzer, baseline_generator
    
    try:
        grok_client = GrokClient()
        storage_manager = StorageManager()
        session_manager = SessionManager(storage_manager)
        context_analyzer = ContextAnalyzer()
        baseline_generator = BaselineGenerator()
        logger.info("All components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        return False

# Initialize components on import
if not initialize_components():
    logger.error("Failed to initialize server components")
    sys.exit(1)

# Tool handlers
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="grok_ask",
            description="Ask a quick question to Grok with intelligent context gathering",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask Grok"
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Whether to include context",
                        "default": True
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="grok_discuss",
            description="Start an iterative discussion with baseline preparation",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to discuss"
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum number of iterations",
                        "default": 3
                    },
                    "use_baseline": {
                        "type": "boolean",
                        "description": "Whether to generate baseline",
                        "default": True
                    },
                    "expert_mode": {
                        "type": "boolean",
                        "description": "Include expert perspectives",
                        "default": False
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="grok_list_sessions",
            description="List all discussion sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum sessions to return",
                        "default": 10
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    logger.debug(f"Tool called: {name} with arguments: {arguments}")
    
    if name == "grok_ask":
        return await handle_grok_ask(arguments)
    elif name == "grok_discuss":
        return await handle_grok_discuss(arguments)
    elif name == "grok_list_sessions":
        return await handle_grok_list_sessions(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def handle_grok_ask(arguments: dict) -> list[TextContent]:
    """Handle grok_ask tool."""
    question = arguments.get("question", "")
    include_context = arguments.get("include_context", True)
    
    logger.debug(f"grok_ask: {question[:100]}...")
    
    try:
        # Analyze question
        analysis = await context_analyzer.analyze_question(question)
        
        # Gather context if requested
        context_text = ""
        context_included = []
        
        if include_context:
            context_items = await context_analyzer.gather_context(analysis)
            for item in context_items:
                context_text += f"\n\n---\nContext from {item.path}:\n{item.content[:500]}"
                context_included.append(item.path)
        
        # Prepare prompt
        full_prompt = question
        if context_text:
            full_prompt = f"Question: {question}\n\nRelevant Context:{context_text}"
        
        # Ask Grok
        response = await grok_client.ask(
            prompt=full_prompt,
            stream=False
        )
        
        # Create session for tracking
        session_id = session_manager.generate_session_id(prefix="ask")
        
        # Save response
        await storage_manager.save_response(
            session_id=session_id,
            response=response.content,
            metadata={
                "question": question,
                "context_files": context_included,
                "tokens": response.tokens_used
            }
        )
        
        logger.info(f"grok_ask completed, session_id: {session_id}")
        
        # Format response with metadata
        response_text = f"{response.content}\n\n---\nSession: {session_id}\nTokens used: {response.tokens_used}"
        if context_included:
            response_text += f"\nContext from: {', '.join(context_included)}"
        
        return [TextContent(type="text", text=response_text)]
        
    except Exception as e:
        logger.error(f"Error in grok_ask: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def handle_grok_discuss(arguments: dict) -> list[TextContent]:
    """Handle grok_discuss tool."""
    topic = arguments.get("topic", "")
    max_iterations = arguments.get("max_iterations", 3)
    use_baseline = arguments.get("use_baseline", True)
    expert_mode = arguments.get("expert_mode", False)
    
    logger.debug(f"grok_discuss: {topic}")
    
    try:
        # Create session
        session = await session_manager.create_session(
            topic=topic,
            max_iterations=max_iterations,
            session_type="discuss"
        )
        
        # Analyze topic
        analysis = await context_analyzer.analyze_question(topic)
        
        # Gather context
        context_items = await context_analyzer.gather_context(analysis)
        
        # Generate baseline if requested
        baseline_content = ""
        if use_baseline:
            baseline_content = await baseline_generator.generate(
                topic=topic,
                analysis=analysis,
                context_items=context_items,
                use_expert_mode=expert_mode
            )
            
            # Save baseline
            baseline_path = await storage_manager.save_baseline(
                session_id=session.id,
                baseline=baseline_content,
                topic=topic
            )
            
            session.has_baseline = True
            session.baseline_path = baseline_path
        
        # Initial prompt
        if baseline_content:
            prompt = f"Based on this analysis:\n{baseline_content[:2000]}...\n\nPlease provide insights on: {topic}"
        else:
            prompt = f"Please provide comprehensive insights on: {topic}"
        
        # Get initial response
        response = await grok_client.ask(prompt=prompt, stream=False)
        
        # Update session
        await session_manager.update_session(
            session_id=session.id,
            response=response,
            iteration_complete=True
        )
        
        # Save response
        await storage_manager.save_response(
            session_id=session.id,
            response=response.content,
            iteration=1
        )
        
        logger.info(f"grok_discuss started session: {session.id}")
        
        result = (
            f"Session started: {session.id}\n\n"
            f"Topic: {topic}\n"
            f"Max iterations: {max_iterations}\n"
            f"Baseline generated: {use_baseline}\n\n"
            f"Initial response:\n{response.content[:500]}..."
        )
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error in grok_discuss: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def handle_grok_list_sessions(arguments: dict) -> list[TextContent]:
    """Handle grok_list_sessions tool."""
    status = arguments.get("status")
    limit = arguments.get("limit", 10)
    
    logger.debug(f"grok_list_sessions: status={status}, limit={limit}")
    
    try:
        sessions = await storage_manager.list_sessions(
            status=status,
            limit=limit
        )
        
        if not sessions:
            return [TextContent(type="text", text="No sessions found.")]
        
        result = f"Found {len(sessions)} session(s):\n\n"
        for session in sessions:
            result += (
                f"- {session['id']}\n"
                f"  Topic: {session.get('topic', 'N/A')}\n"
                f"  Status: {session.get('status', 'N/A')}\n"
                f"  Iterations: {session.get('iterations', 0)}\n\n"
            )
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error in grok_list_sessions: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point."""
    logger.info("Starting Grok MCP Server with official SDK...")
    
    try:
        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())