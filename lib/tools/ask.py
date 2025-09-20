"""
Basic ask tool - backward compatible with simple_mcp.py.
"""

from typing import Any, Dict
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class AskTool(BaseTool):
    """Simple question-answer tool."""
    
    @property
    def name(self) -> str:
        return "grok_ask"
    
    @property
    def description(self) -> str:
        return "Ask Grok a question"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use",
                    "enum": ["grok-4-fast-reasoning", "grok-4-0709", "grok-2-1212", "grok-2-vision", "grok-beta"],
                    "default": "grok-4-fast-reasoning"
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for response",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "default": 0.7
                },
                "stream": {
                    "type": "boolean",
                    "description": "Stream the response",
                    "default": False
                }
            },
            "required": ["question"]
        }
    
    async def execute(self, question: str, model: str = None, 
                     temperature: float = None, stream: bool = False, **kwargs) -> str:
        """Execute the ask tool."""
        try:
            # Use provided parameters or defaults
            actual_model = model or "grok-4-fast-reasoning"
            actual_temp = temperature if temperature is not None else 0.7
            
            # For now, ignore streaming (Phase 2)
            response = await self.grok_client.ask(
                prompt=question,
                stream=False  # Will implement streaming in Phase 2
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error in grok_ask: {e}")
            # Return error message instead of raising
            return f"Error: {str(e)}"