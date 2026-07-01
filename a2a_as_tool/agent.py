"""Answers a real question: is agent-as-tool (lesson 5c) a competing
mechanism with A2A (lesson 4), or orthogonal to it?

`RemoteA2aAgent` (used in a2a_consumer/ as a `sub_agent`, i.e. delegation) is
just another `BaseAgent` subclass — confirmed: `issubclass(RemoteA2aAgent,
BaseAgent)` is True. `AgentTool` wraps *any* `BaseAgent`. So there is nothing
stopping you from wrapping a `RemoteA2aAgent` in an `AgentTool` instead of
putting it in `sub_agents` — same remote agent, same A2A wire protocol
underneath, different control-flow semantics on top:

    sub_agents=[remote_agent]      -> transfer_to_agent: open-ended hand-off,
                                       remote agent can own the rest of the
                                       conversation, possibly many turns
    tools=[AgentTool(remote_agent)] -> one bounded call-and-return, coordinator
                                        never loses control, always speaks
                                        again after

"A2A" (the wire protocol, lesson 4) and "delegate vs. call-as-tool" (the
control-flow choice, lesson 5c) are two independent axes — this file is the
same remote agent as a2a_consumer/, reached the *other* way.

Prereq: the A2A server must be running (see `make a2a-serve`).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

load_dotenv(".env", override=False)
load_dotenv(Path.home() / ".config" / "secrets" / "secrets.env", override=False)

MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")
REMOTE_AGENT_URL = os.getenv("REMOTE_AGENT_URL", "http://localhost:18001")

remote_utility_agent = RemoteA2aAgent(
    name="utility_agent",
    description="Remote ADK agent (reached over A2A) that can tell the current time and roll dice.",
    agent_card=f"{REMOTE_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=False,
)

root_agent = LlmAgent(
    name="a2a_coordinator",
    model=LiteLlm(model=MODEL),
    description="Calls a remote A2A agent as a TOOL, not a hand-off.",
    instruction=(
        "For anything about the current time/date or rolling dice, call the "
        "`utility_agent` tool to get the answer. Then ALWAYS continue: restate "
        "the result in your own words and add one short sentence of your own "
        "commentary. Never stop right after the tool call."
    ),
    tools=[AgentTool(agent=remote_utility_agent)],
)
