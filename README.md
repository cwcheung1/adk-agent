# adk-agent

A barebones [Google ADK](https://adk.dev) agent — the smallest useful shape:
one LLM-backed agent with a system prompt, driven by a CLI, and packaged to run
in Docker. Powered by **Anthropic Claude** through ADK's LiteLLM connector.

This is **Stage 1–2** of a learning project that grows in complexity.

- **New to a concept here?** Start with [lessons/](./lessons/) — one file per
  concept: what it is, an analogy, how it actually works, what to look at,
  what to run.
- **Need the dense reference/roadmap version?** See [NOTES.md](./NOTES.md).

## Layout

```
adk-agent/
├── adk_agent/
│   ├── __init__.py      # loads secrets + observability, then the agent package
│   ├── config.py        # central + local credential loading
│   ├── observability.py # Langfuse tracing (OpenInference instrumentation)
│   ├── agent.py         # root_agent = LlmAgent(...) with the MCP toolset
│   ├── mcp_server.py    # our own MCP server (FastMCP): current_time, roll_dice
│   │                    #   supports stdio (default) and streamable-http transports
│   ├── mcp_http_check.py # standalone client sanity-check for the http transport
│   ├── a2a_server.py    # expose root_agent over A2A (to_a2a)
│   └── cli.py           # programmatic Runner loop (one-shot + REPL)
├── a2a_consumer/        # a 2nd agent that calls the first over A2A (RemoteA2aAgent)
├── writer_pipeline/     # SequentialAgent: draft -> critique -> revise (deterministic, not LLM-delegated)
├── research_fanout/     # ParallelAgent: 3 angles concurrently -> synthesizer (SequentialAgent nesting a ParallelAgent)
├── refine_loop/         # LoopAgent: critique/revise repeats until exit_loop (escalate) or max_iterations
├── agent_as_tool/       # AgentTool: an agent called as a function (return value), not delegated to (no turn hand-off)
├── pyproject.toml       # uv-managed; defines the `adk-agent` console script
├── Dockerfile           # slim image; secrets passed at runtime, never baked in
├── Makefile             # all common tasks
└── .env.example         # optional local overrides
```

## Features by stage

- **Stage 1–2** — single `LlmAgent` + system prompt, CLI, Docker, Makefile.
- **Stage 3 (MCP)** — `mcp_server.py` is our own MCP server; the agent calls its
  tools (`current_time`, `roll_dice`) via `McpToolset`. Ask "what time is it?" and
  watch it call the tool. Default transport is stdio (ADK spawns the server);
  set `MCP_TRANSPORT=streamable-http` to instead run it standalone (`make
  mcp-serve`) and connect over HTTP — see NOTES.md for stdio-vs-HTTP and why we
  use Streamable HTTP, not the older HTTP+SSE transport.
- **Stage 4 (A2A)** — `make a2a-serve` exposes the agent over A2A; `a2a_consumer/`
  is a second agent that delegates to it. See NOTES.md for MCP-vs-A2A.
- **Observability** — Langfuse tracing turns on automatically when `LANGFUSE_*`
  keys are in the store. `make langfuse-check` to verify; dashboard at
  https://us.cloud.langfuse.com.
- **Stage 5 (workflow agents)** — three deterministic-composition primitives,
  all in `lessons/05-workflow-agents.md`:
  - `writer_pipeline/` — `SequentialAgent`: drafter → critic → reviser, chained
    via `output_key`/`{state}` templating. `make stage5-ask Q="explain X"`.
  - `research_fanout/` — `ParallelAgent`: 3 independent angles run
    concurrently (verified via log timestamps, not just wall-clock), fanned
    into a synthesizer. `make fanout-ask Q="..."`.
  - `refine_loop/` — `LoopAgent`: critique/revise repeats until the critic
    calls the `exit_loop` tool (`escalate=True`) or `max_iterations` hits.
    `make refine-ask Q="explain X"`.
- **Chapter 3 complete: agent-as-tool** — `agent_as_tool/` wraps an agent as a
  regular tool (`AgentTool`), a 3rd way to combine agents distinct from both
  A2A (hands off the whole turn) and workflow agents (no LLM decision at
  all). `coordinator` calls `poet` as a tool, gets a haiku back, and keeps
  talking — proven via `--jsonl` trace, every event's author stays
  `coordinator`. `make tool-ask Q="explain X"`. See `lessons/05c-agent-as-tool.md`.

## Credentials

The agent reads its API key from a **central, cross-project store**:

```
~/.config/secrets/secrets.env      # chmod 600, never committed
```

Add your key once and every project can use it:

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.config/secrets/secrets.env
make secrets-check        # confirm it's there
```

Precedence: real shell env > project-local `.env` > central store.

## Run it (local)

```bash
make install                       # uv sync
make ask Q="what is an LLM agent?" # one-shot
make chat                          # interactive REPL
make web                           # ADK dev web UI
```

Or without make:

```bash
uv run adk-agent "what is an LLM agent?"
```

## Run it (Docker)

```bash
make docker-build
make docker-run Q="explain Google ADK in one sentence"
make docker-chat                   # interactive, inside the container
```

The image contains no secrets; `make docker-run` injects them with
`--env-file ~/.config/secrets/secrets.env`.

## Switching models

The model is set by the `ADK_MODEL` env var (default
`anthropic/claude-haiku-4-5-20251001`). To use Gemini instead, set
`ADK_MODEL=gemini-2.0-flash` and provide a `GOOGLE_API_KEY` — note Gemini takes
a bare model string, so you'd also drop the `LiteLlm(...)` wrapper in
`agent.py`. See NOTES.md.
