"""
Shared pytest fixtures.

Every test runs against a fake xAI client unless it is marked ``live``.
Live tests talk to the real API and are skipped when XAI_API_KEY is not set.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")  # lets `pytest -m live` pick up the key from .env

from lib.grok_client import GrokResponse  # noqa: E402

DEFAULT_MODEL = "grok-code-fast"
DUMMY_KEY = "test-key-not-real"


class FakeGrokClient:
    """In-memory stand-in for GrokClient that records calls and never hits the network."""

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.7,
                 reply: str = "Fake response", **_: Any):
        self.model = model
        self.temperature = temperature
        self.reply = reply
        self.calls: List[Dict[str, Any]] = []
        self.total_tokens = 0

    def _respond(self, **call: Any) -> GrokResponse:
        self.calls.append(call)
        self.total_tokens += 10
        return GrokResponse(content=self.reply, tokens_used=10,
                            model=self.model, timestamp=time.time())

    async def ask(self, prompt: str, stream: bool = False, **kwargs: Any) -> GrokResponse:
        return self._respond(prompt=prompt, **kwargs)

    async def ask_with_history(self, messages: List[Dict[str, str]], stream: bool = False,
                               **kwargs: Any) -> GrokResponse:
        return self._respond(messages=messages, **kwargs)

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_total_tokens_used(self) -> int:
        return self.total_tokens

    def reset_token_counter(self) -> None:
        self.total_tokens = 0


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: calls the real xAI API (needs XAI_API_KEY)")


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    if os.getenv("XAI_API_KEY") and os.getenv("XAI_API_KEY") != DUMMY_KEY:
        return
    skip_live = pytest.mark.skip(reason="XAI_API_KEY not set; live API test skipped")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run each test in its own directory so sessions/logs never land in the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _no_real_api(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap the real client for FakeGrokClient in every non-live test."""
    if "live" in request.keywords:
        return
    monkeypatch.setenv("XAI_API_KEY", DUMMY_KEY)
    monkeypatch.setattr("lib.grok_client.GrokClient", FakeGrokClient)


@pytest.fixture
def fake_client() -> FakeGrokClient:
    return FakeGrokClient()
