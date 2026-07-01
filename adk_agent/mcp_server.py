"""A tiny MCP server exposing tools our agent can call.

This is the *server* side of MCP — we implement the tools here. The agent
connects to it as an MCP *client* (see the McpToolset in agent.py). Two
transports are supported, chosen by MCP_TRANSPORT at run time:

- "stdio" (default) — ADK launches this file as a subprocess and speaks MCP
  over its stdin/stdout. No network, no port; see StdioConnectionParams.
- "streamable-http" — this file runs as a standalone, long-lived HTTP server;
  the agent connects over the network via StreamableHTTPConnectionParams.
  This is the *current* MCP HTTP transport (spec 2025-03-26+), which replaced
  the older "HTTP+SSE" transport — a single POST/response endpoint, with SSE
  only as an optional per-request upgrade, not a mandatory always-open stream.

Run it standalone to sanity-check it:
    python adk_agent/mcp_server.py                        # stdio, waits on stdin
    MCP_TRANSPORT=streamable-http python adk_agent/mcp_server.py   # HTTP, waits on the socket
"""

import datetime
import os
import random

from mcp.server.fastmcp import FastMCP

MCP_HTTP_HOST = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "18002"))

# host/port only take effect for the streamable-http transport; stdio ignores them.
mcp = FastMCP("adk-agent-utils", host=MCP_HTTP_HOST, port=MCP_HTTP_PORT)


@mcp.tool()
def current_time() -> str:
    """Return the current UTC date and time.

    Use this whenever the user asks what the time or date is — the model has no
    clock of its own, so it must call this tool.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


@mcp.tool()
def roll_dice(sides: int = 6, count: int = 1) -> dict:
    """Roll `count` dice with `sides` faces each.

    Returns the individual rolls and their total. Use this for any request that
    needs a real random dice roll.
    """
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {"rolls": rolls, "total": sum(rolls)}


if __name__ == "__main__":
    # "stdio" matches StdioConnectionParams (default); "streamable-http" matches
    # StreamableHTTPConnectionParams in agent.py. Deliberately no "sse" option —
    # that's the legacy transport streamable-http replaced.
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
