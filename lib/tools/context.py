"""
Context-aware question tool.
"""

from pathlib import Path
from typing import Any, Dict, List
from .base import BaseTool
from .context_loader import ContextLoader
import logging

logger = logging.getLogger(__name__)


class AskWithContextTool(BaseTool):
    """Tool for asking questions with file/code context."""
    
    @property
    def name(self) -> str:
        return "grok_ask_with_context"
    
    @property
    def description(self) -> str:
        return "Ask Grok a question with file/code context"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask"
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
                }
            },
            "required": ["question"]
        }
    
    async def execute(self, question: str, context_files: List[str] = None,
                     context_type: str = "general", max_context_lines: int = 100,
                     max_total_context_lines: int = 2000000, **kwargs) -> str:
        """Execute with context."""
        try:
            # Build context from files
            context = ""
            metadata = {}
            if context_files:
                context, metadata = ContextLoader.load_context(
                    context_files,
                    max_lines_per_file=max_context_lines,
                    max_total_lines=max_total_context_lines,
                    context_type=context_type
                )
            
            # Build the prompt
            prompt = self._build_contextual_prompt(question, context, context_type)
            
            # Get response
            response = await self.grok_client.ask(prompt=prompt, stream=False)
            
            # Add metadata info if relevant
            result = response.content
            if metadata and metadata.get('files_processed', 0) > 0:
                result += f"\n\n[Context: {metadata['files_processed']} files, {metadata.get('total_lines', 0)} lines]"
                if metadata.get('errors'):
                    result += f"\n[Errors: {'; '.join(metadata['errors'])}]"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in context-aware ask: {e}")
            return f"Error: {str(e)}"
    
    
    def _build_contextual_prompt(self, question: str, context: str, context_type: str) -> str:
        """Build a prompt with context."""
        if not context:
            return question
        
        if context_type == "code":
            prompt = f"Given the following code:\n{context}\n\n{question}"
        elif context_type == "docs":
            prompt = f"Based on this documentation:\n{context}\n\n{question}"
        else:
            prompt = f"Context:\n{context}\n\nQuestion: {question}"
        
        return prompt