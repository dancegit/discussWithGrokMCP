#!/usr/bin/env python3
"""
Grok MCP Server - Standalone MCP server implementation using stdio.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from dotenv import load_dotenv

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    GrokClient,
    StorageManager,
    SessionManager,
    ContextAnalyzer,
    BaselineGenerator,
)

# Load environment variables
load_dotenv()

# Configure logging to file only (not stderr which would interfere with stdio)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('grok_mcp_server.log')
    ]
)
logger = logging.getLogger(__name__)


class StdioProtocol:
    """Handles stdio communication for MCP."""
    
    def __init__(self, server):
        self.server = server
        self.reader = None
        self.writer = None
        
    async def start(self):
        """Start reading from stdin and writing to stdout."""
        # Create streams for stdin/stdout
        loop = asyncio.get_event_loop()
        self.reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self.reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        # Writer for stdout
        w_transport, w_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        self.writer = asyncio.StreamWriter(w_transport, w_protocol, self.reader, loop)
        
        # Start processing messages
        await self.process_messages()
    
    async def process_messages(self):
        """Process incoming JSON-RPC messages."""
        buffer = ""
        
        while True:
            try:
                # Read a chunk of data
                chunk = await self.reader.read(4096)
                if not chunk:
                    break
                    
                buffer += chunk.decode('utf-8')
                
                # Try to parse complete JSON objects
                while buffer:
                    try:
                        # Find the end of a JSON object
                        decoder = json.JSONDecoder()
                        obj, idx = decoder.raw_decode(buffer)
                        buffer = buffer[idx:].lstrip()
                        
                        # Process the message
                        response = await self.server.handle_request(obj)
                        if response:
                            await self.send_response(response)
                            
                    except json.JSONDecodeError:
                        # Need more data
                        break
                        
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self.send_error(None, -32700, "Parse error")
    
    async def send_response(self, response: Dict[str, Any]):
        """Send a JSON-RPC response."""
        response_str = json.dumps(response) + "\n"
        self.writer.write(response_str.encode('utf-8'))
        await self.writer.drain()
    
    async def send_error(self, id: Any, code: int, message: str, data: Any = None):
        """Send a JSON-RPC error response."""
        error_response = {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data:
            error_response["error"]["data"] = data
        await self.send_response(error_response)


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
        
        # Server state
        self.initialized = False
        
        logger.info("Grok MCP Server initialized")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request."""
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return self._error_response(request.get("id"), -32600, "Invalid Request")
        
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "initialized":
                self.initialized = True
                return None  # No response for notification
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
            
            # Return successful response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return self._error_response(request_id, -32603, str(e))
    
    def _error_response(self, id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create an error response."""
        response = {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data:
            response["error"]["data"] = data
        return response
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": {},
                "resources": {
                    "list": True,
                    "read": True
                }
            },
            "serverInfo": self.server_info
        }
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "grok_ask",
                "description": "Ask a quick question to Grok with intelligent context gathering",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question or prompt"
                        },
                        "include_context": {
                            "type": "boolean",
                            "description": "Auto-gather relevant context",
                            "default": True
                        },
                        "context_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific files to include as context"
                        },
                        "stream": {
                            "type": "boolean",
                            "description": "Stream the response",
                            "default": True
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "grok_discuss",
                "description": "Start an iterative discussion with baseline preparation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Discussion topic"
                        },
                        "max_iterations": {
                            "type": "integer",
                            "description": "Maximum discussion rounds",
                            "default": 3
                        },
                        "use_baseline": {
                            "type": "boolean",
                            "description": "Generate baseline document",
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
            },
            {
                "name": "grok_list_sessions",
                "description": "List all discussion sessions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "completed", "failed", "paused"],
                            "description": "Filter by status"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum sessions to return",
                            "default": 10
                        }
                    }
                }
            }
        ]
        
        return {"tools": tools}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "grok_ask":
            result = await self._handle_grok_ask(arguments)
        elif tool_name == "grok_discuss":
            result = await self._handle_grok_discuss(arguments)
        elif tool_name == "grok_list_sessions":
            result = await self._handle_grok_list_sessions(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    async def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = []
        
        # List sessions as resources
        sessions = await self.storage_manager.list_sessions(limit=20)
        for session in sessions:
            resources.append({
                "uri": f"grok://sessions/{session['id']}",
                "name": f"Session: {session['topic']}",
                "mimeType": "application/json",
                "description": f"Status: {session['status']}, Iterations: {session['iterations']}"
            })
        
        return {"resources": resources}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        
        if uri and uri.startswith("grok://sessions/"):
            session_id = uri.replace("grok://sessions/", "")
            session = await self.session_manager.get_session(session_id)
            
            if session:
                content = json.dumps(session.to_dict(), indent=2)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                            "mimeType": "application/json"
                        }
                    ]
                }
            else:
                raise ValueError(f"Session {session_id} not found")
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    async def _handle_grok_ask(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_ask tool."""
        question = arguments["question"]
        include_context = arguments.get("include_context", True)
        context_files = arguments.get("context_files", [])
        
        # Analyze question
        analysis = await self.context_analyzer.analyze_question(question)
        
        # Gather context if requested
        context_text = ""
        context_included = []
        
        if include_context:
            context_items = await self.context_analyzer.gather_context(
                analysis,
                include_files=context_files
            )
            
            for item in context_items:
                context_text += f"\n\n---\nContext from {item.path}:\n{item.content[:500]}"
                context_included.append(item.path)
        
        # Prepare prompt
        full_prompt = question
        if context_text:
            full_prompt = f"Question: {question}\n\nRelevant Context:{context_text}"
        
        # Ask Grok
        response = await self.grok_client.ask(
            prompt=full_prompt,
            stream=False  # Can't stream in JSON-RPC response
        )
        
        # Create simple session for tracking
        session_id = self.session_manager.generate_session_id(prefix="ask")
        
        # Save response
        await self.storage_manager.save_response(
            session_id=session_id,
            response=response.content,
            metadata={
                "question": question,
                "context_files": context_included,
                "tokens": response.tokens_used
            }
        )
        
        return {
            "response": response.content,
            "session_id": session_id,
            "context_included": context_included,
            "tokens_used": response.tokens_used
        }
    
    async def _handle_grok_discuss(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_discuss tool."""
        topic = arguments["topic"]
        max_iterations = arguments.get("max_iterations", 3)
        use_baseline = arguments.get("use_baseline", True)
        expert_mode = arguments.get("expert_mode", False)
        
        # Create session
        session = await self.session_manager.create_session(
            topic=topic,
            max_iterations=max_iterations,
            session_type="discuss"
        )
        
        # Analyze topic
        analysis = await self.context_analyzer.analyze_question(topic)
        
        # Gather context
        context_items = await self.context_analyzer.gather_context(analysis)
        
        # Generate baseline if requested
        baseline_content = ""
        if use_baseline:
            baseline_content = await self.baseline_generator.generate(
                topic=topic,
                analysis=analysis,
                context_items=context_items,
                use_expert_mode=expert_mode
            )
            
            # Save baseline
            baseline_path = await self.storage_manager.save_baseline(
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
        response = await self.grok_client.ask(prompt=prompt, stream=False)
        
        # Update session
        await self.session_manager.update_session(
            session_id=session.id,
            response=response,
            iteration_complete=True
        )
        
        # Save response
        await self.storage_manager.save_response(
            session_id=session.id,
            response=response.content,
            iteration=1
        )
        
        return {
            "session_id": session.id,
            "status": "active",
            "iterations_completed": 1,
            "max_iterations": max_iterations,
            "baseline_generated": use_baseline,
            "initial_response": response.content[:500] + "..." if len(response.content) > 500 else response.content
        }
    
    async def _handle_grok_list_sessions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_list_sessions tool."""
        status = arguments.get("status")
        limit = arguments.get("limit", 10)
        
        sessions = await self.storage_manager.list_sessions(
            status=status,
            limit=limit
        )
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    
    async def run(self):
        """Run the MCP server."""
        try:
            logger.info("Starting Grok MCP Server...")
            
            # Create stdio protocol
            protocol = StdioProtocol(self)
            
            # Start processing messages
            await protocol.start()
            
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            logger.info("Server shutting down...")


async def main():
    """Main entry point."""
    server = GrokMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())