"""
Context-aware question tool.
"""

from pathlib import Path
from typing import Any, Dict, List
from .base import BaseTool
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
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File path"},
                                    "from": {"type": "integer", "description": "Start line number (1-based)", "minimum": 1},
                                    "to": {"type": "integer", "description": "End line number (1-based)", "minimum": 1}
                                },
                                "required": ["path"]
                            }
                        ]
                    },
                    "description": "List of file paths or objects with path and line ranges {path, from?, to?}"
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
                }
            },
            "required": ["question"]
        }
    
    async def execute(self, question: str, context_files: List[str] = None,
                     context_type: str = "general", max_context_lines: int = 100, **kwargs) -> str:
        """Execute with context."""
        try:
            # Build context from files
            context = ""
            if context_files:
                context = self._load_context_files(context_files, max_context_lines)
            
            # Build the prompt
            prompt = self._build_contextual_prompt(question, context, context_type)
            
            # Get response
            response = await self.grok_client.ask(prompt=prompt, stream=False)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error in context-aware ask: {e}")
            return f"Error: {str(e)}"
    
    def _load_context_files(self, file_specs, max_lines: int) -> str:
        """Load content from context files with optional line ranges."""
        context_parts = []
        
        for file_spec in file_specs:
            try:
                # Parse file specification
                if isinstance(file_spec, str):
                    # Simple string path
                    file_path = file_spec
                    from_line = None
                    to_line = None
                elif isinstance(file_spec, dict):
                    # Object with path and optional line ranges
                    file_path = file_spec['path']
                    from_line = file_spec.get('from')
                    to_line = file_spec.get('to')
                else:
                    logger.warning(f"Invalid file specification: {file_spec}")
                    continue
                
                path = Path(file_path)
                if not path.exists():
                    context_parts.append(f"\n--- File: {file_path} ---\n[File not found]\n--- End of {file_path} ---\n")
                    continue
                
                # Read file content
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Apply line range if specified
                original_line_count = len(lines)
                if from_line is not None or to_line is not None:
                    # Convert to 0-based indexing
                    start_idx = (from_line - 1) if from_line is not None else 0
                    end_idx = to_line if to_line is not None else len(lines)
                    
                    # Validate ranges
                    start_idx = max(0, min(start_idx, len(lines) - 1))
                    end_idx = max(start_idx + 1, min(end_idx, len(lines)))
                    
                    lines = lines[start_idx:end_idx]
                    range_info = f" (lines {start_idx + 1}-{end_idx})"
                else:
                    # Apply max_lines truncation only if no specific range is given
                    if len(lines) > max_lines:
                        lines = lines[:max_lines]
                    range_info = ""
                
                # Check if truncated by max_lines (only when no specific range)
                truncated = (from_line is None and to_line is None and 
                           original_line_count > max_lines)
                
                # Format context
                content = ''.join(lines)
                context_part = f"\n--- File: {file_path}{range_info} ---\n{content}\n--- End of {file_path} ---"
                
                if truncated:
                    context_part += f"\n[Truncated to {max_lines} lines of {original_line_count} total]"
                elif from_line is not None or to_line is not None:
                    context_part += f"\n[Showing {len(lines)} lines of {original_line_count} total]"
                
                context_parts.append(context_part)
                
            except Exception as e:
                logger.error(f"Error reading {file_spec}: {e}")
                context_parts.append(f"\n--- File: {file_spec} ---\n[Error reading file: {str(e)}]\n--- End of file ---\n")
        
        return ''.join(context_parts) if context_parts else ""
    
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