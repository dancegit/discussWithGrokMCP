"""
Agent personas for panels and persona-driven discussions.

An agent is a name plus system instructions. Agents come from three places, resolved in
this order (later sources override earlier ones with the same name):

1. Built-in presets (``PRESETS`` below).
2. Markdown files in the agents directories: ``agents/`` in this repository plus any
   directories listed in ``GROK_AGENTS_DIR`` (os.pathsep-separated). Each file has YAML
   frontmatter with ``name`` and ``description`` (and optionally ``model``); the body is
   the system prompt. This is the same shape as Claude Code agent files.
3. Inline definitions passed in a tool call: ``{"name": ..., "instructions": ...}``.
"""

import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

REPO_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
MAX_INSTRUCTIONS_CHARS = 8000
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,39}$")
RESERVED_NAMES = {"moderator", "user", "brief"}  # speaker labels used in panel transcripts


@dataclass(frozen=True)
class Agent:
    name: str
    instructions: str
    description: str = ""
    model: Optional[str] = None
    source: str = "inline"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        return cls(**{k: data[k] for k in ("name", "instructions", "description", "model", "source")
                      if k in data})


def _preset(name: str, description: str, instructions: str) -> Agent:
    return Agent(name=name, description=description, instructions=instructions, source="preset")


PRESETS: Dict[str, Agent] = {a.name: a for a in [
    _preset("architect", "Systems architect: structure, boundaries, long-term fit",
            "You are a pragmatic systems architect. Judge proposals by how they hold up over "
            "time: boundaries between components, data ownership, failure modes, and what "
            "becomes expensive to change later. Prefer simple designs that leave room to grow."),
    _preset("security", "Security engineer: threats, abuse, data exposure",
            "You are a security engineer. Look for how things can be abused or fail unsafely: "
            "untrusted input, secrets, permissions, supply chain, data exposure. Rank risks by "
            "likelihood and impact, and propose the cheapest control that meaningfully reduces each."),
    _preset("skeptic", "Devil's advocate: challenges assumptions",
            "You are the panel's skeptic. Find the weakest assumption in each argument and "
            "test it. Ask what evidence would change the conclusion. Do not be contrarian for "
            "its own sake: concede points that survive scrutiny."),
    _preset("pragmatist", "Delivery-focused engineer: smallest thing that works",
            "You are a delivery-focused senior engineer. Push toward the smallest solution that "
            "solves the real problem this week, name what can be deferred, and call out "
            "gold-plating. Cost, time and maintenance burden matter to you."),
    _preset("qa", "QA engineer: testability, edge cases, verification",
            "You are a QA engineer. For every proposal ask how we would know it works: what to "
            "test, which edge cases and failure paths matter, what to monitor in production, "
            "and what a regression would look like."),
    _preset("performance", "Performance engineer: latency, throughput, cost at scale",
            "You are a performance engineer. Reason with rough numbers: data sizes, request "
            "rates, latency budgets, memory and cost. Say where the bottleneck will be and "
            "when it would actually matter, and avoid optimising what will not."),
    _preset("product", "Product thinker: user value and trade-offs",
            "You are a product-minded engineer. Keep the discussion anchored on who the user "
            "is, what problem they have, and which trade-off they would choose. Point out "
            "where the team is solving a problem nobody has."),
    _preset("researcher", "Researcher: evidence, prior art, unknowns",
            "You are a careful researcher. Separate what is known from what is assumed, cite "
            "the kind of evidence or prior art that would settle a question, and flag where "
            "the panel is guessing. State your confidence."),
]}

MODERATOR = Agent(
    name="moderator",
    source="preset",
    description="Neutral moderator that synthesises the panel",
    instructions=(
        "You are a neutral moderator. You did not take part in the debate. Summarise it "
        "faithfully and attribute positions to panelists by name. Do not add new arguments."
    ),
)

DEFAULT_PANEL = ["architect", "skeptic", "pragmatist"]


class AgentError(ValueError):
    """Invalid or unknown agent specification."""


def agent_dirs() -> List[Path]:
    dirs = [REPO_AGENTS_DIR]
    for entry in os.getenv("GROK_AGENTS_DIR", "").split(os.pathsep):
        if entry.strip():
            dirs.append(Path(entry.strip()).expanduser())
    return dirs


