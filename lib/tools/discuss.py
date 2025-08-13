"""
Discussion tool for multi-turn conversations.
"""

from typing import Any, Dict
from .base import BaseTool
from .session import SessionManager
import logging

logger = logging.getLogger(__name__)


class DiscussTool(BaseTool):
    """Tool for extended discussions with Grok."""
    
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
                }
            },
            "required": ["topic"]
        }
    
    async def execute(self, topic: str, context: str = None, 
                     max_turns: int = 3, expert_mode: bool = False, **kwargs) -> str:
        """Start a discussion."""
        try:
            # Create a new session
            session_id = self.session_manager.create_session(topic)
            
            # Build initial prompt
            initial_prompt = f"Let's discuss: {topic}"
            if context:
                initial_prompt += f"\n\nContext: {context}"
            if expert_mode:
                initial_prompt += "\n\nPlease provide expert-level insights with multiple perspectives."
            
            # Add initial user message
            self.session_manager.add_message(session_id, "user", initial_prompt)
            
            # Start the discussion
            result = f"Starting discussion on: {topic}\n"
            result += f"Session ID: {session_id}\n"
            result += f"Max turns: {max_turns}\n"
            result += "=" * 50 + "\n\n"
            
            messages = [{"role": "user", "content": initial_prompt}]
            
            for turn in range(max_turns):
                # Get Grok's response
                response = await self.grok_client.ask_with_history(
                    messages=messages,
                    stream=False
                )
                
                # Add to session
                self.session_manager.add_message(session_id, "assistant", response.content)
                messages.append({"role": "assistant", "content": response.content})
                
                result += f"Turn {turn + 1}:\n{response.content}\n\n"
                
                # Generate follow-up question if not last turn
                if turn < max_turns - 1:
                    follow_up = self._generate_follow_up(response.content, expert_mode)
                    self.session_manager.add_message(session_id, "user", follow_up)
                    messages.append({"role": "user", "content": follow_up})
                    result += f"Follow-up: {follow_up}\n\n"
            
            # Close the session
            self.session_manager.close_session(session_id)
            result += f"\nDiscussion completed. Session ID: {session_id}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in discussion: {e}")
            return f"Error: {str(e)}"
    
    def _generate_follow_up(self, response: str, expert_mode: bool) -> str:
        """Generate a follow-up question based on the response."""
        if expert_mode:
            return "Can you elaborate on the technical implications and potential edge cases?"
        else:
            return "Can you provide more details or examples?"