"""
Discussion tool for multi-turn conversations with file context support and pagination.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import BaseTool
from .session import SessionManager
from .context_loader import ContextLoader
import logging

logger = logging.getLogger(__name__)


class DiscussTool(BaseTool):
    """Tool for extended discussions with Grok, supporting file context and pagination."""
    
    def __init__(self, grok_client, session_manager: SessionManager):
        super().__init__(grok_client)
        self.session_manager = session_manager
    
    @property
    def name(self) -> str:
        return "grok_discuss"
    
    @property
    def description(self) -> str:
        return "Start an extended discussion with Grok"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Discussion topic"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context for the discussion"
                },
                "context_files": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string", "description": "File path, directory path, or glob pattern"},
                            {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File path, directory path, or glob pattern"},
                                    "from": {"type": "integer", "description": "Start line number (1-based) for files", "minimum": 1},
                                    "to": {"type": "integer", "description": "End line number (1-based) for files", "minimum": 1},
                                    "recursive": {"type": "boolean", "description": "Recursive directory traversal", "default": True},
                                    "extensions": {
                                        "type": "array", 
                                        "items": {"type": "string"},
                                        "description": "File extensions to include (e.g., ['.py', '.js'])"
                                    },
                                    "exclude": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Patterns to exclude (e.g., ['test_*', '*.pyc'])"
                                    },
                                    "pattern": {"type": "string", "description": "Glob pattern for file matching"}
                                },
                                "required": ["path"]
                            }
                        ]
                    },
                    "description": "List of files, directories, or patterns. Supports: file paths, directories (with recursive/extension options), glob patterns ('**/*.py'), and line ranges"
                },
                "context_type": {
                    "type": "string",
                    "description": "Type of context",
                    "enum": ["code", "docs", "general"],
                    "default": "general"
                },
                "max_context_lines": {
                    "type": "integer",
                    "description": "Maximum lines per file",
                    "default": 100
                },
                "max_total_context_lines": {
                    "type": "integer",
                    "description": "Maximum total lines across all files",
                    "default": 2000000
                },
                "max_turns": {
                    "type": "integer",
                    "description": "Maximum conversation turns",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3
                },
                "expert_mode": {
                    "type": "boolean",
                    "description": "Include expert perspectives",
                    "default": False
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for paginated results (1-based)",
                    "minimum": 1,
                    "default": 1
                },
                "turns_per_page": {
                    "type": "integer",
                    "description": "Number of turns to include per page",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 2
                },
                "paginate": {
                    "type": "boolean",
                    "description": "Enable pagination (default: true)",
                    "default": True
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID to continue an existing discussion"
                }
            },
            "required": []
        }
    
    async def execute(self, topic: str = None, context: str = None, 
                     context_files: List[str] = None,
                     context_type: str = "general",
                     max_context_lines: int = 100,
                     max_total_context_lines: int = 2000000,
                     max_turns: int = 3, expert_mode: bool = False,
                     page: int = 1, turns_per_page: int = 2, 
                     paginate: bool = True, **kwargs) -> str:
        """Start a discussion with optional file context and pagination support."""
        try:
            # Create a new session or continue existing one
            session_id = kwargs.get('session_id')
            if not session_id:
                # Creating new session requires topic
                if not topic:
                    return "Error: 'topic' parameter is required when creating a new discussion"

                # Store pagination settings with the session
                pagination_settings = {
                    "turns_per_page": turns_per_page,
                    "max_turns": max_turns,
                    "paginate": paginate
                }
                session_id = self.session_manager.create_session(topic, pagination_settings)
                
                # Build file context if provided
                file_context = ""
                file_metadata = {}
                if context_files:
                    file_context, file_metadata = ContextLoader.load_context(
                        context_files,
                        max_lines_per_file=max_context_lines,
                        max_total_lines=max_total_context_lines,
                        context_type=context_type
                    )
                
                # Build initial prompt
                initial_prompt = f"Let's discuss: {topic}"
                
                # Add file context first if provided
                if file_context:
                    initial_prompt = self._build_contextual_prompt(initial_prompt, file_context, context_type)
                
                # Add additional context if provided
                if context:
                    initial_prompt += f"\n\nAdditional context: {context}"
                
                if expert_mode:
                    initial_prompt += "\n\nPlease provide expert-level insights with multiple perspectives."
                
                # Add initial user message
                self.session_manager.add_message(session_id, "user", initial_prompt)
                messages = [{"role": "user", "content": initial_prompt}]
            else:
                # Load existing session messages
                session = self.session_manager.get_session(session_id)
                if not session:
                    return f"Error: Session {session_id} not found"
                messages = session['messages']

                # Retrieve pagination settings from session if they exist
                if 'pagination' in session and session['pagination']:
                    stored_pagination = session['pagination']
                    # Use stored values if not explicitly provided
                    if 'turns_per_page' not in kwargs:
                        turns_per_page = stored_pagination.get('turns_per_page', turns_per_page)
                    if 'max_turns' not in kwargs:
                        max_turns = stored_pagination.get('max_turns', max_turns)
                    if 'paginate' not in kwargs:
                        paginate = stored_pagination.get('paginate', paginate)

                # Extract context_files from kwargs if continuing a session
                context_files = kwargs.get('context_files')
            
            # Calculate pagination
            if paginate:
                start_turn = (page - 1) * turns_per_page
                end_turn = min(start_turn + turns_per_page, max_turns)
                total_pages = (max_turns + turns_per_page - 1) // turns_per_page
                
                if start_turn >= max_turns:
                    return f"Error: Page {page} exceeds total pages ({total_pages})"
            else:
                start_turn = 0
                end_turn = max_turns
                total_pages = 1
            
            # Start the discussion
            result = f"Discussion on: {topic}\n"
            result += f"Session ID: {session_id}\n"
            
            if context_files:
                # Format context files for display
                file_list = []
                for file_spec in context_files:
                    if isinstance(file_spec, str):
                        file_list.append(file_spec)
                    elif isinstance(file_spec, dict):
                        path = file_spec['path']
                        if 'from' in file_spec or 'to' in file_spec:
                            from_line = file_spec.get('from', '?')
                            to_line = file_spec.get('to', '?')
                            file_list.append(f"{path}:{from_line}-{to_line}")
                        elif 'pattern' in file_spec:
                            file_list.append(f"Pattern: {file_spec['pattern']}")
                        elif 'recursive' in file_spec or 'extensions' in file_spec:
                            desc = path
                            if file_spec.get('recursive'):
                                desc += " (recursive)"
                            if 'extensions' in file_spec:
                                desc += f" [{', '.join(file_spec['extensions'])}]"
                            file_list.append(desc)
                        else:
                            file_list.append(path)
                result += f"Context: {', '.join(file_list)}\n"
                if file_metadata and 'files_processed' in file_metadata:
                    result += f"Files loaded: {file_metadata['files_processed']}, Total lines: {file_metadata.get('total_lines', 0)}\n"
            
            if paginate:
                result += f"Page {page} of {total_pages} (Turns {start_turn + 1}-{end_turn} of {max_turns})\n"
            else:
                result += f"Max turns: {max_turns}\n"
            
            result += "=" * 50 + "\n\n"
            
            # Get the current turn count from session
            current_turn_count = len([m for m in messages if m['role'] == 'assistant'])
            
            # Execute turns for this page
            for turn in range(start_turn, end_turn):
                # Skip if turn already exists
                if turn < current_turn_count:
                    # Get existing turn from messages
                    assistant_messages = [m for m in messages if m['role'] == 'assistant']
                    if turn < len(assistant_messages):
                        result += f"Turn {turn + 1}:\n{assistant_messages[turn]['content']}\n\n"
                        
                        # Add follow-up if exists
                        user_messages = [m for m in messages if m['role'] == 'user']
                        if turn + 1 < len(user_messages) - 1:  # -1 for initial prompt
                            result += f"Follow-up: {user_messages[turn + 2]['content']}\n\n"
                    continue
                
                # Generate new turn
                response = await self.grok_client.ask_with_history(
                    messages=messages,
                    stream=False
                )
                
                # Add to session
                self.session_manager.add_message(session_id, "assistant", response.content)
                messages.append({"role": "assistant", "content": response.content})
                
                result += f"Turn {turn + 1}:\n{response.content}\n\n"
                
                # Generate follow-up question if not last turn on this page
                if turn < end_turn - 1:
                    follow_up = self._generate_follow_up(response.content, expert_mode, context_files is not None)
                    self.session_manager.add_message(session_id, "user", follow_up)
                    messages.append({"role": "user", "content": follow_up})
                    result += f"Follow-up: {follow_up}\n\n"
            
            # Add pagination info and navigation
            if paginate:
                result += "\n" + "=" * 50 + "\n"
                result += f"Page {page} of {total_pages}\n"
                
                if page < total_pages:
                    result += f"\nTo continue, use: grok_discuss with session_id='{session_id}' and page={page + 1}"
                else:
                    # Close the session only when reaching the last page
                    self.session_manager.close_session(session_id)
                    result += f"\nDiscussion completed. Session ID: {session_id}"
            else:
                # Close the session for non-paginated discussions
                self.session_manager.close_session(session_id)
                result += f"\nDiscussion completed. Session ID: {session_id}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in discussion: {e}")
            return f"Error: {str(e)}"
    
    
    def _build_contextual_prompt(self, base_prompt: str, file_context: str, context_type: str) -> str:
        """Build a prompt with file context."""
        if not file_context:
            return base_prompt
        
        if context_type == "code":
            prompt = f"Given the following code:\n{file_context}\n\n{base_prompt}"
        elif context_type == "docs":
            prompt = f"Based on this documentation:\n{file_context}\n\n{base_prompt}"
        else:
            prompt = f"Context:\n{file_context}\n\n{base_prompt}"
        
        return prompt
    
    def _generate_follow_up(self, response: str, expert_mode: bool, has_file_context: bool = False) -> str:
        """Generate a follow-up question based on the response."""
        if has_file_context:
            if expert_mode:
                return "How does this relate to the code structure and what optimizations or refactoring would you suggest?"
            else:
                return "Can you explain how this applies to the specific code we're discussing?"
        else:
            if expert_mode:
                return "Can you elaborate on the technical implications and potential edge cases?"
            else:
                return "Can you provide more details or examples?"