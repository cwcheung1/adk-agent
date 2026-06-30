"""The agent definition.

``root_agent`` is the single required export of an ADK agent package — it is
what ``adk run adk_agent`` / ``adk web`` discover, and what our CLI imports.

This is the most barebones useful shape: one LLM-backed agent with a name, a
description, and a system instruction. The model is pluggable via the
``ADK_MODEL`` env var; by default we use Anthropic Claude through LiteLLM.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# LiteLLM model string format is "<provider>/<model-id>". For Anthropic this
# reads the ANTHROPIC_API_KEY env var. Swap this to e.g. "gemini-2.0-flash"
# (a bare string, no LiteLlm wrapper) to use Gemini instead.
MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")

SYSTEM_INSTRUCTION = (
    "You are a concise, helpful assistant. "
    "Answer the user's question directly and accurately. "
    "Prefer short, well-structured answers. "
    "If you are unsure or lack the information, say so plainly instead of guessing."
)

root_agent = LlmAgent(
    name="adk_agent",
    model=LiteLlm(model=MODEL),
    description="A minimal question-answering assistant.",
    instruction=SYSTEM_INSTRUCTION,
)
