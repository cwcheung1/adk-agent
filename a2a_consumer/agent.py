"""A second, separate agent that calls the first one over A2A.

This is the *consuming* side of A2A. ``RemoteA2aAgent`` fetches the remote
agent's card and exposes it as a normal sub-agent, so our coordinator can
delegate to it via ADK's usual LLM-driven transfer — even though that agent
lives in another process (and could be another framework entirely).

Prereq: the A2A server must be running (see `make a2a-serve`).
Discover this agent in the dev UI with `adk web` (pick "a2a_consumer").
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

# Standalone credential load (kept independent of the adk_agent package).
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
    name="a2a_consumer",
    model=LiteLlm(model=MODEL),
    description="Coordinator that delegates to a remote agent over A2A.",
    instruction=(
        "You are a coordinator. For anything about the current time/date, or for "
        "rolling dice, delegate to the `utility_agent`. For everything else, "
        "answer directly and concisely."
    ),
    sub_agents=[remote_utility_agent],
)
