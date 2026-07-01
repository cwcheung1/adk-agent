# Lessons

`NOTES.md` (one level up) is a dense running log — good for reference, bad for
learning something the first time. These are the friendlier version: one file
per concept, same shape every time —

- **Concept** — the one-sentence version.
- **Analogy** — something you already know that this maps onto.
- **How it works** — the real explanation, tied to this repo's actual code.
- **Look at** — which files to open, in order.
- **Run this** — exact commands, with what you should see.
- **You'll know it clicked when** — a question you should be able to answer
  yourself after.

Read in order — each one assumes the last:

1. [Foundations](./01-foundations.md) — agent, Runner, event loop, CLI, Docker
2. [MCP: stdio transport](./02-mcp-stdio.md) — how an agent calls a tool it spawns itself
3. [MCP: streamable HTTP](./03-mcp-http.md) — calling a tool server you *don't* spawn, and why it's not SSE
4. [A2A](./04-a2a.md) — how an agent calls *another agent*
5. [Workflow agents: Sequential](./05-workflow-agents.md) — deterministic composition, the anti-A2A
5b. [Workflow agents: Parallel and Loop](./05b-parallel-and-loop.md) — concurrent fan-out, and repeat-until-satisfied
5c. [Agent-as-tool](./05c-agent-as-tool.md) — an agent as a callable, not a hand-off (3rd way to combine agents)
6. [Observability](./06-observability.md) — seeing what actually happened

Progress against these is tracked in the
[learning-tracker](../../../learning-tracker) app, not in these files — treat
these as the textbook, that app as the gradebook.

(Aside: `adk web`/`adk run` list *every* subdirectory here as a potential
agent, including this one — `lessons` will show up in the dropdown and error
cleanly with "No root_agent found" if picked. Harmless, just ignore it.)
