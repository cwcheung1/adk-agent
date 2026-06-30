"""A tiny MCP server (stdio transport) exposing tools our agent can call.

This is the *server* side of MCP — we implement the tools here. The agent
connects to it as an MCP *client* (see the McpToolset in agent.py), which
launches this file as a subprocess and speaks the MCP protocol over stdin/stdout.

Run it standalone to sanity-check it:
    python adk_agent/mcp_server.py        # then it waits for MCP messages on stdin
"""

import datetime
import random

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("adk-agent-utils")


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
    # Default transport is stdio, which is what McpToolset's StdioServerParameters expects.
    mcp.run()
