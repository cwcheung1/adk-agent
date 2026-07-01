# 2. MCP — stdio transport

## Concept

MCP (Model Context Protocol) connects an agent to **tools** that live in a
separate process. The default transport, stdio, needs no network at all — the
agent *spawns* the tool server itself and talks to it over the child
process's stdin/stdout.

## Analogy

Exactly `cmd1 | cmd2` in your shell. No socket, no port, no `bind()` — just
two file descriptors every process already has, connected between a parent
and the child it spawned. The only requirement is that they're related as
parent/child, which spawning gives you for free.

## How it works

1. `adk_agent/mcp_server.py` is the **server** — it implements tools with
   `FastMCP` and `@mcp.tool()`. Nothing here is ADK-specific; this is plain
   MCP, the same code would work with Claude Desktop or Cursor.
2. `adk_agent/agent.py`'s `McpToolset(StdioConnectionParams(StdioServerParameters(
   command=sys.executable, args=[mcp_server.py])))` is the **client**. It
   doesn't connect to something already running — it *launches*
   `mcp_server.py` as a subprocess and gets back handles to that new
   process's stdin/stdout.
3. The wire format on those pipes is just **newline-delimited JSON-RPC
   messages** — one JSON object per line, flowing in both directions. No HTTP
   headers, no framing beyond `\n`. (Confirmed by reading the actual SDK:
   `mcp.client.stdio.stdio_client` spawns the process, then runs a
   `stdin_writer` loop that serializes each message + `\n` to the child's
   stdin, and a `stdout_reader` loop that splits the child's stdout on `\n`
   and parses each line.)
4. This only works because the *client* owns the server's process lifecycle —
   guaranteed same machine, guaranteed the server exists for exactly as long
   as the client wants it to.

## Look at

1. `adk_agent/mcp_server.py` — `@mcp.tool()` on `current_time`/`roll_dice`.
2. `adk_agent/agent.py` — the `else:` branch (when `MCP_TRANSPORT` isn't
   `streamable-http`) building `StdioConnectionParams`.

## Run this

```bash
make ask Q="what time is it?"
make ask Q="roll 3d6"
```

Both should show correct tool output. Then *watch* it happen:

```bash
make web
```
`adk_agent` → ask the same question → **Events** panel → find the discrete
`current_time`/`roll_dice` tool-call event, separate from the model's text.

For the deepest proof, bypass ADK entirely and speak raw JSON-RPC to the
server yourself — no client library, just piped text:

```bash
cat > /tmp/handshake.jsonl << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"demo","version":"0.1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"current_time","arguments":{}}}
EOF
timeout 3 uv run python adk_agent/mcp_server.py < /tmp/handshake.jsonl
```

You'll get back two JSON-RPC responses (the `initialize` handshake, then the
tool result) — proof there's no server listening anywhere, just a script
reading stdin and writing stdout.

## You'll know it clicked when

You can explain why `McpToolset` needs no port number anywhere in its config,
and what would break if `mcp_server.py` had a syntax error (hint: it's not
agent startup — the subprocess only gets spawned/fails when a tool is
actually called).
