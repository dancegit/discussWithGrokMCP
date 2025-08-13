#!/usr/bin/env python3
"""
Integration tests for the enhanced MCP server.
"""

import sys
import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
import subprocess
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMCPProtocol:
    """Test MCP protocol handling."""
    
    @pytest.fixture
    def server_process(self):
        """Start the enhanced MCP server as a subprocess."""
        # Start server
        proc = subprocess.Popen(
            [sys.executable, "enhanced_mcp.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Give it time to start
        time.sleep(0.5)
        
        yield proc
        
        # Clean up
        proc.terminate()
        proc.wait(timeout=2)
    
    def send_request(self, proc, request):
        """Send a request to the server and get response."""
        request_str = json.dumps(request) + "\n"
        proc.stdin.write(request_str)
        proc.stdin.flush()
        
        # Read response (with timeout)
        import select
        if select.select([proc.stdout], [], [], 2)[0]:
            response_line = proc.stdout.readline()
            if response_line:
                return json.loads(response_line)
        return None
    
    def test_initialize(self, server_process):
        """Test initialization handshake."""
        # Send initialize
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }
        
        response = self.send_request(server_process, request)
        
        assert response is not None
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "grok-enhanced"
    
    def test_initialized_notification(self, server_process):
        """Test initialized notification."""
        # First initialize
        self.send_request(server_process, {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
        
        # Send initialized notification (no ID, no response expected)
        request = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
        
        server_process.stdin.write(json.dumps(request) + "\n")
        server_process.stdin.flush()
        
        # Should not get a response for notification
        import select
        ready = select.select([server_process.stdout], [], [], 0.5)[0]
        assert len(ready) == 0  # No response expected
    
    def test_tools_list(self, server_process):
        """Test listing tools."""
        # Initialize first
        self.send_request(server_process, {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
        
        # List tools
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        response = self.send_request(server_process, request)
        
        assert response is not None
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        assert len(tools) > 0
        
        # Check for expected tools
        tool_names = [t["name"] for t in tools]
        assert "grok_ask" in tool_names
        assert "grok_discuss" in tool_names
        assert "grok_list_sessions" in tool_names
        assert "grok_health" in tool_names
    
    def test_resources_list(self, server_process):
        """Test listing resources."""
        # Initialize first
        self.send_request(server_process, {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
        
        # List resources
        request = {
            "jsonrpc": "2.0",
            "method": "resources/list",
            "id": 2
        }
        
        response = self.send_request(server_process, request)
        
        assert response is not None
        assert "result" in response
        assert "resources" in response["result"]
        
        resources = response["result"]["resources"]
        assert len(resources) > 0
        
        # Check for expected resources
        resource_uris = [r["uri"] for r in resources]
        assert "grok://sessions" in resource_uris
        assert "grok://config" in resource_uris
        assert "grok://stats" in resource_uris
    
    def test_unknown_method(self, server_process):
        """Test handling of unknown method."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "id": 1
        }
        
        response = self.send_request(server_process, request)
        
        assert response is not None
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "not found" in response["error"]["message"].lower()


class TestToolExecution:
    """Test tool execution with mocked Grok client."""
    
    @pytest.mark.asyncio
    async def test_grok_ask_execution(self):
        """Test grok_ask tool execution."""
        from enhanced_mcp import EnhancedMCPServer
        
        # Mock the Grok client
        with patch('enhanced_mcp.GrokClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.ask = AsyncMock(return_value=AsyncMock(content="Mocked response"))
            
            server = EnhancedMCPServer()
            
            # Call grok_ask
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grok_ask",
                    "arguments": {
                        "question": "What is 2+2?"
                    }
                },
                "id": 1
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            assert "result" in response
            assert "content" in response["result"]
            assert len(response["result"]["content"]) > 0
            assert response["result"]["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    async def test_health_check_execution(self):
        """Test health check tool."""
        from enhanced_mcp import EnhancedMCPServer
        
        with patch('enhanced_mcp.GrokClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.ask = AsyncMock(return_value=AsyncMock(content="pong"))
            mock_instance.get_total_tokens_used = lambda: 100
            
            server = EnhancedMCPServer()
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grok_health",
                    "arguments": {}
                },
                "id": 1
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            assert "result" in response
            assert "content" in response["result"]
            
            health_text = response["result"]["content"][0]["text"]
            assert "Health Status:" in health_text
            assert "Server: healthy" in health_text


class TestResourceHandling:
    """Test resource reading."""
    
    @pytest.mark.asyncio
    async def test_read_config_resource(self):
        """Test reading config resource."""
        from enhanced_mcp import EnhancedMCPServer
        
        with patch('enhanced_mcp.GrokClient'):
            server = EnhancedMCPServer()
            
            request = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {
                    "uri": "grok://config"
                },
                "id": 1
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            assert "result" in response
            assert "contents" in response["result"]
            
            content = response["result"]["contents"][0]
            assert content["uri"] == "grok://config"
            assert content["mimeType"] == "application/json"
            
            # Parse the JSON content
            config = json.loads(content["text"])
            assert "model" in config
            assert "temperature" in config
    
    @pytest.mark.asyncio
    async def test_read_stats_resource(self):
        """Test reading stats resource."""
        from enhanced_mcp import EnhancedMCPServer
        
        with patch('enhanced_mcp.GrokClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_total_tokens_used = lambda: 42
            
            server = EnhancedMCPServer()
            
            # Make a few requests to update stats
            await server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            })
            
            request = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {
                    "uri": "grok://stats"
                },
                "id": 2
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            stats = json.loads(response["result"]["contents"][0]["text"])
            assert stats["requests"] >= 1
            assert stats["tokens_used"] == 42
            assert "uptime_seconds" in stats


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_error(self):
        """Test handling of tool execution errors."""
        from enhanced_mcp import EnhancedMCPServer
        
        with patch('enhanced_mcp.GrokClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.ask = AsyncMock(side_effect=Exception("API Error"))
            
            server = EnhancedMCPServer()
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grok_ask",
                    "arguments": {
                        "question": "Test"
                    }
                },
                "id": 1
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            # The tool returns an error message in the result, not an error response
            assert "result" in response
            assert "content" in response["result"]
            error_text = response["result"]["content"][0]["text"]
            assert "Error:" in error_text
            assert "API Error" in error_text
    
    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test calling non-existent tool."""
        from enhanced_mcp import EnhancedMCPServer
        
        with patch('enhanced_mcp.GrokClient'):
            server = EnhancedMCPServer()
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "nonexistent_tool",
                    "arguments": {}
                },
                "id": 1
            }
            
            response = await server.handle_request(request)
            
            assert response is not None
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "Unknown tool" in response["error"]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])