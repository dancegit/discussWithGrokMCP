#!/usr/bin/env python3
"""
Grok MCP Server - Main server implementation for Model Context Protocol.
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
from mcp import Server
from mcp.server import Request
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    INTERNAL_ERROR,
)

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('grok_mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GrokMCPServer:
    """Main MCP server for Grok discussions."""
    
    def __init__(self):
        """Initialize the Grok MCP server."""
        self.server = Server("grok-mcp-server")
        
        # Initialize components
        self.grok_client = GrokClient()
        self.storage_manager = StorageManager()
        self.session_manager = SessionManager(self.storage_manager)
        self.context_analyzer = ContextAnalyzer()
        self.baseline_generator = BaselineGenerator()
        
        # Register handlers
        self._register_tools()
        self._register_resources()
        
        logger.info("Grok MCP Server initialized")
    
    def _register_tools(self):
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
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
                ),
                Tool(
                    name="grok_discuss",
                    description="Start an iterative discussion with baseline preparation",
                    inputSchema={
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
                            },
                            "continue_session": {
                                "type": "string",
                                "description": "Continue existing session ID"
                            }
                        },
                        "required": ["topic"]
                    }
                ),
                Tool(
                    name="grok_continue",
                    description="Continue an active discussion session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session ID"
                            },
                            "input": {
                                "type": "string",
                                "description": "Follow-up question or refinement"
                            },
                            "include_new_context": {
                                "type": "boolean",
                                "description": "Add new context files",
                                "default": False
                            }
                        },
                        "required": ["session_id", "input"]
                    }
                ),
                Tool(
                    name="grok_export_problem",
                    description="Export a structured problem description for Grok analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Problem title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed problem description"
                            },
                            "error_messages": {
                                "type": "string",
                                "description": "Error output"
                            },
                            "code_files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string"},
                                        "start_line": {"type": "integer"},
                                        "end_line": {"type": "integer"}
                                    }
                                },
                                "description": "Files with line ranges"
                            },
                            "include_git": {
                                "type": "boolean",
                                "description": "Include git status/commits",
                                "default": False
                            },
                            "send_to_grok": {
                                "type": "boolean",
                                "description": "Immediately send to Grok",
                                "default": True
                            }
                        },
                        "required": ["title", "description"]
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
                ),
                Tool(
                    name="grok_get_response",
                    description="Retrieve a specific response or session details",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID to retrieve"
                            },
                            "include_baseline": {
                                "type": "boolean",
                                "description": "Include baseline if exists",
                                "default": False
                            },
                            "iteration": {
                                "type": "integer",
                                "description": "Specific iteration number"
                            }
                        },
                        "required": ["session_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "grok_ask":
                    result = await self._handle_grok_ask(arguments)
                elif name == "grok_discuss":
                    result = await self._handle_grok_discuss(arguments)
                elif name == "grok_continue":
                    result = await self._handle_grok_continue(arguments)
                elif name == "grok_export_problem":
                    result = await self._handle_grok_export_problem(arguments)
                elif name == "grok_list_sessions":
                    result = await self._handle_grok_list_sessions(arguments)
                elif name == "grok_get_response":
                    result = await self._handle_grok_get_response(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                raise
    
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources."""
            resources = []
            
            # List sessions
            sessions = await self.storage_manager.list_sessions(limit=50)
            for session in sessions:
                resources.append(Resource(
                    uri=f"grok://sessions/{session['id']}",
                    name=f"Session: {session['topic']}",
                    mimeType="application/json",
                    description=f"Status: {session['status']}, Iterations: {session['iterations']}"
                ))
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a resource."""
            if uri.startswith("grok://sessions/"):
                session_id = uri.replace("grok://sessions/", "")
                session = await self.session_manager.get_session(session_id)
                if session:
                    return json.dumps(session.to_dict(), indent=2)
                else:
                    raise ValueError(f"Session {session_id} not found")
            else:
                raise ValueError(f"Unknown resource URI: {uri}")
    
    async def _handle_grok_ask(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_ask tool call."""
        question = arguments["question"]
        include_context = arguments.get("include_context", True)
        context_files = arguments.get("context_files", [])
        stream = arguments.get("stream", True)
        
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
                context_text += f"\n\n---\nContext from {item.path}:\n{item.content[:1000]}"
                context_included.append(item.path)
        
        # Prepare prompt
        full_prompt = question
        if context_text:
            full_prompt = f"Question: {question}\n\nRelevant Context:{context_text}"
        
        # Ask Grok
        response = await self.grok_client.ask(
            prompt=full_prompt,
            stream=stream
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
        """Handle grok_discuss tool call."""
        topic = arguments["topic"]
        max_iterations = arguments.get("max_iterations", 3)
        use_baseline = arguments.get("use_baseline", True)
        expert_mode = arguments.get("expert_mode", False)
        continue_session = arguments.get("continue_session")
        
        # Create or continue session
        if continue_session:
            session = await self.session_manager.get_session(continue_session)
            if not session:
                raise ValueError(f"Session {continue_session} not found")
        else:
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
        baseline_path = None
        if use_baseline and not session.has_baseline:
            baseline = await self.baseline_generator.generate(
                topic=topic,
                analysis=analysis,
                context_items=context_items,
                use_expert_mode=expert_mode
            )
            
            # Save baseline
            baseline_path = await self.storage_manager.save_baseline(
                session_id=session.id,
                baseline=baseline,
                topic=topic
            )
            
            # Update session
            session.has_baseline = True
            session.baseline_path = baseline_path
            await self.session_manager.update_session(session.id)
        
        # First iteration prompt
        if use_baseline and baseline_path:
            initial_prompt = f"""Based on the following baseline analysis, please provide your insights on:
{topic}

Baseline Document:
{baseline}

Please provide a comprehensive response addressing the key questions and requirements outlined."""
        else:
            initial_prompt = f"""Please provide comprehensive insights on the following topic:
{topic}

Consider technical requirements, best practices, potential challenges, and implementation approaches."""
        
        # Get initial response
        response = await self.grok_client.ask(
            prompt=initial_prompt,
            stream=True
        )
        
        # Update session with response
        await self.session_manager.update_session(
            session_id=session.id,
            response=response,
            iteration_complete=True
        )
        
        # Save response
        await self.storage_manager.save_response(
            session_id=session.id,
            response=response.content,
            iteration=1,
            metadata={
                "topic": topic,
                "has_baseline": use_baseline
            }
        )
        
        return {
            "session_id": session.id,
            "status": "active",
            "iterations_completed": 1,
            "baseline_generated": use_baseline,
            "baseline_path": baseline_path,
            "initial_response": response.content[:500] + "..." if len(response.content) > 500 else response.content
        }
    
    async def _handle_grok_continue(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_continue tool call."""
        session_id = arguments["session_id"]
        user_input = arguments["input"]
        include_new_context = arguments.get("include_new_context", False)
        
        # Get session
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "active":
            raise ValueError(f"Session {session_id} is not active (status: {session.status})")
        
        if session.iterations_completed >= session.max_iterations:
            raise ValueError(f"Session {session_id} has reached maximum iterations")
        
        # Build conversation history
        conversation = "Previous discussion:\n"
        for resp in session.responses[-2:]:  # Last 2 responses for context
            conversation += f"\nIteration {resp['iteration']}:\n{resp['content'][:500]}...\n"
        
        # Add new context if requested
        context_text = ""
        if include_new_context:
            analysis = await self.context_analyzer.analyze_question(user_input)
            context_items = await self.context_analyzer.gather_context(analysis)
            for item in context_items[:3]:  # Top 3 context items
                context_text += f"\nAdditional context from {item.path}:\n{item.content[:500]}...\n"
        
        # Prepare follow-up prompt
        follow_up_prompt = f"""{conversation}

User follow-up: {user_input}
{context_text if context_text else ''}

Please provide a focused response addressing the follow-up question while building on the previous discussion."""
        
        # Get response
        response = await self.grok_client.ask(
            prompt=follow_up_prompt,
            stream=True
        )
        
        # Update session
        iteration = session.iterations_completed + 1
        await self.session_manager.update_session(
            session_id=session_id,
            response=response,
            iteration_complete=True
        )
        
        # Save response
        await self.storage_manager.save_response(
            session_id=session_id,
            response=response.content,
            iteration=iteration,
            metadata={
                "user_input": user_input,
                "new_context_added": include_new_context
            }
        )
        
        return {
            "response": response.content,
            "iteration": iteration,
            "session_id": session_id,
            "remaining_iterations": session.max_iterations - iteration,
            "tokens_used": response.tokens_used
        }
    
    async def _handle_grok_export_problem(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_export_problem tool call."""
        title = arguments["title"]
        description = arguments["description"]
        error_messages = arguments.get("error_messages", "")
        code_files = arguments.get("code_files", [])
        include_git = arguments.get("include_git", False)
        send_to_grok = arguments.get("send_to_grok", True)
        
        # Create problem document
        document = f"""# Problem Export: {title}

## Description
{description}

## Timestamp
{datetime.now().isoformat()}
"""
        
        # Add error messages if provided
        if error_messages:
            document += f"""
## Error Messages
```
{error_messages}
```
"""
        
        # Add code files
        if code_files:
            document += "\n## Relevant Code\n"
            for file_info in code_files:
                file_path = file_info["path"]
                start_line = file_info.get("start_line", 1)
                end_line = file_info.get("end_line", -1)
                
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        if end_line == -1:
                            end_line = len(lines)
                        
                        code_snippet = ''.join(lines[start_line-1:end_line])
                        document += f"\n### {file_path} (lines {start_line}-{end_line})\n```\n{code_snippet}\n```\n"
                except Exception as e:
                    document += f"\n### {file_path}\nError reading file: {e}\n"
        
        # Add git info if requested
        if include_git:
            import subprocess
            try:
                git_status = subprocess.run(
                    ["git", "status", "-s"],
                    capture_output=True,
                    text=True
                ).stdout
                
                git_log = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    capture_output=True,
                    text=True
                ).stdout
                
                document += f"""
## Git Information

### Status
```
{git_status}
```

### Recent Commits
```
{git_log}
```
"""
            except Exception as e:
                logger.warning(f"Failed to get git info: {e}")
        
        # Create session
        session_id = self.session_manager.generate_session_id(prefix="problem")
        
        # Save export
        export_path = self.storage_path / f"problem_{session_id}.md"
        with open(export_path, 'w') as f:
            f.write(document)
        
        # Send to Grok if requested
        grok_response = None
        if send_to_grok:
            prompt = f"""Please analyze the following problem and provide solutions:

{document}

Please provide:
1. Root cause analysis
2. Recommended solution approach
3. Step-by-step implementation guide
4. Potential pitfalls to avoid"""
            
            response = await self.grok_client.ask(prompt=prompt, stream=True)
            grok_response = response.content
            
            # Save response
            await self.storage_manager.save_response(
                session_id=session_id,
                response=grok_response,
                metadata={
                    "problem_title": title,
                    "export_path": str(export_path)
                }
            )
        
        return {
            "export_path": str(export_path),
            "session_id": session_id,
            "response": grok_response if grok_response else "Problem exported successfully",
            "sent_to_grok": send_to_grok
        }
    
    async def _handle_grok_list_sessions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_list_sessions tool call."""
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
    
    async def _handle_grok_get_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grok_get_response tool call."""
        session_id = arguments["session_id"]
        include_baseline = arguments.get("include_baseline", False)
        iteration = arguments.get("iteration")
        
        # Get session
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Prepare response data
        result = {
            "session_id": session_id,
            "topic": session.topic,
            "status": session.status,
            "iterations_completed": session.iterations_completed,
            "total_tokens": session.total_tokens
        }
        
        # Add responses
        if iteration is not None:
            # Get specific iteration
            for resp in session.responses:
                if resp["iteration"] == iteration:
                    result["response"] = resp["content"]
                    break
        else:
            # Get all responses
            result["responses"] = [r["content"] for r in session.responses]
        
        # Add baseline if requested
        if include_baseline and session.baseline_path:
            try:
                with open(session.baseline_path, 'r') as f:
                    result["baseline"] = f.read()
            except Exception as e:
                logger.error(f"Failed to read baseline: {e}")
        
        # Add quality scores if available
        if session.quality_scores:
            result["average_quality"] = sum(session.quality_scores) / len(session.quality_scores)
        
        return result
    
    async def run(self):
        """Run the MCP server."""
        try:
            logger.info("Starting Grok MCP Server...")
            
            # Start server
            async with self.server.run():
                logger.info("Grok MCP Server is running")
                
                # Keep server running
                while True:
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            # Cleanup
            logger.info("Cleaning up...")
            await self.session_manager.cleanup_inactive_sessions()


async def main():
    """Main entry point."""
    server = GrokMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())