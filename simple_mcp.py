#!/usr/bin/env python3
"""
Ultra-simple MCP server that just works with Claude Code.
Based on what Claude Code actually expects.
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import GrokClient

# Load .env
load_dotenv(Path(__file__).parent / '.env')

# Configure logging to file only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('simple_mcp.log')]
)
logger = logging.getLogger(__name__)

# Global Grok client
grok_client = GrokClient()


class SimpleMCPServer:
    """Dead simple MCP server."""
    
    def __init__(self):
        self.initialized = False
        logger.info("SimpleMCPServer created")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.debug(f"Handling: {method}")
        
        if method == "initialize":
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "grok-simple",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "initialized":
            # This is a notification, no response
            logger.debug("Got initialized notification")
            return None
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "grok_ask",
                            "description": "Ask Grok a question",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "The question to ask"
                                    }
                                },
                                "required": ["question"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "grok_ask":
                question = arguments.get("question", "Hello")
                try:
                    response = await grok_client.ask(prompt=question, stream=False)
                    content = response.content
                except Exception as e:
                    content = f"Error: {str(e)}"
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": content
                            }
                        ]
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        
        else:
            # Unknown method
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            return None


async def main():
    """Main loop - read JSON-RPC from stdin, write to stdout."""
    server = SimpleMCPServer()
    logger.info("Starting main loop")
    
    # Use asyncio for stdin reading
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    try:
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    except:
        # Fallback to sync reading
        pass
    
    buffer = ""
    while True:
        try:
            # Try async read first
            try:
                chunk = await asyncio.wait_for(reader.read(1024), timeout=0.1)
                if chunk:
                    buffer += chunk.decode('utf-8')
            except (asyncio.TimeoutError, AttributeError):
                # Fallback to sync read
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    line = sys.stdin.readline()
                    if line:
                        buffer += line
            
            # Process complete JSON objects from buffer
            while buffer:
                # Try to find a complete JSON object
                try:
                    # Simple approach: assume one JSON per line
                    if '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            request = json.loads(line)
                            logger.debug(f"Request: {request}")
                            
                            # Handle the request
                            response = await server.handle_request(request)
                            
                            # Send response if not a notification
                            if response:
                                response_str = json.dumps(response)
                                sys.stdout.write(response_str + '\n')
                                sys.stdout.flush()
                                logger.debug(f"Response: {response_str}")
                    else:
                        # No complete line yet
                        break
                except json.JSONDecodeError as e:
                    logger.error(f"JSON error: {e}, buffer: {buffer[:100]}")
                    buffer = ""  # Clear bad buffer
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            
    logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())