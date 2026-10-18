"""
Tests for grok_panel and for personas in grok_discuss / grok_continue_session.
"""

import asyncio
import re
import time

import pytest

from conftest import FakeGrokClient
from lib.grok_client import GrokResponse
from lib.tools import ContinueSessionTool, DiscussTool, ListSessionsTool, PanelTool, SessionManager


class PanelFake(FakeGrokClient):
    """Answers in character: '<agent> says #<n>', based on the system prompt it receives."""

    def __init__(self, fail_for=(), delay=0.0, **kwargs):
        super().__init__(**kwargs)
        self.fail_for = set(fail_for)
        self.delay = delay
        self.counts = {}

    async def ask_with_history(self, messages, stream=False, **kwargs):
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        match = re.search(r"You are '([^']+)' on a discussion panel", system)
        speaker = match.group(1) if match else "moderator"
        self.calls.append({"speaker": speaker, "messages": messages})
        if self.delay:
            await asyncio.sleep(self.delay)
        if speaker in self.fail_for:
            raise RuntimeError(f"{speaker} timed out")
        self.counts[speaker] = self.counts.get(speaker, 0) + 1
        text = f"{speaker} says #{self.counts[speaker]}"
        return GrokResponse(content=text, tokens_used=1, model=self.model, timestamp=time.time())

    def prompts_for(self, speaker):
        return [c["messages"][-1]["content"] for c in self.calls if c["speaker"] == speaker]


@pytest.fixture
def manager(tmp_path):
    return SessionManager(tmp_path / "sessions")


@pytest.fixture
def client():
    return PanelFake()


@pytest.fixture
def panel(client, manager):
    return PanelTool(client, manager)


def session_id_of(result):
    return re.search(r"Session ID: (\S+)", result).group(1)


