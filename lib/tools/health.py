"""
Health check tool for monitoring server status.
"""

import time
from typing import Any, Dict
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class HealthCheckTool(BaseTool):
    """Tool for checking server and API health."""
    
    def __init__(self, grok_client):
        super().__init__(grok_client)
        self.start_time = time.time()
    
    @property
    def name(self) -> str:
        return "grok_health"
    
    @property
    def description(self) -> str:
        return "Check server and API health status"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verbose": {
                    "type": "boolean",
                    "description": "Include detailed diagnostics",
                    "default": False
                }
            }
        }
    
    async def execute(self, verbose: bool = False, **kwargs) -> str:
        """Check health status."""
        try:
            # Check server uptime
            uptime = int(time.time() - self.start_time)
            
            # Test API connectivity
            api_status = "unknown"
            latency_ms = -1
            
            start = time.time()
            try:
                response = await self.grok_client.ask(
                    prompt="ping",
                    max_tokens=1,
                    stream=False
                )
                api_status = "connected" if response else "error"
                latency_ms = int((time.time() - start) * 1000)
            except Exception as e:
                api_status = "disconnected"
                logger.error(f"API health check failed: {e}")
            
            # Build response
            health = {
                "server": "healthy",
                "api": api_status,
                "latency_ms": latency_ms,
                "uptime_seconds": uptime
            }
            
            if verbose:
                health["diagnostics"] = {
                    "version": "0.8.0",
                    "features": {
                        "streaming": True,
                        "sessions": True,
                        "context": True,
                        "caching": True
                    },
                    "limits": {
                        "max_context_tokens": 10000,
                        "max_session_turns": 10,
                        "cache_ttl_seconds": 3600
                    }
                }
            
            # Format as string
            result = f"Health Status:\n"
            result += f"  Server: {health['server']}\n"
            result += f"  API: {health['api']}\n"
            result += f"  Latency: {health['latency_ms']}ms\n"
            result += f"  Uptime: {health['uptime_seconds']}s\n"
            
            if verbose and "diagnostics" in health:
                result += "\nDiagnostics:\n"
                diag = health["diagnostics"]
                result += f"  Version: {diag['version']}\n"
                result += f"  Features: {', '.join(k for k, v in diag['features'].items() if v)}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return f"Health check failed: {str(e)}"