"""LoopAgent: repeat a critique/revise cycle until the critic is satisfied
(or a safety-net max_iterations is hit) — an iterative version of
writer_pipeline's one-shot draft -> critique -> revise.

The loop-exit mechanism, verified by reading LoopAgent._run_async_impl in the
SDK: a LoopAgent keeps re-running its sub_agents in order until either (a)
max_iterations is reached, or (b) any event's `event.actions.escalate` is
True. ADK ships a ready-made tool for (b): `google.adk.tools.exit_loop_tool
.exit_loop` just sets `tool_context.actions.escalate = True`. Give an LlmAgent
that tool and instruct it to call the tool once it's satisfied — the model
decides *when* to stop, the LoopAgent just enforces the mechanics.

critic and reviser both read/write the SAME state key ("draft") — each loop
iteration critiques whatever the previous iteration revised it into.
"""

import os

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.exit_loop_tool import exit_loop

from adk_agent.config import load_secrets

load_secrets()

MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")

drafter = LlmAgent(
    name="drafter",
    model=LiteLlm(model=MODEL),
    description="Writes a first-pass answer.",
    instruction=(
        "Answer the user's question directly and concisely, in 2-4 sentences. "
        "This is a first draft — don't hedge or over-explain."
    ),
    output_key="draft",
)

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model=MODEL),
    description="Critiques the current draft; ends the loop once satisfied.",
    instruction=(
        "Here is the current draft answer:\n\n{draft}\n\n"
        "If it's accurate, complete, and well-explained, call `exit_loop` and "
        "say briefly why it's ready — do not restate the draft. "
        "Otherwise, write at most 2 concrete, actionable pieces of feedback "
        "for the reviser (no preamble, no exit_loop call)."
    ),
    tools=[exit_loop],
    output_key="critique",
)

reviser = LlmAgent(
    name="reviser",
    model=LiteLlm(model=MODEL),
    description="Revises the draft using the critique, in place.",
    instruction=(
        "Current draft:\n{draft}\n\nFeedback:\n{critique}\n\n"
        "Rewrite the draft to address the feedback. Output only the revised "
        "draft, nothing else — this replaces the draft for the next round."
    ),
    output_key="draft",  # overwrites the same key critic just read
)

refine = LoopAgent(
    name="refine",
    description="Repeats critique -> revise until the critic calls exit_loop.",
    sub_agents=[critic, reviser],
    max_iterations=3,  # safety net if the critic never calls exit_loop
)

root_agent = SequentialAgent(
    name="refine_loop",
    description="Draft once, then iteratively critique+revise until satisfied.",
    sub_agents=[drafter, refine],
)