class TestPanel:
    @pytest.mark.asyncio
    async def test_default_panel_two_rounds_and_synthesis(self, panel, client):
        result = await panel.execute(topic="Monorepo or polyrepo?")
        assert "Panel: architect, skeptic, pragmatist" in result
        for name in ("architect", "skeptic", "pragmatist"):
            assert f"**{name}:** {name} says #1" in result
            assert f"**{name}:** {name} says #2" in result
        assert "### Synthesis\nmoderator says #1" in result
        assert len(client.calls) == 3 * 2 + 1

    @pytest.mark.asyncio
    async def test_each_agent_gets_its_own_system_prompt(self, panel, client):
        await panel.execute(topic="T", agents=["security", "qa"], rounds=1, synthesize=False)
        systems = {c["speaker"]: c["messages"][0]["content"] for c in client.calls}
        assert "security engineer" in systems["security"]
        assert "QA engineer" in systems["qa"]
        assert "panel with: qa" in systems["security"]
        assert "Stay under 150 words" in systems["qa"]

    @pytest.mark.asyncio
    async def test_opening_round_is_independent_later_rounds_see_transcript(self, panel, client):
        await panel.execute(topic="T", agents=["architect", "skeptic"], rounds=2, synthesize=False)
        opening, rebuttal = client.prompts_for("skeptic")
        assert "architect says" not in opening
        assert opening.endswith("Round 1: give your opening position on the topic.")
        assert "Discussion so far" not in opening
        assert "[architect]\narchitect says #1" in rebuttal
        assert "[skeptic]\nskeptic says #1" in rebuttal

    @pytest.mark.asyncio
    async def test_agents_in_a_round_run_concurrently(self, manager):
        client = PanelFake(delay=0.3)
        started = time.monotonic()
        await PanelTool(client, manager).execute(
            topic="T", agents=["architect", "skeptic", "qa", "security"], rounds=1, synthesize=False)
        assert time.monotonic() - started < 0.9  # 4 x 0.3s sequentially would be 1.2s

    @pytest.mark.asyncio
    async def test_inline_and_custom_agents(self, panel, client):
        result = await panel.execute(topic="Four-day week?", rounds=1, synthesize=False, agents=[
            "economist",
            {"name": "team-lead", "instructions": "You lead a team of eight engineers."},
        ])
        assert "**team-lead:** team-lead says #1" in result
        systems = {c["speaker"]: c["messages"][0]["content"] for c in client.calls}
        assert systems["team-lead"].startswith("You lead a team of eight engineers.")
        assert "You are an economist" in systems["economist"]

    @pytest.mark.asyncio
    async def test_one_failing_agent_does_not_sink_the_panel(self, manager):
        client = PanelFake(fail_for={"skeptic"})
        result = await PanelTool(client, manager).execute(topic="T", agents=["architect", "skeptic"])
        assert "**skeptic:** _(no response: skeptic timed out)_" in result
        assert "### Synthesis" in result

    @pytest.mark.asyncio
    async def test_all_agents_failing_is_an_error_and_leaves_no_session(self, manager):
        client = PanelFake(fail_for={"architect", "skeptic"})
        result = await PanelTool(client, manager).execute(topic="T", agents=["architect", "skeptic"])
        assert result.startswith("Error: every panelist failed in round 1")
        assert manager.list_sessions() == []
        assert list(manager.storage_path.glob("*.json")) == []

    @pytest.mark.asyncio
    async def test_synthesis_failure_keeps_the_rounds(self, manager):
        client = PanelFake(fail_for={"moderator"})
        result = await PanelTool(client, manager).execute(topic="T", agents=["architect", "skeptic"])
        assert "Session ID:" in result
        assert "**architect:** architect says #2" in result
        assert "_Synthesis failed: moderator timed out." in result
        assert manager.get_session(session_id_of(result))["panel"]["rounds_run"] == 2

    @pytest.mark.asyncio
    async def test_failed_round_on_resume_returns_partial_output(self, panel, client, manager):
        session_id = session_id_of(await panel.execute(
            topic="T", agents=["architect", "skeptic"], rounds=1, synthesize=False))
        client.fail_for = {"architect", "skeptic"}
        result = await panel.execute(session_id=session_id, message="Again?", rounds=2)
        assert "**You:** Again?" in result
        assert "_Round 2 failed: every panelist failed in round 2" in result
        assert "### Synthesis" not in result
        assert manager.get_session(session_id)["panel"]["rounds_run"] == 1

    @pytest.mark.asyncio
    async def test_transcript_is_bounded_by_last_synthesis(self, panel, client):
        session_id = session_id_of(await panel.execute(topic="T", agents=["architect", "skeptic"]))
        client.calls.clear()
        await panel.execute(session_id=session_id, message="Next?")
        prompt = client.prompts_for("architect")[0]
        assert "architect says #1" not in prompt  # round 1 now lives in the synthesis
        assert "[Moderator synthesis]\nmoderator says #1" in prompt
        assert "summarised in the synthesis below" in prompt

    @pytest.mark.asyncio
    async def test_per_model_clients_are_reused(self, panel, client, monkeypatch):
        import lib.grok_client
        built = []
        real = lib.grok_client.create_client
        monkeypatch.setattr(lib.grok_client, "create_client",
                            lambda **kw: built.append(kw["model"]) or real(**kw))
        await panel.execute(topic="T", rounds=3, synthesize=False, agents=[
            "architect", {"name": "skeptic", "model": "grok-4.6"}])
        assert built == ["grok-4.6"]

    @pytest.mark.asyncio
    async def test_context_files_reach_every_agent(self, panel, client, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("Latency budget: 50ms")
        await panel.execute(topic="T", agents=["architect", "performance"], rounds=1,
                            synthesize=False, context_files=[str(spec)], context="Small team")
        for speaker in ("architect", "performance"):
            prompt = client.prompts_for(speaker)[0]
            assert "Latency budget: 50ms" in prompt and "Background: Small team" in prompt

    @pytest.mark.asyncio
    async def test_resume_with_user_message(self, panel, client, manager, tmp_path):
        session_id = session_id_of(await panel.execute(topic="T", agents=["architect", "skeptic"]))
        client.calls.clear()

        # A fresh tool and manager prove it is resumed from disk
        resumed = PanelTool(client, SessionManager(tmp_path / "sessions"))
        result = await resumed.execute(session_id=session_id, message="What about cost?")

        assert "**You:** What about cost?" in result
        assert "### Round 3" in result and "### Round 2" not in result
        prompt = client.prompts_for("architect")[0]
        assert "[The user]\nWhat about cost?" in prompt
        assert "[Moderator synthesis]\nmoderator says #1" in prompt
        session = SessionManager(tmp_path / "sessions").get_session(session_id)
        assert session["panel"]["rounds_run"] == 3

    @pytest.mark.asyncio
    async def test_errors(self, panel):
        assert (await panel.execute()).startswith("Error: 'topic' is required")
        assert (await panel.execute(topic="T", agents=["architect"])).startswith(
            "Error: Provide between 2 and 6 agents")
        assert "Unknown agent 'nobody'" in await panel.execute(topic="T", agents=["architect", "nobody"])
        assert (await panel.execute(session_id="missing")).startswith("Error: no panel session")

    @pytest.mark.asyncio
    async def test_rounds_are_capped(self, panel, client):
        await panel.execute(topic="T", agents=["architect", "skeptic"], rounds=99, synthesize=False)
        assert len(client.calls) == 2 * 4

    @pytest.mark.asyncio
    async def test_per_agent_model_uses_its_own_client(self, panel, client):
        await panel.execute(topic="T", rounds=1, synthesize=False, agents=[
            "architect", {"name": "skeptic", "model": "grok-4.6"}])
        # The default client only served the architect; the patched factory built the other
        assert [c["speaker"] for c in client.calls] == ["architect"]

    @pytest.mark.asyncio
    async def test_listed_and_guarded_from_continue_session(self, panel, client, manager):
        session_id = session_id_of(await panel.execute(topic="T", agents=["qa", "security"], rounds=1))
        listing = await ListSessionsTool(client, manager).execute()
        assert "Panel: qa, security (1 rounds)" in listing
        result = await ContinueSessionTool(client, manager).execute(session_id=session_id, message="hi")
        assert "is a panel discussion; resume it with grok_panel" in result


class TestDiscussPersona:
    @pytest.mark.asyncio
    async def test_discuss_refuses_panel_sessions(self, fake_client, manager):
        panel_result = await PanelTool(PanelFake(), manager).execute(
            topic="T", agents=["qa", "security"], rounds=1, synthesize=False)
        session_id = session_id_of(panel_result)
        before = manager.get_session(session_id)["messages"][:]
        result = await DiscussTool(fake_client, manager).execute(session_id=session_id)
        assert "is a panel discussion; resume it with grok_panel" in result
        assert manager.get_session(session_id)["messages"] == before
        assert "pagination" not in manager.get_session(session_id) or \
            manager.get_session(session_id)["pagination"] == {}

    @pytest.mark.asyncio
    async def test_persona_model_is_used(self, fake_client, manager, monkeypatch):
        import lib.grok_client
        built = []
        real = lib.grok_client.create_client
        monkeypatch.setattr(lib.grok_client, "create_client",
                            lambda **kw: built.append(kw["model"]) or real(**kw))
        result = await DiscussTool(fake_client, manager).execute(
            topic="T", agent={"name": "architect", "model": "grok-4.6"}, max_turns=1)
        assert "Model: grok-4.6" in result
        assert built == ["grok-4.6"]

    @pytest.mark.asyncio
    async def test_discuss_with_agent_sends_system_prompt(self, fake_client, manager):
        tool = DiscussTool(fake_client, manager)
        result = await tool.execute(topic="Threat model this", agent="security", max_turns=1)
        assert "Agent: security" in result
        system = fake_client.calls[0]["messages"][0]
        assert system["role"] == "system" and "security engineer" in system["content"]

    @pytest.mark.asyncio
    async def test_agent_and_system_prompt_combine(self, fake_client, manager):
        tool = DiscussTool(fake_client, manager)
        await tool.execute(topic="T", agent="skeptic", system_prompt="Answer in French.", max_turns=1)
        content = fake_client.calls[0]["messages"][0]["content"]
        assert content.startswith("You are the panel's skeptic") and content.endswith("Answer in French.")

    @pytest.mark.asyncio
    async def test_custom_system_prompt_only(self, fake_client, manager):
        result = await DiscussTool(fake_client, manager).execute(
            topic="T", system_prompt="You are a pirate.", max_turns=1)
        assert "Agent: custom" in result
        assert fake_client.calls[0]["messages"][0]["content"] == "You are a pirate."

    @pytest.mark.asyncio
    async def test_unknown_agent_creates_no_session(self, fake_client, manager):
        result = await DiscussTool(fake_client, manager).execute(topic="T", agent="nobody")
        assert result.startswith("Error: Unknown agent 'nobody'")
        assert manager.list_sessions() == []

    @pytest.mark.asyncio
    async def test_persona_survives_continue_session(self, fake_client, manager, tmp_path):
        result = await DiscussTool(fake_client, manager).execute(topic="T", agent="qa", max_turns=1)
        session_id = session_id_of(result)
        fake_client.calls.clear()

        reloaded = SessionManager(tmp_path / "sessions")
        await ContinueSessionTool(fake_client, reloaded).execute(session_id=session_id, message="More?")
        first = fake_client.calls[0]["messages"][0]
        assert first["role"] == "system" and "QA engineer" in first["content"]

    @pytest.mark.asyncio
    async def test_no_persona_means_no_system_message(self, fake_client, manager):
        await DiscussTool(fake_client, manager).execute(topic="T", max_turns=1)
        assert fake_client.calls[0]["messages"][0]["role"] == "user"
