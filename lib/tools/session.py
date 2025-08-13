"""
Session management tools for multi-turn conversations.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions."""
    
    def __init__(self, storage_path: Path = None):
        """Initialize session manager."""
        self.storage_path = storage_path or Path("./sessions")
        self.storage_path.mkdir(exist_ok=True)
        self.sessions = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load existing sessions from disk."""
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    self.sessions[session['id']] = session
            except Exception as e:
                logger.error(f"Failed to load session {session_file}: {e}")
    
    def create_session(self, topic: str) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "status": "active"
        }
        self.sessions[session_id] = session
        self._save_session(session_id)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to a session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        self.sessions[session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def list_sessions(self, status: str = None, limit: int = 10) -> List[Dict]:
        """List sessions with optional filtering."""
        sessions = list(self.sessions.values())
        
        if status:
            sessions = [s for s in sessions if s.get("status") == status]
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return sessions[:limit]
    
    def _save_session(self, session_id: str):
        """Save a session to disk."""
        session = self.sessions[session_id]
        session_file = self.storage_path / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session, f, indent=2)
    
    def close_session(self, session_id: str):
        """Mark a session as completed."""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "completed"
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
            self._save_session(session_id)


class ListSessionsTool(BaseTool):
    """Tool to list conversation sessions."""
    
    def __init__(self, grok_client, session_manager: SessionManager):
        super().__init__(grok_client)
        self.session_manager = session_manager
    
    @property
    def name(self) -> str:
        return "grok_list_sessions"
    
    @property
    def description(self) -> str:
        return "List conversation sessions"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status",
                    "enum": ["active", "completed", "failed", "paused"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum sessions to return",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                }
            }
        }
    
    async def execute(self, status: str = None, limit: int = 10, **kwargs) -> str:
        """List sessions."""
        try:
            sessions = self.session_manager.list_sessions(status, limit)
            
            if not sessions:
                return "No sessions found."
            
            result = f"Found {len(sessions)} session(s):\n\n"
            for session in sessions:
                result += f"ID: {session['id']}\n"
                result += f"Topic: {session['topic']}\n"
                result += f"Status: {session['status']}\n"
                result += f"Messages: {len(session['messages'])}\n"
                result += f"Updated: {session['updated_at']}\n"
                result += "-" * 40 + "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return f"Error: {str(e)}"


class ContinueSessionTool(BaseTool):
    """Tool to continue a conversation session."""
    
    def __init__(self, grok_client, session_manager: SessionManager):
        super().__init__(grok_client)
        self.session_manager = session_manager
    
    @property
    def name(self) -> str:
        return "grok_continue_session"
    
    @property
    def description(self) -> str:
        return "Continue a previous conversation"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to continue"
                },
                "message": {
                    "type": "string",
                    "description": "Your message to continue the conversation"
                }
            },
            "required": ["session_id", "message"]
        }
    
    async def execute(self, session_id: str, message: str, **kwargs) -> str:
        """Continue a session."""
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                return f"Session {session_id} not found"
            
            # Add user message
            self.session_manager.add_message(session_id, "user", message)
            
            # Build conversation history
            messages = [{"role": msg["role"], "content": msg["content"]} 
                       for msg in session["messages"]]
            
            # Get response from Grok
            response = await self.grok_client.ask_with_history(
                messages=messages,
                stream=False
            )
            
            # Add assistant response
            self.session_manager.add_message(session_id, "assistant", response.content)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error continuing session: {e}")
            return f"Error: {str(e)}"