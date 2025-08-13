"""
Storage Manager - Local persistence for sessions, responses, and baselines.
"""

import json
import os
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages local storage for Grok discussions."""
    
    def __init__(self, storage_path: str = "./grok_discussions"):
        """Initialize storage manager.
        
        Args:
            storage_path: Base path for storage directories
        """
        self.storage_path = Path(storage_path)
        self.sessions_path = self.storage_path / "sessions"
        self.responses_path = self.storage_path / "responses"
        self.baselines_path = self.storage_path / "baselines"
        self.metadata_file = self.storage_path / "metadata.json"
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
        
    def _ensure_directories(self):
        """Ensure all storage directories exist."""
        for path in [self.sessions_path, self.responses_path, self.baselines_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file or create new."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
        
        # Initialize new metadata
        return {
            "version": "1.0.0",
            "created": datetime.now().isoformat(),
            "sessions": {},
            "total_sessions": 0,
            "total_responses": 0,
            "index": {}  # For search functionality
        }
    
    async def save_metadata(self):
        """Save metadata to file."""
        try:
            async with aiofiles.open(self.metadata_file, 'w') as f:
                await f.write(json.dumps(self.metadata, indent=2))
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> str:
        """Save a session to storage.
        
        Args:
            session_id: Unique session identifier
            session_data: Session data to save
            
        Returns:
            Path to saved session file
        """
        file_path = self.sessions_path / f"{session_id}.json"
        
        try:
            # Add timestamp if not present
            if "saved_at" not in session_data:
                session_data["saved_at"] = datetime.now().isoformat()
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
            
            # Update metadata
            self.metadata["sessions"][session_id] = {
                "path": str(file_path),
                "saved_at": session_data["saved_at"],
                "topic": session_data.get("topic", "Unknown")
            }
            self.metadata["total_sessions"] += 1
            await self.save_metadata()
            
            logger.info(f"Saved session {session_id} to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            raise
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from storage.
        
        Args:
            session_id: Session identifier to load
            
        Returns:
            Session data or None if not found
        """
        file_path = self.sessions_path / f"{session_id}.json"
        
        if not file_path.exists():
            logger.warning(f"Session {session_id} not found")
            return None
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    async def save_response(
        self,
        session_id: str,
        response: str,
        iteration: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a Grok response.
        
        Args:
            session_id: Associated session ID
            response: Response content
            iteration: Iteration number in discussion
            metadata: Additional metadata
            
        Returns:
            Path to saved response file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"response_{session_id}_{iteration}_{timestamp}.md"
        file_path = self.responses_path / filename
        
        try:
            # Prepare response document
            document = f"# Grok Response\n\n"
            document += f"**Session**: {session_id}\n"
            document += f"**Iteration**: {iteration}\n"
            document += f"**Timestamp**: {datetime.now().isoformat()}\n"
            
            if metadata:
                document += f"\n## Metadata\n"
                for key, value in metadata.items():
                    document += f"- **{key}**: {value}\n"
            
            document += f"\n## Response\n\n{response}"
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(document)
            
            # Update metadata
            self.metadata["total_responses"] += 1
            
            # Add to search index
            response_hash = hashlib.md5(response.encode()).hexdigest()[:8]
            if "responses" not in self.metadata["index"]:
                self.metadata["index"]["responses"] = {}
            
            self.metadata["index"]["responses"][response_hash] = {
                "session_id": session_id,
                "iteration": iteration,
                "path": str(file_path),
                "timestamp": timestamp
            }
            
            await self.save_metadata()
            
            logger.info(f"Saved response for session {session_id} to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save response: {e}")
            raise
    
    async def save_baseline(
        self,
        session_id: str,
        baseline: str,
        topic: str
    ) -> str:
        """Save a baseline document.
        
        Args:
            session_id: Associated session ID
            baseline: Baseline document content
            topic: Discussion topic
            
        Returns:
            Path to saved baseline file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"baseline_{session_id}_{timestamp}.md"
        file_path = self.baselines_path / filename
        
        try:
            # Prepare baseline document
            document = f"# Baseline Document\n\n"
            document += f"**Topic**: {topic}\n"
            document += f"**Session**: {session_id}\n"
            document += f"**Generated**: {datetime.now().isoformat()}\n"
            document += f"\n---\n\n{baseline}"
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(document)
            
            # Add to index
            if "baselines" not in self.metadata["index"]:
                self.metadata["index"]["baselines"] = {}
            
            self.metadata["index"]["baselines"][session_id] = {
                "topic": topic,
                "path": str(file_path),
                "timestamp": timestamp
            }
            
            await self.save_metadata()
            
            logger.info(f"Saved baseline for session {session_id} to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            raise
    
    async def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List stored sessions.
        
        Args:
            status: Filter by status (active/completed/failed)
            limit: Maximum sessions to return
            
        Returns:
            List of session metadata
        """
        sessions = []
        
        for session_id, info in self.metadata.get("sessions", {}).items():
            # Load session to check status
            session_data = await self.load_session(session_id)
            if session_data:
                if status and session_data.get("status") != status:
                    continue
                    
                sessions.append({
                    "id": session_id,
                    "topic": info.get("topic", "Unknown"),
                    "status": session_data.get("status", "unknown"),
                    "created": session_data.get("created"),
                    "iterations": session_data.get("iterations_completed", 0),
                    "path": info.get("path")
                })
        
        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x.get("created", ""), reverse=True)
        
        return sessions[:limit]
    
    async def search_responses(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search through stored responses.
        
        Args:
            query: Search query
            session_id: Optional filter by session
            
        Returns:
            List of matching responses with metadata
        """
        results = []
        query_lower = query.lower()
        
        # Search through response files
        for response_file in self.responses_path.glob("*.md"):
            try:
                async with aiofiles.open(response_file, 'r') as f:
                    content = await f.read()
                    
                if query_lower in content.lower():
                    # Extract session ID from filename
                    parts = response_file.stem.split("_")
                    if len(parts) >= 3:
                        file_session_id = parts[1]
                        
                        if session_id and file_session_id != session_id:
                            continue
                        
                        results.append({
                            "file": str(response_file),
                            "session_id": file_session_id,
                            "snippet": self._extract_snippet(content, query_lower)
                        })
                        
            except Exception as e:
                logger.error(f"Error searching file {response_file}: {e}")
        
        return results
    
    def _extract_snippet(self, content: str, query: str, context_chars: int = 100) -> str:
        """Extract a snippet around the query match.
        
        Args:
            content: Full content
            query: Search query
            context_chars: Characters of context on each side
            
        Returns:
            Snippet with query highlighted
        """
        content_lower = content.lower()
        index = content_lower.find(query)
        
        if index == -1:
            return ""
        
        start = max(0, index - context_chars)
        end = min(len(content), index + len(query) + context_chars)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet
    
    async def cleanup_old_sessions(self, days: int = 30):
        """Clean up sessions older than specified days.
        
        Args:
            days: Number of days to keep sessions
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_count = 0
        
        for session_id, info in list(self.metadata.get("sessions", {}).items()):
            try:
                saved_at = datetime.fromisoformat(info.get("saved_at", ""))
                if saved_at < cutoff_date:
                    # Remove session file
                    session_file = Path(info.get("path", ""))
                    if session_file.exists():
                        session_file.unlink()
                    
                    # Remove from metadata
                    del self.metadata["sessions"][session_id]
                    removed_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")
        
        if removed_count > 0:
            await self.save_metadata()
            logger.info(f"Cleaned up {removed_count} old sessions")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        total_size = 0
        file_count = 0
        
        for path in [self.sessions_path, self.responses_path, self.baselines_path]:
            for file_path in path.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        
        return {
            "total_sessions": self.metadata.get("total_sessions", 0),
            "total_responses": self.metadata.get("total_responses", 0),
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }