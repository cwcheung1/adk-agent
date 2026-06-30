"""Expose our agent over the A2A (Agent2Agent) protocol.

``to_a2a`` wraps the agent in an ASGI app that publishes an *agent card* and an
A2A endpoint, so other agents (in any A2A-speaking framework) can discover and
call it. Serve it with uvicorn:

    uv run uvicorn adk_agent.a2a_server:a2a_app --host 0.0.0.0 --port $A2A_PORT

Then the public agent card is at:
    http://localhost:$A2A_PORT/.well-known/agent-card.json
"""

import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import root_agent

# `port` is baked into the URLs advertised in the agent card, so it must match
# the port uvicorn serves on. Keep A2A_PORT consistent across both.
A2A_PORT = int(os.getenv("A2A_PORT", "8001"))

a2a_app = to_a2a(root_agent, port=A2A_PORT)
