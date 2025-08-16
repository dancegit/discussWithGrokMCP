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
            "required": ["topic"]
        }
    
    async def execute(self, topic: str, context: str = None, 
                     max_turns: int = 3, expert_mode: bool = False,
                     page: int = 1, turns_per_page: int = 2, 
                     paginate: bool = True, **kwargs) -> str:
        """Start a discussion with pagination support."""
        try:
            # Create a new session or continue existing one
            session_id = kwargs.get('session_id')
            if not session_id:
                session_id = self.session_manager.create_session(topic)
                
                # Build initial prompt
                initial_prompt = f"Let's discuss: {topic}"
                if context:
                    initial_prompt += f"\n\nContext: {context}"
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
                
                # Generate follow-up question if not last turn
                if turn < max_turns - 1:
                    follow_up = self._generate_follow_up(response.content, expert_mode)
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
    
    def _generate_follow_up(self, response: str, expert_mode: bool) -> str:
        """Generate a follow-up question based on the response."""
        if expert_mode:
            return "Can you elaborate on the technical implications and potential edge cases?"
        else:
            return "Can you provide more details or examples?"