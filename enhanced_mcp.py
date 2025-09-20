#!/usr/bin/env python3
"""
Enhanced MCP server with all features from the improvement spec.
Backward compatible with simple_mcp.py.
"""

import sys
import json
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid

from dotenv import load_dotenv

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import GrokClient
from lib.tools import (
    AskTool,
    DiscussTool,
    SessionManager,
    ListSessionsTool,
    ContinueSessionTool,
    AskWithContextTool,
    HealthCheckTool
)

# Load .env
load_dotenv(Path(__file__).parent / '.env')

# Configure logging
log_level = os.getenv('MCP_LOG_LEVEL', 'INFO')
log_file = os.getenv('MCP_LOG_FILE', 'enhanced_mcp.log')

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        # Also log errors to a separate file
        logging.FileHandler('mcp_errors.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Global instances
grok_client = None
session_manager = None
tools = {}
resources = {}
cache = {}
cache_size = 0  # Track total cache size in bytes
max_cache_size = None  # Will be initialized from env
streaming_enabled = False


class EnhancedMCPServer:
    """Enhanced MCP server with full feature set."""
    
    def __init__(self):
        """Initialize the enhanced server."""
        global max_cache_size
        self.initialized = False
        self.capabilities = self._build_capabilities()
        self.setup_tools()
        self.setup_resources()
        self.request_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        max_cache_size = int(os.getenv('MAX_CACHE_SIZE_MB', '100')) * 1024 * 1024
        logger.info(f"EnhancedMCPServer created at {self.start_time}")
    
    def _build_capabilities(self) -> Dict[str, Any]:
        """Build server capabilities."""
        global streaming_enabled
        streaming_enabled = os.getenv('MCP_ENABLE_STREAMING', 'false').lower() == 'true'
        
        caps = {
            "tools": {},
            "resources": {
                "subscribe": False,
                "list": True,
                "read": True
            }
        }
        
        if streaming_enabled:
            caps["streaming"] = {
                "supported": True,
                "methods": ["tools/call"]
            }
        
        return caps
    
    def setup_tools(self):
        """Initialize all tools."""
        global grok_client, session_manager, tools
        
        # Initialize clients
        model = os.getenv('GROK_MODEL', 'grok-4-fast-reasoning')
        temperature = float(os.getenv('GROK_TEMPERATURE', '0.7'))
        
        grok_client = GrokClient(model=model, temperature=temperature)
        session_manager = SessionManager(Path("./sessions"))
        
        # Initialize tools
        tool_instances = [
            AskTool(grok_client),
            DiscussTool(grok_client, session_manager),
            ListSessionsTool(grok_client, session_manager),
            ContinueSessionTool(grok_client, session_manager),
            AskWithContextTool(grok_client),
            HealthCheckTool(grok_client)
        ]
        
        for tool in tool_instances:
            tools[tool.name] = tool
        
        logger.info(f"Initialized {len(tools)} tools")
    
    def setup_resources(self):
        """Initialize resources."""
        global resources
        
        resources = {
            "grok://sessions": {
                "name": "sessions",
                "description": "Conversation sessions",
                "mimeType": "application/json"
            },
            "grok://config": {
                "name": "config",
                "description": "Server configuration",
                "mimeType": "application/json"
            },
            "grok://stats": {
                "name": "stats",
                "description": "Usage statistics",
                "mimeType": "application/json"
            }
        }
        
        logger.info(f"Initialized {len(resources)} resources")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        self.request_count += 1
        logger.debug(f"Request #{self.request_count}: {method}")
        
        try:
            # Protocol methods
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "initialized":
                logger.info("Client confirmed initialization")
                return None  # Notification, no response
            
            # Tool methods
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tool_call(request_id, params)
            
            # Resource methods
            elif method == "resources/list":
                return await self.handle_resources_list(request_id)
            elif method == "resources/read":
                return await self.handle_resource_read(request_id, params)
            
            # Unknown method
            else:
                logger.warning(f"Unknown method: {method}")
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
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error handling request: {e}", exc_info=True)
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
            return None
    
    async def handle_initialize(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        self.initialized = True
        
        # Log client capabilities
        client_caps = params.get("capabilities", {})
        logger.info(f"Client capabilities: {client_caps}")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": "grok-enhanced",
                    "version": "0.8.0"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: int) -> Dict[str, Any]:
        """Handle tools/list request."""
        tool_list = [tool.to_mcp_tool() for tool in tools.values()]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tool_list
            }
        }
    
    async def handle_tool_call(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in tools:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
        
        try:
            # Check if streaming is requested and supported
            if arguments.get("stream", False) and streaming_enabled:
                # TODO: Implement streaming in Phase 2
                # For now, fall back to non-streaming
                arguments["stream"] = False
            
            # Execute the tool
            tool = tools[tool_name]
            result = await tool.execute(**arguments)
            
            # Check cache for repeated questions (Phase 5)
            cache_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
            cache_enabled = os.getenv('MCP_ENABLE_CACHING', 'true').lower() == 'true'
            cache_hit = False
            
            if cache_key in cache and cache_enabled:
                cache_entry = cache[cache_key]
                if (datetime.now() - cache_entry['timestamp']).seconds < int(os.getenv('MCP_CACHE_TTL', '3600')):
                    logger.debug(f"Cache hit for {cache_key}")
                    result = cache_entry['result']
                    cache_hit = True
                else:
                    # Remove expired entry
                    self._remove_from_cache(cache_key)
            
            if not cache_hit and cache_enabled:
                # Check if adding to cache would exceed size limit
                self._add_to_cache(cache_key, result)
            
            # Check response size and truncate if necessary
            max_response_tokens = int(os.getenv('MCP_MAX_RESPONSE_TOKENS', '40000'))
            estimated_tokens = self._estimate_tokens(result)
            
            if estimated_tokens > max_response_tokens:
                logger.warning(f"Response size ({estimated_tokens} tokens) exceeds limit ({max_response_tokens} tokens). Truncating...")
                result = self._truncate_response(result, max_response_tokens)
                result += f"\n\n[Response truncated. Original size: ~{estimated_tokens} tokens, limit: {max_response_tokens} tokens]"
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def handle_resources_list(self, request_id: int) -> Dict[str, Any]:
        """Handle resources/list request."""
        resource_list = [
            {
                "uri": uri,
                "name": res["name"],
                "description": res["description"],
                "mimeType": res["mimeType"]
            }
            for uri, res in resources.items()
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": resource_list
            }
        }
    
    async def handle_resource_read(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        
        if uri not in resources:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Unknown resource: {uri}"
                }
            }
        
        try:
            content = await self.get_resource_content(uri)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resources[uri]["mimeType"],
                            "text": json.dumps(content, indent=2)
                        }
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Resource read failed: {str(e)}"
                }
            }
    
    async def get_resource_content(self, uri: str) -> Dict[str, Any]:
        """Get content for a resource."""
        if uri == "grok://sessions":
            return {
                "sessions": session_manager.list_sessions(limit=100)
            }
        elif uri == "grok://config":
            return {
                "model": os.getenv('GROK_MODEL', 'grok-4-fast-reasoning'),
                "temperature": float(os.getenv('GROK_TEMPERATURE', '0.7')),
                "max_tokens": int(os.getenv('GROK_MAX_TOKENS', '4096')),
                "streaming": streaming_enabled,
                "caching": os.getenv('MCP_ENABLE_CACHING', 'true').lower() == 'true',
                "cache_ttl": int(os.getenv('MCP_CACHE_TTL', '3600')),
                "features": {
                    "sessions": os.getenv('ENABLE_SESSIONS', 'true').lower() == 'true',
                    "context": os.getenv('ENABLE_CONTEXT', 'true').lower() == 'true',
                    "resources": os.getenv('ENABLE_RESOURCES', 'true').lower() == 'true',
                    "health": os.getenv('ENABLE_HEALTH_CHECK', 'true').lower() == 'true'
                }
            }
        elif uri == "grok://stats":
            uptime = (datetime.now() - self.start_time).total_seconds()
            return {
                "requests": self.request_count,
                "errors": self.error_count,
                "error_rate": self.error_count / max(1, self.request_count),
                "uptime_seconds": int(uptime),
                "tokens_used": grok_client.get_total_tokens_used() if grok_client else 0,
                "cache_size": len(cache),
                "active_sessions": len([s for s in session_manager.sessions.values() 
                                      if s.get("status") == "active"]) if session_manager else 0
            }
        else:
            raise ValueError(f"Unknown resource: {uri}")
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string.
        
        Uses a simple heuristic: ~1 token per 4 characters.
        This is a rough approximation that works reasonably well for English text.
        """
        return len(text) // 4
    
    def _truncate_response(self, text: str, max_tokens: int) -> str:
        """Truncate response to fit within token limit.
        
        Attempts to truncate at a reasonable boundary (paragraph or sentence).
        """
        # Estimate character limit based on token limit
        char_limit = max_tokens * 4
        
        if len(text) <= char_limit:
            return text
        
        # Try to find a good truncation point
        truncated = text[:char_limit]
        
        # Look for the last paragraph break
        last_paragraph = truncated.rfind('\n\n')
        if last_paragraph > char_limit * 0.8:  # If we found a paragraph break in the last 20%
            return truncated[:last_paragraph]
        
        # Look for the last sentence
        last_sentence = max(
            truncated.rfind('. '),
            truncated.rfind('! '),
            truncated.rfind('? ')
        )
        if last_sentence > char_limit * 0.8:
            return truncated[:last_sentence + 1]
        
        # Fall back to simple truncation
        return truncated + "..."
    
    def _add_to_cache(self, key: str, value: str):
        """Add an item to cache with size management."""
        global cache, cache_size, max_cache_size
        
        # Calculate size of new entry
        entry = {'result': value, 'timestamp': datetime.now()}
        # Convert datetime to string for JSON serialization
        entry_json = {'result': value, 'timestamp': entry['timestamp'].isoformat()}
        entry_size = len(json.dumps(entry_json))
        
        # Check if we need to evict entries to make room
        while cache and (cache_size + entry_size > max_cache_size):
            # Find and remove oldest entry
            oldest_key = min(cache.keys(), key=lambda k: cache[k]['timestamp'])
            self._remove_from_cache(oldest_key)
            logger.debug(f"Evicted cache entry {oldest_key} to free space")
        
        # Add new entry
        cache[key] = entry
        cache_size += entry_size
        logger.debug(f"Added to cache: {key}, cache size now {cache_size / 1024:.1f} KB")
    
    def _remove_from_cache(self, key: str):
        """Remove an item from cache and update size."""
        global cache, cache_size
        
        if key in cache:
            # Convert datetime to string for JSON serialization
            entry = cache[key]
            entry_json = {'result': entry['result'], 'timestamp': entry['timestamp'].isoformat() if hasattr(entry['timestamp'], 'isoformat') else str(entry['timestamp'])}
            entry_size = len(json.dumps(entry_json))
            del cache[key]
            cache_size = max(0, cache_size - entry_size)  # Ensure non-negative


async def main():
    """Main loop - read JSON-RPC from stdin, write to stdout."""
    server = EnhancedMCPServer()
    logger.info("Starting enhanced MCP server main loop")
    
    # Set up async stdin reading
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    try:
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    except:
        # Fallback for systems that don't support async pipes
        pass
    
    buffer = ""
    
    while True:
        try:
            # Try async read
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
            
            # Process complete JSON objects
            while buffer:
                try:
                    if '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            request = json.loads(line)
                            logger.debug(f"Received: {request}")
                            
                            # Handle request
                            response = await server.handle_request(request)
                            
                            # Send response if not a notification
                            if response:
                                response_str = json.dumps(response)
                                sys.stdout.write(response_str + '\n')
                                sys.stdout.flush()
                                logger.debug(f"Sent: {response_str}")
                    else:
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}, buffer: {buffer[:100]}")
                    buffer = ""  # Clear bad buffer
                    break
                except Exception as e:
                    logger.error(f"Processing error: {e}", exc_info=True)
                    break
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
    
    logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())