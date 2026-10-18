"""
Panel discussion tool: several agents with their own system instructions debate a topic.

Round 1 collects independent opening positions (run in parallel, so nobody anchors on
anyone else). Each later round shows every agent the full transcript and asks them to
respond to the others. A neutral moderator then writes the synthesis. Panels are stored
as sessions and can be resumed with a new message from the user and more rounds.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from ..agents import (DEFAULT_PANEL, MODERATOR, Agent, AgentError, describe_available,
                      resolve_agents)
from .base import BaseTool
from .context_loader import ContextLoader
from .session import SessionManager

logger = logging.getLogger(__name__)

MAX_ROUNDS = 4
# Shared material is re-sent to every agent in every round, so keep it modest
MAX_CONTEXT_LINES = 1500
SPEC_ITEM = {
    "oneOf": [
        {"type": "string", "description": "Preset or custom agent name"},
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "instructions": {"type": "string", "description": "System prompt for this agent"},
                "description": {"type": "string"},
                "model": {"type": "string", "description": "Optional per-agent model"},
            },
            "required": ["name"],
        },
    ]
}


class PanelTool(BaseTool):
    """Multi-agent panel discussion."""

    def __init__(self, grok_client, session_manager: SessionManager):
        super().__init__(grok_client)
        self.session_manager = session_manager
        self.concurrency = max(1, int(os.getenv("GROK_PANEL_CONCURRENCY", "4")))
        self._clients: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "grok_panel"

    @property
    def description(self) -> str:
        return (
            "Run a panel of Grok agents with different roles (system instructions) that debate "
            "a topic over several rounds, then get a moderator's synthesis. Agents can be "
            "presets, custom agents from agents/*.md, or inline {name, instructions}. "
            "Resume a panel with session_id and an optional message. "
            "Available agents:\n" + describe_available(max_custom=30)
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Question or decision to debate"},
                "agents": {
                    "type": "array", "items": SPEC_ITEM, "minItems": 2, "maxItems": 6,
                    "description": f"Panelists (default: {', '.join(DEFAULT_PANEL)})",
                },
                "rounds": {"type": "integer", "minimum": 1, "maximum": MAX_ROUNDS,
                           "description": "Debate rounds (default 2 for a new panel, 1 when resuming)"},
                "max_words": {"type": "integer", "minimum": 40, "maximum": 600,
                              "description": "Word budget per contribution (default 150)"},
                "synthesize": {"type": "boolean", "description": "Add a moderator synthesis (default true)"},
                "context": {"type": "string", "description": "Extra background for all agents"},
                "context_files": {
                    "type": "array",
                    "items": {"oneOf": [{"type": "string"}, {"type": "object"}]},
                    "description": "Files/dirs/globs shared with all agents (same format as grok_discuss)",
                },
                "context_type": {"type": "string", "enum": ["code", "docs", "config", "general"]},
                "session_id": {"type": "string", "description": "Resume an existing panel"},
                "message": {"type": "string", "description": "When resuming: your input to the panel"},
            },
        }

    # ------------------------------------------------------------------ prompts

    @staticmethod
    def _system_prompt(agent: Agent, panel: List[Agent], max_words: int) -> str:
        others = ", ".join(a.name for a in panel if a.name != agent.name)
        return (
            f"{agent.instructions}\n\n"
            f"You are '{agent.name}' on a discussion panel with: {others}. Speak only as "
            f"yourself and only from your role's perspective. Address other panelists by name "
            f"when you agree or disagree. Change your position when an argument convinces you, "
            f"and say so. Be concrete. Stay under {max_words} words. No preamble, and do not "
            f"write anyone else's lines."
        )

    @staticmethod
    def _transcript(messages: List[Dict[str, Any]]) -> str:
        """Render the debate. Once a synthesis exists, earlier rounds are represented by it
        alone, so prompts stay bounded however often a panel is resumed."""
        body = messages[1:]  # messages[0] is the brief
        last_synthesis = max((i for i, m in enumerate(body) if m.get("name") == "moderator"),
                             default=None)
        parts = []
        if last_synthesis is not None:
            body = body[last_synthesis:]
            parts.append("(Earlier rounds are summarised in the synthesis below.)")
        for m in body:
            speaker = m.get("name") or m["role"]
            if speaker == "moderator":
                parts.append(f"[Moderator synthesis]\n{m['content']}")
            elif m["role"] == "user":
                parts.append(f"[The user]\n{m['content']}")
            else:
                parts.append(f"[{speaker}]\n{m['content']}")
        return "\n\n".join(parts)

    def _turn_prompt(self, brief: str, messages: List[Dict[str, Any]], agent: Agent,
                     round_no: int, opening: bool) -> str:
        if opening:
            return f"{brief}\n\nRound {round_no}: give your opening position on the topic."
        return (
            f"{brief}\n\nDiscussion so far:\n\n{self._transcript(messages)}\n\n"
            f"Round {round_no}: respond as {agent.name}. Engage with the strongest points "
            f"from the others, especially where you disagree, and answer anything the user "
            f"asked. Do not repeat yourself."
        )

    # ---------------------------------------------------------------- execution

    def _client_for(self, agent: Agent):
        """One client per model for the whole tool, not one per call."""
        if not agent.model or agent.model == self.grok_client.model:
            return self.grok_client
        if agent.model not in self._clients:
            from lib.grok_client import create_client
            self._clients[agent.model] = create_client(
                model=agent.model, temperature=self.grok_client.temperature)
        return self._clients[agent.model]

    async def _speak(self, agent: Agent, system: str, prompt: str, semaphore) -> str:
        async with semaphore:
            response = await self._client_for(agent).ask_with_history(
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                stream=False,
            )
        return response.content.strip()

    async def _run_round(self, session_id: str, panel: List[Agent], brief: str,
                         round_no: int, opening: bool, max_words: int) -> List[str]:
        """Run one round; returns per-agent output lines. Failures don't abort the round."""
        messages = list(self.session_manager.get_session(session_id)["messages"])
        semaphore = asyncio.Semaphore(self.concurrency)
        results = await asyncio.gather(*[
            self._speak(agent, self._system_prompt(agent, panel, max_words),
                        self._turn_prompt(brief, messages, agent, round_no, opening), semaphore)
            for agent in panel
        ], return_exceptions=True)

        lines, spoke = [f"### Round {round_no}"], 0
        for agent, result in zip(panel, results):
            if isinstance(result, BaseException):
                logger.error(f"Panel agent {agent.name} failed: {result}")
                lines.append(f"**{agent.name}:** _(no response: {result})_")
                continue
            self.session_manager.add_message(session_id, "assistant", result, name=agent.name)
            lines.append(f"**{agent.name}:** {result}")
            spoke += 1
        if spoke == 0:
            raise RuntimeError(f"every panelist failed in round {round_no}: {results[0]}")
        return lines

    async def _synthesize(self, session_id: str, brief: str) -> str:
        messages = self.session_manager.get_session(session_id)["messages"]
        prompt = (
            f"{brief}\n\nFull panel transcript:\n\n{self._transcript(messages)}\n\n"
            "Write the synthesis with these headings: Consensus, Disagreements (who holds "
            "which view and why), Recommendation, Open questions. Be brief."
        )
        response = await self.grok_client.ask_with_history(
            messages=[{"role": "system", "content": MODERATOR.instructions},
                      {"role": "user", "content": prompt}],
            stream=False,
        )
        content = response.content.strip()
        self.session_manager.add_message(session_id, "assistant", content, name="moderator")
        return content

    def _brief(self, topic: str, context: Optional[str], context_files, context_type: str) -> str:
        brief = f"Panel topic: {topic}"
        if context:
            brief += f"\n\nBackground: {context}"
        if context_files:
            content, meta = ContextLoader.load_context(
                context_files, max_lines_per_file=300, max_total_lines=MAX_CONTEXT_LINES,
                context_type=context_type,
            )
            if content:
                brief += f"\n\nShared material ({meta.get('files_processed', 0)} files):\n{content}"
        return brief

    async def execute(self, topic: str = None, agents: List[Any] = None, rounds: int = None,
                      max_words: int = 150, synthesize: bool = True, context: str = None,
                      context_files: List[Any] = None, context_type: str = "general",
                      session_id: str = None, message: str = None, **kwargs) -> str:
        try:
            max_words = max(40, min(int(max_words), 600))
            if session_id:
                session = self.session_manager.get_session(session_id)
                if not session or session.get("type") != "panel":
                    return f"Error: no panel session {session_id}"
                panel = [Agent.from_dict(a) for a in session["panel"]["agents"]]
                brief = session["messages"][0]["content"]
                topic = session["topic"]
                max_words = session["panel"].get("max_words", max_words)
                rounds = rounds or 1
                is_resume = True
                if message:
                    self.session_manager.add_message(session_id, "user", message, name="user")
                start = session["panel"]["rounds_run"] + 1
            else:
                if not topic:
                    return "Error: 'topic' is required to start a panel"
                panel = resolve_agents(agents or DEFAULT_PANEL, min_count=2, max_count=6)
                rounds = rounds or 2
                is_resume = False
                brief = self._brief(topic, context, context_files, context_type)
                session_id = self.session_manager.create_session(topic)
                self.session_manager.update_session(session_id, type="panel", panel={
                    "agents": [a.to_dict() for a in panel], "rounds_run": 0, "max_words": max_words,
                })
                self.session_manager.add_message(session_id, "user", brief, name="brief")
                start = 1

            rounds = max(1, min(int(rounds), MAX_ROUNDS))
            out = [
                f"## Panel: {topic}",
                f"Session ID: {session_id}",
                "Panel: " + ", ".join(a.name for a in panel),
            ]
            if message and is_resume:
                out.append(f"\n**You:** {message}")

            completed = 0
            for round_no in range(start, start + rounds):
                # Independent openings only when nothing has been said yet
                history = self.session_manager.get_session(session_id)["messages"]
                opening = len(history) <= 1
                try:
                    lines = await self._run_round(session_id, panel, brief, round_no, opening, max_words)
                except Exception as e:
                    if not is_resume and completed == 0:
                        # Nothing usable was produced: do not leave an empty session behind
                        self.session_manager.delete_session(session_id)
                        return f"Error: {e}"
                    out.append(f"\n_Round {round_no} failed: {e}_")
                    break
                out.append("")
                out.extend(lines)
                completed += 1
                session = self.session_manager.get_session(session_id)
                self.session_manager.update_session(
                    session_id, panel={**session["panel"], "rounds_run": round_no})

            if synthesize and completed:
                out.append("\n### Synthesis")
                try:
                    out.append(await self._synthesize(session_id, brief))
                except Exception as e:
                    logger.error(f"Panel synthesis failed: {e}")
                    out.append(f"_Synthesis failed: {e}. The rounds above are saved; resume to retry._")

            out.append(f"\nResume with grok_panel session_id='{session_id}' and a message.")
            return "\n".join(out)

        except AgentError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error in panel: {e}")
            return f"Error: {e}"
