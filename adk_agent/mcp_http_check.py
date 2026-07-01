"""Sanity-check the streamable-http MCP server with a real MCP client.

Unlike A2A's agent card (a plain GET a browser/curl can read), MCP has no
unauthenticated manifest endpoint — you have to speak the protocol: open the
streamable-http connection, `initialize`, then `list_tools`/`call_tool`. This
script does exactly that, using the same `mcp` client SDK ADK uses internally.

Run with `make mcp-http-check` (requires `make mcp-serve` running).
"""

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_HTTP_HOST = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = os.getenv("MCP_HTTP_PORT", "18002")
URL = f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}/mcp"


async def main() -> None:
    async with streamablehttp_client(URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"connected: {init.serverInfo.name} (protocol {init.protocolVersion})")

            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])

            result = await session.call_tool("current_time", {})
            print("current_time ->", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
