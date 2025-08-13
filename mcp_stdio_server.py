#!/usr/bin/env python3
"""
Grok MCP Server - Simplified stdio implementation for MCP.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load .env from script directory, not CWD
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Debug: Log current working directory and environment
debug_info = {
    "cwd": os.getcwd(),
    "script_path": __file__,
    "python_path": sys.path,
    "env_XAI_API_KEY": "SET" if os.getenv("XAI_API_KEY") else "NOT SET"
}

# Write debug info to log file instead of stderr to avoid interference
with open('/tmp/mcp_debug.log', 'w') as f:
    f.write(f"DEBUG: MCP Server Starting\n")
    f.write(f"DEBUG: CWD: {debug_info['cwd']}\n")
    f.write(f"DEBUG: Script: {debug_info['script_path']}\n")
    f.write(f"DEBUG: API Key: {debug_info['env_XAI_API_KEY']}\n")

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    GrokClient,
    StorageManager,
    SessionManager,
    ContextAnalyzer,
    BaselineGenerator,
)

# Configure logging to file only
log_file_path = Path(__file__).parent / 'grok_mcp_server.log'
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger(__name__)

# Log startup details
logger.debug(f"Starting Grok MCP Server")
logger.debug(f"Current working directory: {os.getcwd()}")
logger.debug(f"Script path: {__file__}")
logger.debug(f"Python path: {sys.path}")
logger.debug(f"Environment XAI_API_KEY: {'SET' if os.getenv('XAI_API_KEY') else 'NOT SET'}")


class GrokMCPServer:
    """Main MCP server for Grok discussions."""
    
    def __init__(self):
        """Initialize the Grok MCP server."""
        # Server info
        self.server_info = {
            "name": "grok-mcp-server",
            "version": "0.1.0",
            "vendor": "Grok MCP"
        }
        
        # Initialize components
        self.grok_client = GrokClient()
        self.storage_manager = StorageManager()
        self.session_manager = SessionManager(self.storage_manager)
        self.context_analyzer = ContextAnalyzer()
        self.baseline_generator = BaselineGenerator()
        
        logger.info("Grok MCP Server initialized")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "initialized":
                return None  # No response for notification
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            elif method == "completion/complete":
                result = await self._handle_completion(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "serverInfo": self.server_info
        }
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": [
                {
                    "name": "grok_ask",
                    "description": "Ask a quick question to Grok",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "include_context": {"type": "boolean", "default": True}
                        },
                        "required": ["question"]
                    }
                },
                {
                    "name": "grok_discuss",
                    "description": "Start a discussion with Grok",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "max_iterations": {"type": "integer", "default": 3}
                        },
                        "required": ["topic"]
                    }
                }
            ]
        }
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "grok_ask":
            question = arguments.get("question", "")
            response = await self.grok_client.ask(prompt=question, stream=False)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response.content
                    }
                ]
            }
        
        elif tool_name == "grok_discuss":
            topic = arguments.get("topic", "")
            response = await self.grok_client.ask(
                prompt=f"Let's discuss: {topic}",
                stream=False
            )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response.content
                    }
                ]
            }
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        return {"resources": []}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        return {"contents": []}
    
    async def _handle_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion request."""
        return {"completion": {"values": []}}


async def main():
    """Main entry point - handle stdio communication."""
    try:
        server = GrokMCPServer()
        logger.info("Server created, entering main loop")
    except Exception as e:
        logger.error(f"Failed to create server: {e}")
        return
    
    # Read from stdin and write to stdout
    while True:
        try:
            # Read a line from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            if not line:
                # Don't exit on EOF, just continue waiting
                logger.debug("Empty line received, continuing")
                await asyncio.sleep(0.1)
                continue
                
            # Parse JSON-RPC request
            try:
                request = json.loads(line)
                logger.debug(f"Received request: {request.get('method', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                continue
            
            # Handle request
            response = await server.handle_request(request)
            
            # Send response if not a notification
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                logger.debug(f"Sent response for {request.get('method', 'unknown')}")
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt, exiting")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    # Run the server
    asyncio.run(main())