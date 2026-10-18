"""
Tests for agent personas: presets, Markdown agent files and inline definitions.
"""

import logging

import pytest

from lib.agents import (PRESETS, AgentError, available_agents, describe_available,
                        resolve_agent, resolve_agents)


@pytest.fixture
def agents_dir(tmp_path, monkeypatch):
    directory = tmp_path / "my-agents"
    directory.mkdir()
    monkeypatch.setenv("GROK_AGENTS_DIR", str(directory))
    return directory


def write_agent(directory, filename, frontmatter, body):
    (directory / filename).write_text(f"---\n{frontmatter}\n---\n{body}\n")


def test_presets_resolve_by_name():
    agent = resolve_agent("security")
    assert agent.source == "preset"
    assert "security engineer" in agent.instructions


def test_repo_ships_example_custom_agents():
    agents = available_agents()
    assert agents["economist"].source.endswith("agents/economist.md")
    assert "Look at incentives" in agents["economist"].instructions


def test_markdown_agent_file(agents_dir):
    write_agent(agents_dir, "quant.md",
                "name: quant\ndescription: Quant researcher\nmodel: grok-4.6",
                "You are a quant researcher.")
    agent = resolve_agent("quant")
    assert agent.instructions == "You are a quant researcher."
    assert agent.description == "Quant researcher"
    assert agent.model == "grok-4.6"
    assert agent.source == str(agents_dir / "quant.md")


def test_file_name_is_default_agent_name(agents_dir):
    write_agent(agents_dir, "ops.md", "description: On-call engineer", "You run production.")
    assert resolve_agent("ops").instructions == "You run production."


def test_custom_file_overrides_preset(agents_dir):
    write_agent(agents_dir, "skeptic.md", "name: skeptic", "You doubt everything twice.")
    assert resolve_agent("skeptic").instructions == "You doubt everything twice."


def test_broken_files_are_skipped(agents_dir, caplog):
    caplog.set_level(logging.WARNING)
    (agents_dir / "no-frontmatter.md").write_text("just text")
    write_agent(agents_dir, "bad-yaml.md", "name: [unclosed", "x")
    write_agent(agents_dir, "empty.md", "name: empty", "")
    agents = available_agents()
    assert "no-frontmatter" not in agents and "empty" not in agents
    assert set(PRESETS) <= set(agents)
    assert "Skipping agent file" in caplog.text and "no-frontmatter.md" in caplog.text


def test_inline_agent():
    agent = resolve_agent({"name": "historian", "instructions": "You are a historian."})
    assert agent.source == "inline"
    assert agent.instructions == "You are a historian."


def test_inline_accepts_system_prompt_alias():
    assert resolve_agent({"name": "x", "system_prompt": "Be brief."}).instructions == "Be brief."


def test_inline_model_override_of_known_agent():
    agent = resolve_agent({"name": "architect", "model": "grok-4.6"})
    assert agent.model == "grok-4.6"
    assert agent.instructions == PRESETS["architect"].instructions


@pytest.mark.parametrize("spec, message", [
    ("nobody", "Unknown agent 'nobody'. Available:"),
    ({"instructions": "x"}, "needs a 'name'"),
    ({"name": "ghost"}, "needs 'instructions'"),
    ({"name": "x" * 41, "instructions": "y"}, "Invalid agent name"),
    ({"name": "x", "instructions": "y" * 8001}, "exceed 8000 characters"),
    (42, "name or an object"),
    ({"name": "moderator", "instructions": "x"}, "is reserved"),
    ({"name": "User", "instructions": "x"}, "is reserved"),
    ({"name": "x", "instructions": "y", "model": 4.6}, "model must be a string"),
    ({"name": "architect", "model": 4.6}, "model must be a string"),
])
def test_invalid_specs(spec, message):
    with pytest.raises(AgentError, match=message.replace("(", r"\(").replace(".", r"\.")):
        resolve_agent(spec)


def test_resolve_agents_limits_and_duplicates():
    with pytest.raises(AgentError, match="between 2 and 6"):
        resolve_agents(["architect"], min_count=2)
    with pytest.raises(AgentError, match="between 2 and 6"):
        resolve_agents(["architect"] * 7, min_count=2)
    with pytest.raises(AgentError, match="Duplicate agent names: architect"):
        resolve_agents(["architect", {"name": "architect", "instructions": "x"}], min_count=2)


def test_tool_description_listing_is_capped(agents_dir):
    for i in range(5):
        write_agent(agents_dir, f"a{i}.md", f"name: a{i}\ndescription: {'d' * 300}", "x")
    listing = describe_available(max_custom=3)
    assert "...and 4 more custom agents" in listing  # 5 here + 2 shipped examples - 3 shown
    assert all(len(line) < 140 for line in listing.splitlines())
