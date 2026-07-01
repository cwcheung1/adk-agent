"""Stage 5: workflow agents — deterministic composition, not LLM-driven delegation.

Everything in adk_agent/ and a2a_consumer/ used *dynamic* control flow: the
model itself decides whether to call a tool or transfer to a sub-agent.
`SequentialAgent` is the opposite mode — *we* author the order, the LLM has no
say in what runs next. This is the direct LangGraph analogue: an author-defined
graph instead of an LLM-driven decision.

Three plain LlmAgents chained by `output_key`/`{state_key}` templating:
    drafter  -> writes session.state["draft"]
    critic   -> reads {draft},   writes session.state["critique"]
    reviser  -> reads {draft} and {critique}, writes session.state["final"]

`output_key` is ADK's mechanism for an agent to write its final text response
into session state under that key. A plain string `instruction` containing
`{some_key}` gets that value substituted from session.state automatically
(see google.adk.utils.instructions_utils.inject_session_state) — no manual
prompt-building required to pass one agent's output to the next.

Try it: `make stage5-ask Q="what is the speed of light?"` and diff the
drafter's answer against the reviser's — the critique step should visibly
change something. Or `adk web` and watch all three steps run in the Events
trace with no transfer_to_agent in sight.
"""

import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

# Standalone package (like a2a_consumer/) — load secrets before reading env vars.
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
    description="Critiques the draft.",
    instruction=(
        "You are a terse, critical reviewer. Here is a draft answer to the "
        "user's question:\n\n{draft}\n\n"
        "List at most 3 concrete weaknesses, inaccuracies, or missing points. "
        "If the draft is already solid, say so plainly instead of inventing "
        "issues. Output only the critique, no preamble."
    ),
    output_key="critique",
)

reviser = LlmAgent(
    name="reviser",
    model=LiteLlm(model=MODEL),
    description="Produces the final answer, addressing the critique.",
    instruction=(
        "Original draft:\n{draft}\n\n"
        "Critique:\n{critique}\n\n"
        "Write the final, improved answer to the user's original question, "
        "addressing the critique where it's valid. Output only the final "
        "answer — no meta-commentary about the revision process."
    ),
    output_key="final",
)

root_agent = SequentialAgent(
    name="writer_pipeline",
    description="Draft -> critique -> revise pipeline (deterministic, not LLM-delegated).",
    sub_agents=[drafter, critic, reviser],
)
