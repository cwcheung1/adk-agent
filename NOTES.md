# ADK learning notes

Running notes as I learn Google ADK. Audience: someone who already knows
LangGraph.

## Mental model: ADK vs LangGraph

| Concept | LangGraph | ADK |
|---|---|---|
| Unit of work | Node (a function) | **Agent** (`LlmAgent`, or a workflow agent) |
| Control flow | edges + conditional edges you author | LLM-driven delegation (`sub_agents`) **or** workflow agents (`Sequential`/`Parallel`/`Loop`) |
| State | typed channels + reducers | `session.state` dict (scoped: `user:`, `app:`, `temp:`), agents write via `output_key` |
| Persistence | checkpointer + `thread_id` | `SessionService` + `MemoryService` |
| Execution | `graph.invoke/stream` | `Runner` yields an **event** stream |
| Tools | LangChain tools | functions, built-ins, MCP, agent-as-tool, wrapped LC/CrewAI tools |
| Models | any LangChain model | Gemini native; others via `LiteLlm` |

Key idea: **LangGraph = you author the control-flow graph. ADK = you compose
agents**, and control flow comes either from the LLM (dynamic delegation) or
from workflow primitives (deterministic).

## Stage 1 anatomy (what's in this repo)

- `agent.py` exports `root_agent` — the *only* required piece. `adk run` /
  `adk web` discover an agent by importing the package and finding `root_agent`.
- The CLI shows the **programmatic** path: `Runner` + `InMemorySessionService`,
  build a `types.Content` message, iterate `runner.run_async(...)` events, take
  the one where `event.is_final_response()` is true.
- Anthropic via LiteLLM: `LiteLlm(model="anthropic/<model-id>")`, reads
  `ANTHROPIC_API_KEY`. The canonical docs use Gemini (`model="gemini-2.0-flash"`
  as a bare string); we use Claude because that's the key in the store.

## Roadmap (increasing complexity)

- [x] **Stage 1** — single agent + system prompt + CLI
- [x] **Stage 2** — Dockerize + Makefile
- [ ] **Stage 3** — add a tool (function tool), watch the event stream show the
      tool call
- [ ] **Stage 4** — multi-agent: a coordinator with `sub_agents` and LLM-driven
      transfer (the ADK analog of a LangGraph router)
- [ ] **Stage 5** — workflow agents (`SequentialAgent` / `ParallelAgent`)
- [ ] **Stage 6** — persistent sessions + memory, then `adk eval`
- [ ] **Stage 7** — deploy beyond local Docker (Cloud Run / Vertex Agent Engine)

## Gotchas seen so far

- Docs moved from `google.github.io/adk-docs` to **`adk.dev`**.
- Secrets must load *before* `agent.py` reads `os.getenv` — that's why
  `__init__.py` calls `load_secrets()` before `from . import agent`.
