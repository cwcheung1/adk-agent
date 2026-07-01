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
- [ ] **Stage 5** — workflow agents (`SequentialAgent` / `ParallelAgent`)
- [ ] **Stage 6** — persistent sessions + memory, then `adk eval`
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

## Observability (Langfuse)

`observability.py` calls `GoogleADKInstrumentor().instrument()` (OpenInference).
Every model call + tool call becomes an OpenTelemetry span shipped to Langfuse.
No-op without `LANGFUSE_*` keys. Keys live in the central store. Dashboard:
https://us.cloud.langfuse.com . `make langfuse-check` verifies connectivity.

## Gotchas seen so far

- Docs moved from `google.github.io/adk-docs` to **`adk.dev`**.
- Secrets must load *before* `agent.py` reads `os.getenv` — that's why
  `__init__.py` calls `load_secrets()` before `from . import agent`.
