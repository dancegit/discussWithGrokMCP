"""
Session Manager - State tracking with checkpointing and crash recovery.
"""

import asyncio
import uuid
import time
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging
import json

from .storage_manager import StorageManager
from .grok_client import GrokResponse

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a discussion session."""
    id: str
    topic: str
    status: str = "active"  # active, completed, failed, paused
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    max_iterations: int = 3
    iterations_completed: int = 0
    has_baseline: bool = False
    baseline_path: Optional[str] = None
    responses: List[Dict[str, Any]] = field(default_factory=list)
    context_files: List[str] = field(default_factory=list)
    total_tokens: int = 0
    quality_scores: List[float] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    last_checkpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(**data)


class SessionManager:
    """Manages discussion sessions with checkpointing and recovery."""
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize session manager.
        
        Args:
            storage_manager: Storage manager instance
        """
        self.storage = storage_manager
        self.active_sessions: Dict[str, Session] = {}
        self.checkpoint_interval = 60  # seconds
        self._checkpoint_tasks: Dict[str, asyncio.Task] = {}
        self.max_active_sessions = int(os.getenv('MAX_ACTIVE_SESSIONS', '100'))  # Max sessions in memory
        self.session_access_times: Dict[str, datetime] = {}  # Track last access for LRU
        self._cleanup_task = None  # Periodic cleanup task
        self._start_cleanup_task()  # Start periodic cleanup
        
    def generate_session_id(self, prefix: str = "session") -> str:
        """Generate a unique session ID.
        
        Args:
            prefix: Prefix for the session ID
            
        Returns:
            Unique session identifier
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{unique_id}"
    
    async def create_session(
        self,
        topic: str,
        max_iterations: int = 3,
        session_type: str = "discuss"
    ) -> Session:
        """Create a new discussion session.
        
        Args:
            topic: Discussion topic
            max_iterations: Maximum iterations allowed
            session_type: Type of session (discuss, ask, problem)
            
        Returns:
            Created session object
        """
        session_id = self.generate_session_id(prefix=session_type)
        
        session = Session(
            id=session_id,
            topic=topic,
            max_iterations=max_iterations,
            metadata={
                "type": session_type,
                "version": "1.0.0"
            }
        )
        
        # Check if we need to evict before adding
        await self._check_and_evict_sessions()
        
        # Add to active sessions
        self.active_sessions[session_id] = session
        self.session_access_times[session_id] = datetime.now()
        
        # Save initial state
        await self._save_session(session)
        
        # Start checkpoint task
        self._start_checkpoint_task(session_id)
        
        logger.info(f"Created session {session_id} for topic: {topic}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            # Update access time for LRU
            self.session_access_times[session_id] = datetime.now()
            return self.active_sessions[session_id]
        
        # Try to load from storage
        session_data = await self.storage.load_session(session_id)
        if session_data:
            # Check if we need to evict before loading
            await self._check_and_evict_sessions()
            
            session = Session.from_dict(session_data)
            self.active_sessions[session_id] = session
            self.session_access_times[session_id] = datetime.now()
            
            # Restart checkpoint task if session is active
            if session.status == "active":
                self._start_checkpoint_task(session_id)
            
            return session
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        response: Optional[GrokResponse] = None,
        iteration_complete: bool = False,
        status: Optional[str] = None
    ) -> Session:
        """Update session state.
        
        Args:
            session_id: Session identifier
            response: Grok response to add
            iteration_complete: Whether an iteration was completed
            status: New status for session
            
        Returns:
            Updated session object
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update response if provided
        if response:
            session.responses.append({
                "iteration": session.iterations_completed,
                "content": response.content,
                "tokens": response.tokens_used,
                "timestamp": response.timestamp
            })
            session.total_tokens += response.tokens_used
        
        # Update iteration count
        if iteration_complete:
            session.iterations_completed += 1
            
            # Check if max iterations reached
            if session.iterations_completed >= session.max_iterations:
                session.status = "completed"
        
        # Update status if provided
        if status:
            session.status = status
        
        # Save updated session
        await self._save_session(session)
        
        # Stop checkpoint task if session is no longer active
        if session.status != "active":
            self._stop_checkpoint_task(session_id)
        
        return session
    
    async def add_checkpoint(self, session_id: str) -> Dict[str, Any]:
        """Create a checkpoint for the session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Checkpoint data
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "iteration": session.iterations_completed,
            "status": session.status,
            "tokens_used": session.total_tokens,
            "responses_count": len(session.responses)
        }
        
        session.checkpoints.append(checkpoint)
        session.last_checkpoint = checkpoint["timestamp"]
        
        # Save session with checkpoint
        await self._save_session(session)
        
        logger.debug(f"Created checkpoint for session {session_id}")
        return checkpoint
    
    async def recover_session(self, session_id: str) -> Optional[Session]:
        """Recover a session from last checkpoint.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Recovered session or None if recovery fails
        """
        try:
            # Load session from storage
            session_data = await self.storage.load_session(session_id)
            if not session_data:
                logger.error(f"No saved data found for session {session_id}")
                return None
            
            session = Session.from_dict(session_data)
            
            # Check if recovery is needed
            if session.status == "active" and session.checkpoints:
                last_checkpoint = session.checkpoints[-1]
                logger.info(f"Recovering session {session_id} from checkpoint: {last_checkpoint['timestamp']}")
                
                # Restore state from checkpoint
                session.iterations_completed = last_checkpoint["iteration"]
                session.total_tokens = last_checkpoint["tokens_used"]
                
                # Mark as recovered
                session.metadata["recovered"] = True
                session.metadata["recovery_time"] = datetime.now().isoformat()
            
            # Add to active sessions
            self.active_sessions[session_id] = session
            
            # Restart checkpoint task if still active
            if session.status == "active":
                self._start_checkpoint_task(session_id)
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to recover session {session_id}: {e}")
            return None
    
    async def pause_session(self, session_id: str) -> Session:
        """Pause an active session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Paused session
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "active":
            raise ValueError(f"Cannot pause session in {session.status} state")
        
        session.status = "paused"
        session.metadata["paused_at"] = datetime.now().isoformat()
        
        # Create checkpoint before pausing
        await self.add_checkpoint(session_id)
        
        # Save and stop checkpoint task
        await self._save_session(session)
        self._stop_checkpoint_task(session_id)
        
        logger.info(f"Paused session {session_id}")
        return session
    
    async def resume_session(self, session_id: str) -> Session:
        """Resume a paused session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Resumed session
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "paused":
            raise ValueError(f"Cannot resume session in {session.status} state")
        
        session.status = "active"
        session.metadata["resumed_at"] = datetime.now().isoformat()
        
        # Save and restart checkpoint task
        await self._save_session(session)
        self._start_checkpoint_task(session_id)
        
        logger.info(f"Resumed session {session_id}")
        return session
    
    def calculate_quality_score(self, response: str) -> float:
        """Calculate quality score for a response.
        
        Args:
            response: Response content to score
            
        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        factors = 0
        
        # Length factor (longer responses often more detailed)
        if len(response) > 100:
            score += 0.2
            factors += 1
        
        # Code presence (indicates actionable content)
        if "```" in response:
            score += 0.3
            factors += 1
        
        # Structure (headers indicate organization)
        if "#" in response or "##" in response:
            score += 0.2
            factors += 1
        
        # Lists (indicate structured information)
        if "- " in response or "* " in response or "1. " in response:
            score += 0.15
            factors += 1
        
        # Specificity (technical terms)
        technical_terms = ["implement", "function", "class", "method", "algorithm", 
                          "optimize", "architecture", "performance", "security"]
        if any(term in response.lower() for term in technical_terms):
            score += 0.15
            factors += 1
        
        # Normalize score
        if factors > 0:
            return min(1.0, score)
        
        # Default score for minimal responses
        return 0.3
    
    async def _save_session(self, session: Session):
        """Save session to storage.
        
        Args:
            session: Session to save
        """
        await self.storage.save_session(session.id, session.to_dict())
    
    def _start_checkpoint_task(self, session_id: str):
        """Start periodic checkpoint task for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._checkpoint_tasks:
            return  # Task already running
        
        async def checkpoint_loop():
            """Periodic checkpoint loop."""
            while session_id in self.active_sessions:
                await asyncio.sleep(self.checkpoint_interval)
                
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    if session.status == "active":
                        await self.add_checkpoint(session_id)
        
        task = asyncio.create_task(checkpoint_loop())
        self._checkpoint_tasks[session_id] = task
    
    def _stop_checkpoint_task(self, session_id: str):
        """Stop checkpoint task for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._checkpoint_tasks:
            task = self._checkpoint_tasks[session_id]
            task.cancel()
            del self._checkpoint_tasks[session_id]
    
    async def _check_and_evict_sessions(self):
        """Check if eviction is needed and evict LRU sessions."""
        if len(self.active_sessions) >= self.max_active_sessions:
            # Find the least recently used session
            if self.session_access_times:
                lru_session_id = min(
                    self.session_access_times.keys(),
                    key=lambda k: self.session_access_times[k]
                )
                
                # Save before evicting
                if lru_session_id in self.active_sessions:
                    await self._save_session(self.active_sessions[lru_session_id])
                    
                    # Stop checkpoint task
                    self._stop_checkpoint_task(lru_session_id)
                    
                    # Remove from memory
                    del self.active_sessions[lru_session_id]
                    del self.session_access_times[lru_session_id]
                    
                    logger.info(f"Evicted LRU session {lru_session_id} to free memory")
    
    async def cleanup_inactive_sessions(self, timeout_hours: int = None):
        """Clean up inactive sessions.
        
        Args:
            timeout_hours: Hours of inactivity before cleanup
        """
        from datetime import timedelta
        
        if timeout_hours is None:
            timeout_hours = float(os.getenv('SESSION_INACTIVITY_TIMEOUT_HOURS', '2'))
        
        cutoff_time = datetime.now() - timedelta(hours=timeout_hours)
        sessions_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            # Check last access time
            if session_id in self.session_access_times:
                last_access = self.session_access_times[session_id]
                if last_access < cutoff_time and session.status != "active":
                    sessions_to_remove.append(session_id)
        
        # Remove inactive sessions
        for session_id in sessions_to_remove:
            # Save before removing
            await self._save_session(self.active_sessions[session_id])
            self._stop_checkpoint_task(session_id)
            del self.active_sessions[session_id]
            if session_id in self.session_access_times:
                del self.session_access_times[session_id]
            logger.info(f"Cleaned up inactive session {session_id}")
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions.
        
        Returns:
            List of active sessions
        """
        return [s for s in self.active_sessions.values() if s.status == "active"]
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {}
        
        avg_quality = sum(session.quality_scores) / len(session.quality_scores) if session.quality_scores else 0
        
        return {
            "id": session.id,
            "topic": session.topic,
            "status": session.status,
            "created": session.created,
            "iterations": f"{session.iterations_completed}/{session.max_iterations}",
            "total_tokens": session.total_tokens,
            "responses": len(session.responses),
            "checkpoints": len(session.checkpoints),
            "average_quality": round(avg_quality, 2),
            "has_baseline": session.has_baseline
        }
    
    def _start_cleanup_task(self):
        """Start periodic cleanup task for memory management."""
        async def periodic_cleanup():
            """Run cleanup periodically."""
            cleanup_interval_hours = float(os.getenv('MEMORY_CLEANUP_INTERVAL_HOURS', '1'))
            cleanup_interval_seconds = cleanup_interval_hours * 3600
            
            while True:
                try:
                    await asyncio.sleep(cleanup_interval_seconds)
                    
                    # Run cleanup for inactive sessions
                    await self.cleanup_inactive_sessions()
                    
                    # Log memory status
                    logger.info(f"Memory cleanup completed. Active sessions: {len(self.active_sessions)}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
        
        # Create and store the task
        self._cleanup_task = asyncio.create_task(periodic_cleanup())
    
    def stop_cleanup_task(self):
        """Stop the periodic cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()