# Custom agents

Each `*.md` file here (and in any directory listed in `GROK_AGENTS_DIR`) defines an agent
that `grok_panel` and `grok_discuss` can use by name. It uses the same shape as a Claude
Code agent file:

```markdown
---
name: economist
description: One line shown in the tool description
model: grok-4.6        # optional; overrides the default model for this agent
---
The system prompt: who this agent is and how it should argue.
```

A file with the same `name` as a preset replaces that preset. Invalid files are skipped.
