"""
Base class for MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self, grok_client):
        """Initialize the tool with a Grok client."""
        self.grok_client = grok_client
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for tool inputs."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool with given arguments."""
        pass
    
    def to_mcp_tool(self) -> Dict[str, Any]:
        """Convert to MCP tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }