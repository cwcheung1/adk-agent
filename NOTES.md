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
- [x] **Stage 3** — MCP tool: we run our *own* MCP server (`mcp_server.py`) and
      the agent calls it via `McpToolset`. See the tool call in the Events stream.
- [x] **Stage 4** — A2A: expose the agent (`a2a_server.py`, `to_a2a`) and consume
      it from a second agent (`a2a_consumer/`, `RemoteA2aAgent`).
- [x] **Observability** — Langfuse tracing via OpenInference (`observability.py`).
- [x] **Stage 5** — workflow agents: `SequentialAgent` (`writer_pipeline/`, a
      draft → critique → revise chain via `output_key`/`{state}` templating),
      `ParallelAgent` (`research_fanout/`, concurrent fan-out + synthesize),
      `LoopAgent` (`refine_loop/`, critique/revise until satisfied via
      `exit_loop` + `escalate`), and agent-as-tool (`agent_as_tool/`,
      `AgentTool` — an agent called as a function, not delegated to).
      **Chapter 3 (multi-agent orchestration) complete.**
- [x] **Stage 6a** — persistent sessions + state scoping (`persistent_agent/`,
      `user:`-prefixed state survives across separate sessions via
      `SqliteSessionService`, verified against the raw DB rows). Chapter 4
      still missing: `MemoryService`/RAG, `adk eval`.
- [ ] **Stage 7** — deploy beyond local Docker (Cloud Run / Vertex Agent Engine)

## MCP (Stage 3)

Two sides:
- **Server** (`mcp_server.py`) — we implement tools with `FastMCP`.
- **Client** (`agent.py`) — `McpToolset(...)`, connection params depend on transport.

Why MCP vs a plain ADK function tool? A function tool lives *in* your agent
process; an MCP tool is a separate process/server you can reuse across agents and
frameworks (the same server works with Claude Desktop, Cursor, etc.). Same idea
as LangChain's MCP adapters.

### Two transports, chosen by `MCP_TRANSPORT`

**stdio (default).** `McpToolset(StdioConnectionParams(StdioServerParameters(
command=sys.executable, args=[mcp_server.py])))`. ADK **spawns** `mcp_server.py`
as a subprocess and talks over its stdin/stdout — plain OS pipes, like
`cmd1 | cmd2`. No socket, no port: the wire format is just newline-delimited
JSON-RPC messages written to the child's stdin and read from its stdout (see
`mcp.client.stdio.stdio_client` in the SDK). This only works because the
*client* owns the server's process lifecycle — guaranteed same machine.

**streamable-http.** `mcp_server.py` runs standalone (`make mcp-serve`), and
the agent connects over the network via `StreamableHTTPConnectionParams(url=
"http://host:port/mcp")` (`MCP_TRANSPORT=streamable-http make ask Q=...`).
Needed when the server isn't something you spawn — a shared tool server other
agents/processes also hit, or one that outlives any single client. Sanity-check
independent of ADK with `make mcp-http-check` (uses the raw `mcp` client SDK:
`initialize` → `list_tools` → `call_tool`).

**Why not SSE?** MCP's original HTTP transport (spec 2024-11-05, "HTTP+SSE")
required a mandatory long-lived `GET /sse` stream pinned to one server process
for *all* responses, plus a separate `POST /messages` that just returned `202`
— bad fit for load-balanced/serverless infra, and proxies tend to kill idle
long connections. The 2025-03-26 spec replaced it with **Streamable HTTP**: a
single endpoint where `POST` returns the JSON-RPC response directly in the
HTTP body (ordinary request/response), and SSE becomes an *optional* per-request
upgrade only when the server needs to stream multiple messages back. We
implement the new one; there's no `sse` option in `mcp_server.py` on purpose.

## A2A (Stage 4)

- **Expose**: `to_a2a(root_agent, port=N)` → an ASGI app; serve with uvicorn.
  Publishes an agent card at `/.well-known/agent-card.json`. Our card even lists
  the MCP tools as A2A *skills* — the stack composes (MCP tool → agent → A2A skill).
- **Consume**: `RemoteA2aAgent(agent_card=URL + AGENT_CARD_WELL_KNOWN_PATH)` used
  as a normal `sub_agent`. The coordinator delegates via `transfer_to_agent`, the
  call crosses the process boundary over A2A (JSON-RPC), runs remotely, returns.
- **MCP vs A2A** (easy to conflate): MCP connects an agent to *tools*; A2A connects
  an agent to *other agents*. Different layers, often used together.
- Both are flagged `[EXPERIMENTAL]` in ADK today (warnings are expected/harmless).

## Workflow agents (Stage 5)

Everything before this stage used **dynamic** control flow — the LLM itself
decides whether to call a tool (MCP) or hand off to another agent
(`transfer_to_agent` in A2A). `writer_pipeline/agent.py` is the other mode:
**deterministic** composition, where *we* author the order and the LLM has no
say in what runs next. This is the direct LangGraph analogue — an
author-defined graph instead of an LLM-driven decision.

