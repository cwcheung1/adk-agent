# 3. MCP — streamable HTTP transport (and why it's not SSE)

## Concept

stdio only works when the client can spawn the server (lesson 2). When the
tool server is something else — long-running, shared across multiple
agents/processes, on another machine — MCP needs a network transport. The
current one is called **Streamable HTTP**, and it deliberately replaced an
older transport that used SSE as its backbone.

## Analogy

- **WebSockets** = a phone call. Either side talks whenever it wants, one
  connection, fully two-way.
- **SSE (bare)** = a radio broadcast you've subscribed to. Purely one-way,
  server → you. To talk back you need an entirely separate channel.
- **Streamable HTTP** = a phone call where you always dial first. You ask a
  question (`POST`), you get an answer back — sometimes as one reply,
  sometimes as several chunks read out over the same call if the answer's
  long. The server never calls you out of the blue.

## How it works

**The old transport ("HTTP+SSE", spec 2024-11-05):** two endpoints. Client
opens `GET /sse` and keeps it open — *every* response comes back over this one
stream, for as long as the connection lives. Requests go out via a separate
`POST /messages`, which just returns a bare `202 Accepted`; the real answer
shows up later, asynchronously, on the SSE stream.

Why this fell out of favor:
- The `GET /sse` stream has to stay pinned to one specific server process. A
  load-balanced `POST` can land on a different replica than the one holding
  the client's SSE stream — that replica has no way to deliver the response
  without extra shared-pubsub plumbing. Bad fit for horizontal scaling.
- Long-lived connections don't survive typical infra well — proxies,
  load balancers, and scale-to-zero platforms (Cloud Run, Lambda) tend to
  buffer or kill idle long connections.
- You can't just `curl` it — the response to your request never comes back on
  the connection you sent it on.

**The current transport (Streamable HTTP, spec 2025-03-26+):** one endpoint.
`POST` a JSON-RPC message, get the response back **directly in that same HTTP
response body** — ordinary, statelessly-load-balanceable request/response.
SSE becomes *optional*: the server can upgrade a single response into an SSE
stream only if it needs to send back multiple messages for that one request
(progress updates, streamed partials) — tied to that request, then closed.
Confirmed by reading the actual server code
(`mcp/server/streamable_http.py`): it uses `sse_starlette.EventSourceResponse`
internally, but only as the encoding for a single response, not as a mandatory
always-open channel.

That's the real shape of "bidirectional" here: **client always initiates,
server always responds to that specific request** (possibly with several
chunks). It's not true unsolicited server-push like WebSockets or classic SSE.

## Look at

1. `adk_agent/mcp_server.py` — `mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))`.
   Same tool definitions as lesson 2, different transport, chosen at runtime.
2. `adk_agent/agent.py` — the `if _MCP_TRANSPORT == "streamable-http":` branch,
   building `StreamableHTTPConnectionParams(url=".../mcp")` instead of
   spawning a subprocess.
3. `adk_agent/mcp_http_check.py` — a raw client (no ADK) doing
   `initialize` → `list_tools` → `call_tool` against the HTTP server. MCP has
   no plain-GET manifest like A2A's agent card, so this is what "just check
   it's up" looks like for MCP.

## Run this

Two terminals:

```bash
# terminal 1 — the server runs standalone now, nobody spawns it
make mcp-serve

# terminal 2
make mcp-http-check                                          # raw protocol check
MCP_TRANSPORT=streamable-http make ask Q="what time is it?"  # full agent, over HTTP
```

Same agent code, same tools, only `MCP_TRANSPORT` changed — proof the
transport is genuinely swappable underneath `McpToolset`.

## You'll know it clicked when

You can explain why the old MCP HTTP transport needed **two** endpoints and
the new one needs **one**, and why that difference specifically matters for
running behind a load balancer.