def _parse_agent_file(path: Path) -> Agent:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not match:
        raise AgentError(f"{path}: missing YAML frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise AgentError(f"{path}: frontmatter must be a mapping")
    return _validated(Agent(
        name=str(meta.get("name") or path.stem),
        description=str(meta.get("description") or ""),
        model=meta.get("model"),
        instructions=match.group(2).strip(),
        source=str(path),
    ))


def load_custom_agents() -> Dict[str, Agent]:
    """Agents defined as Markdown files. Unreadable files are skipped, not fatal."""
    agents: Dict[str, Agent] = {}
    for directory in agent_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            try:
                agent = _parse_agent_file(path)
            except (AgentError, OSError, yaml.YAMLError) as e:
                logger.warning(f"Skipping agent file {path}: {e}")
                continue
            agents[agent.name] = agent
    return agents


def available_agents() -> Dict[str, Agent]:
    return {**PRESETS, **load_custom_agents()}


def _validated(agent: Agent) -> Agent:
    if agent.name.lower() in RESERVED_NAMES and agent.source != "preset":
        raise AgentError(f"Agent name {agent.name!r} is reserved")
    if agent.model is not None and not isinstance(agent.model, str):
        raise AgentError(f"Agent {agent.name!r}: model must be a string")
    if not NAME_PATTERN.match(agent.name):
        raise AgentError(f"Invalid agent name {agent.name!r}: use 1-40 letters, digits, space, _ . -")
    if not agent.instructions.strip():
        raise AgentError(f"Agent {agent.name!r} has no instructions")
    if len(agent.instructions) > MAX_INSTRUCTIONS_CHARS:
        raise AgentError(f"Agent {agent.name!r} instructions exceed {MAX_INSTRUCTIONS_CHARS} characters")
    return agent


AgentSpec = Union[str, Dict[str, Any]]


def resolve_agent(spec: AgentSpec, known: Optional[Dict[str, Agent]] = None) -> Agent:
    """Turn a name or an inline definition into an Agent."""
    known = known if known is not None else available_agents()
    if isinstance(spec, str):
        if spec not in known:
            raise AgentError(f"Unknown agent {spec!r}. Available: {', '.join(sorted(known))}")
        return known[spec]
    if isinstance(spec, dict):
        name = spec.get("name")
        instructions = spec.get("instructions") or spec.get("system_prompt")
        if not name:
            raise AgentError("Inline agent needs a 'name'")
        if not instructions:
            # {"name": "security", "model": "..."} customises a known agent
            if name not in known:
                raise AgentError(f"Inline agent {name!r} needs 'instructions'")
            base = known[name]
            return _validated(Agent(name=base.name, instructions=base.instructions,
                                    description=base.description,
                                    model=spec.get("model") or base.model, source=base.source))
        return _validated(Agent(name=str(name), instructions=str(instructions),
                                description=str(spec.get("description") or ""),
                                model=spec.get("model"), source="inline"))
    raise AgentError(f"Agent must be a name or an object, got {type(spec).__name__}")


def resolve_agents(specs: List[AgentSpec], min_count: int = 1, max_count: int = 6) -> List[Agent]:
    if not isinstance(specs, list) or not (min_count <= len(specs) <= max_count):
        raise AgentError(f"Provide between {min_count} and {max_count} agents")
    known = available_agents()
    agents = [resolve_agent(spec, known) for spec in specs]
    names = [a.name for a in agents]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise AgentError(f"Duplicate agent names: {', '.join(duplicates)}")
    return agents


def describe_available(max_custom: Optional[int] = None) -> str:
    """One line per agent for tool descriptions; descriptions and custom count are capped."""
    agents = sorted(available_agents().values(), key=lambda a: (a.source != "preset", a.name))
    presets = [a for a in agents if a.source == "preset"]
    custom = [a for a in agents if a.source != "preset"]
    hidden = 0
    if max_custom is not None and len(custom) > max_custom:
        hidden, custom = len(custom) - max_custom, custom[:max_custom]
    lines = []
    for agent in presets + custom:
        origin = "preset" if agent.source == "preset" else "custom"
        description = agent.description if len(agent.description) <= 100 else agent.description[:97] + "..."
        lines.append(f"- {agent.name} ({origin}): {description}")
    if hidden:
        lines.append(f"- ...and {hidden} more custom agents")
    return "\n".join(lines)
