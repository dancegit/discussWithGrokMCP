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
                    "items": {"type": "string"},
                    "description": "List of file paths to include as context"
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
                for file_path in context_files:
                    context += self._read_file_context(file_path, max_context_lines)
            
            # Build the prompt
            prompt = self._build_contextual_prompt(question, context, context_type)
            
            # Get response
            response = await self.grok_client.ask(prompt=prompt, stream=False)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error in context-aware ask: {e}")
            return f"Error: {str(e)}"
    
    def _read_file_context(self, file_path: str, max_lines: int) -> str:
        """Read context from a file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"\n[File not found: {file_path}]\n"
            
            with open(path, 'r') as f:
                lines = f.readlines()[:max_lines]
                content = ''.join(lines)
                
            return f"\n--- File: {file_path} ---\n{content}\n--- End of {file_path} ---\n"
            
        except Exception as e:
            return f"\n[Error reading {file_path}: {e}]\n"
    
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