- `SequentialAgent(sub_agents=[a, b, c])` runs each sub-agent in that fixed
  order, once each, no branching.
- Each `LlmAgent` has an `output_key` — its final text response gets written
  to `session.state[output_key]` automatically, no manual wiring.
- A later agent's plain string `instruction` can reference `{some_key}` and
  ADK substitutes it from session state before calling the model (see
  `google.adk.utils.instructions_utils.inject_session_state` — this only
  happens for plain strings; an `InstructionProvider` callable bypasses it and
  must build its own prompt).
Test with `make stage5-ask Q="..."` (uses `adk run`, which prints a
`[agent_name]: ...` line per step — the fastest way to see the pipeline
without a browser) or `adk web` and pick `writer_pipeline` from the dropdown.

### ParallelAgent (`research_fanout/`)

Sub-agents run **concurrently**, not in sequence — use when they don't depend
on each other's output (three independent "angles" on the same question here,
each writing its own `output_key`, fanned in by a `SequentialAgent`-wrapped
synthesizer that reads all three). Verified this is real concurrency, not
just a fast wall-clock, by grepping ADK's own log file
(`/tmp/agents_log/agent.<timestamp>.log`) for the three `LiteLLM completion()`
lines — they fired **4ms apart**, not the 2-3s apart sequential calls would
show. `SequentialAgent(sub_agents=[ParallelAgent(...), synthesizer])` — a
workflow agent nesting another workflow agent works because both just
implement the same `BaseAgent` contract (see `lessons/05-workflow-agents.md`
for why `SequentialAgent` "is" an agent at all).

### LoopAgent (`refine_loop/`)

Repeats its sub-agents in order until either `max_iterations` is hit or any
event carries `event.actions.escalate = True` (read straight from
`LoopAgent._run_async_impl` in the SDK). ADK ships a ready-made tool for the
model to trigger that: `google.adk.tools.exit_loop_tool.exit_loop` just does
`tool_context.actions.escalate = True`. Give an `LlmAgent` that tool and tell
it when to call it — the **model** decides when to stop, `LoopAgent` only
enforces the mechanics (and the `max_iterations` safety net if it never does).
`critic` and `reviser` both read/write the *same* `output_key="draft"` — each
loop iteration critiques whatever the previous one revised it into.

Confirmed the exit mechanism with `adk run --jsonl`, which shows the raw event
structure: `critic` emits text, then `CALL exit_loop` → `RESPONSE exit_loop` →
the event carries `escalate: True` — exactly the SDK source's mechanism, not
an inference. Side effect worth knowing: `exit_loop` also sets
`skip_summarization = True`, so the step that calls it produces **no**
`[critic]: ...` line in `adk run`'s output — don't mistake the missing line
for the loop not running.

## Agent-as-tool (`agent_as_tool/`)

A third way to combine two agents, distinct from both A2A (transfer_to_agent
hands off the **entire turn**) and workflow agents (author-defined structure,
no LLM decision at all). `AgentTool(agent=poet)` wraps an agent as a regular
**tool** — from the calling LLM's point of view it's just a callable named
`poet.name` with `poet.description` (confirmed by reading
`AgentTool.__init__`: `super().__init__(name=agent.name,
description=agent.description)`).

Read `AgentTool.run_async` in the SDK to see what actually happens on a call:
it builds a **completely separate** `Runner` + fresh `InMemorySessionService`
for the wrapped agent, runs it to completion, and returns just its final text
as the tool's return value. The parent's own conversation turn is never
touched — it's a function call that happens to be backed by an LLM, not a
hand-off.

Proved this with `adk run agent_as_tool --jsonl`: every event's `author` is
`coordinator`, **never** `poet` — contrast with A2A (lesson 4), where the
event author literally becomes the sub-agent's name after
`transfer_to_agent`. `coordinator` in this repo answers directly, calls
`poet` as a tool, gets a haiku back, and keeps talking (appends the haiku to
its own answer) — proof it never lost control of the turn.

**`Tool` is generic, same pattern as `Agent`.** `AgentTool`/`McpTool`/
`FunctionTool` are all siblings under `BaseTool` (confirmed via MRO), exactly
like `LlmAgent`/`SequentialAgent`/`RemoteA2aAgent` are siblings under
`BaseAgent`. `McpTool` forwards a call over the MCP wire protocol to a
separate process; `AgentTool` runs a nested agent to completion — same
interface (`_get_declaration()` + `run_async(...)`), different thing behind
it. This means **A2A and agent-as-tool are orthogonal, not competing**:
`RemoteA2aAgent` is just another `BaseAgent`, so it can go in `sub_agents`
(delegate, lesson 4) *or* get wrapped in `AgentTool` (call-and-return).
`a2a_as_tool/agent.py` proves it — the exact same remote agent as
`a2a_consumer/`, wrapped in `AgentTool` instead: verified via `--jsonl` that
the author stays `a2a_coordinator` even though the call crosses the network.

## SessionService is portable, and where it isn't (Chapter 4 follow-up)

