"""ParallelAgent: three sub-agents answering off the same user question
concurrently, each into its own state key, fanned back in by a synthesizer.

Unlike writer_pipeline's chain (each step needs the previous one's output),
these three don't depend on each other at all — pros/cons/risks can be worked
out independently. SequentialAgent would run them one after another for no
reason; ParallelAgent runs them at the same time.

Composability note: this SequentialAgent's first "step" is itself a
ParallelAgent. Works because every workflow agent implements the same
BaseAgent contract (run_async -> yields events) regardless of what it does
internally — see lessons/05-workflow-agents.md.
"""

import os

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from adk_agent.config import load_secrets

load_secrets()

MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")


def angle_agent(name: str, angle: str, output_key: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=LiteLlm(model=MODEL),
        description=f"Answers the {angle} angle of the user's question.",
        instruction=(
            f"Given the user's question, list up to 3 concise {angle}. "
            "Bullet points only, no preamble."
        ),
        output_key=output_key,
    )


fanout = ParallelAgent(
    name="fanout",
    description="Runs pros/cons/risks angles concurrently.",
    sub_agents=[
        angle_agent("pros_agent", "pros / benefits", "pros"),
        angle_agent("cons_agent", "cons / downsides", "cons"),
        angle_agent("risks_agent", "risks / things that could go wrong", "risks"),
    ],
)

synthesizer = LlmAgent(
    name="synthesizer",
    model=LiteLlm(model=MODEL),
    description="Merges the three angles into one balanced answer.",
    instruction=(
        "Pros:\n{pros}\n\nCons:\n{cons}\n\nRisks:\n{risks}\n\n"
        "Write one short, balanced synthesis of these three angles, answering "
        "the user's original question. Output only the synthesis."
    ),
    output_key="final",
)

root_agent = SequentialAgent(
    name="research_fanout",
    description="Fan out three independent angles concurrently, then synthesize.",
    sub_agents=[fanout, synthesizer],
)
