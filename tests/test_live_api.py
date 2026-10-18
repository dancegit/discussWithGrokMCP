"""
Live tests against the real xAI API.

Skipped unless XAI_API_KEY is set. Run explicitly with:

    uv run pytest -m live
"""

import pytest

from lib.grok_client import GrokClient
from lib.tools import AskTool

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_client_round_trip():
    client = GrokClient()
    response = await client.ask("Reply with the single word: pong")
    assert "pong" in response.content.lower()
    assert response.tokens_used > 0


@pytest.mark.asyncio
async def test_ask_tool_round_trip():
    tool = AskTool(GrokClient())
    result = await tool.execute(question="What is 2 + 2? Answer with just the number.")
    assert not result.startswith("Error"), result
    assert "4" in result