`SqliteSessionService`, `DatabaseSessionService`, `InMemorySessionService` are
three siblings under `BaseSessionService` (confirmed via MRO) — not tiers of
each other, and a `Runner` takes exactly one. Overlap worth knowing:
`DatabaseSessionService` explicitly branches on `url.get_backend_name() ==
"sqlite"` in its `__init__`, so it can *also* point at a SQLite file via
SQLAlchemy (`db_url="sqlite+aiosqlite:///..."`) — two independent code paths
to the same storage engine, one lighter (`SqliteSessionService`, raw
`aiosqlite`, no extra deps) and one backend-agnostic
(`DatabaseSessionService`, needs `google-adk[db]` + an async driver per
backend — `asyncpg` for Postgres, since it uses `create_async_engine`, not a
sync engine).

Proved the portability claim isn't just theoretical: ran `persistent_agent`
unchanged against a real (locally Dockerized) Postgres —
`adk run persistent_agent --session_service_uri
"postgresql+asyncpg://postgres:test@localhost:15432/adktest" "..."` — two
separate invocations, same result as SQLite, verified against the raw
Postgres `user_states`/`sessions` rows via `psql` (identical shape to the
SQLite proof). Zero agent code changes — only the storage backend moved.

**Forward-reference for Stage 7 (deployment): don't reach for the Cloud SQL
Auth Proxy sidecar for this project.** Checked current Google guidance (web
search, 2026): for Python specifically, on *both* Cloud Run and GKE, the
recommended connection method is the **Cloud SQL Python Connector**
(`cloud-sql-python-connector`) — in-process, IAM-authenticated, TLS 1.3, no
sidecar container, no certificate/firewall management. The arg-based
Auth Proxy (standalone or sidecar) is the documented fallback for languages
*without* a native connector, not the default recommendation once one exists
— GKE doesn't change this, despite not having Cloud Run's automatic
Unix-socket injection. Wires into `DatabaseSessionService` via its `**kwargs`
→ `create_async_engine(..., creator=connector_callable)`, not a plain URL —
untested here, needs real GCP credentials.

## State scoping + persistence (`persistent_agent/`, Stage 6a)

Every prior stage used `output_key` with **plain, unprefixed** keys — those
live in the `sessions` table (or in-memory equivalent), scoped to one
`session_id`. Start a new session and they're gone. `State`
(`google.adk.sessions.state.State`) defines three prefixes that change
*where* a key is stored: `APP_PREFIX = "app:"`, `USER_PREFIX = "user:"`,
`TEMP_PREFIX = "temp:"`.

Confirmed the actual persistence mechanism by reading
`SqliteSessionService._merge_state`: on session load, `app_state` (one row
per `app_name`, in the `app_states` table) and `user_state` (one row per
`app_name`+`user_id`, in `user_states`) get merged into the session's dict
*ahead of* `session_state` (one row per `session_id`, in `sessions`). A
`user:`-prefixed key set in one session is therefore visible in a brand-new
session for the same `user_id`; a plain key is not.

**We'd been using a persistent SessionService all along without knowing it.**
`adk run`'s default local storage (`--use_local_storage`, on by default) IS
`SqliteSessionService` at `.adk/session.db` — see
`google.adk.cli.utils.local_storage.create_local_database_session_service`.
Every `.adk/session.db` file gitignored across every package in this repo has
been this the whole time. `adk run` also always uses the fixed `user_id =
'test_user'` (`google.adk.cli.cli`) across *separate* invocations — which is
exactly what makes the demo below work with plain `adk run` calls, no custom
`Runner`/`SessionService` wiring needed (unlike every other stage so far).

`persistent_agent/agent.py`: a `remember_name` tool does
`tool_context.state["user:name"] = name`; the instruction reads it back via
`{user:name?}` — the `?` suffix is required for a key that might not exist
yet (a missing key without `?` raises `KeyError` instead of substituting
empty string — see `inject_session_state`).

Verified with **two separate `adk run` process invocations** (not two turns
in one session): tell it your name in call 1, ask "what's my name?" in a
completely fresh call 2 — it remembers. Then verified against the raw SQLite
rows directly (not just trusted the model's answer): `user_states` has one
row, `{"name": "Chi"}`, keyed by `('persistent_agent', 'test_user')`; both
`sessions` rows have `state = '{}'` — the fact lives *only* in the
user-scoped bucket, proving it's not session continuity doing the work.

## Observability (Langfuse)

`observability.py` calls `GoogleADKInstrumentor().instrument()` (OpenInference).
Every model call + tool call becomes an OpenTelemetry span shipped to Langfuse.
No-op without `LANGFUSE_*` keys. Keys live in the central store. Dashboard:
https://us.cloud.langfuse.com . `make langfuse-check` verifies connectivity.

## Gotchas seen so far

- Docs moved from `google.github.io/adk-docs` to **`adk.dev`**.
- Secrets must load *before* `agent.py` reads `os.getenv` — that's why
  `__init__.py` calls `load_secrets()` before `from . import agent`.
