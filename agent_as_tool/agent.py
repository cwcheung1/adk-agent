"""Agent-as-tool: a third way to combine agents, distinct from both A2A
(lesson 4, transfer_to_agent) and workflow agents (lessons 5/5b).

`sub_agents=[...]` (A2A/dynamic delegation) hands the ENTIRE turn to the
sub-agent — the coordinator never speaks again after transferring.
`AgentTool(agent)` wraps an agent as a TOOL instead: calling it is a normal
function call that returns a value, and the caller keeps control afterward to
do more work with that value. Verified by reading AgentTool.run_async in the
SDK: it spins up a completely separate Runner + fresh InMemorySessionService
for the wrapped agent, runs it to completion, and returns just its final text
as the tool's return value — the parent's conversation turn is untouched.

`poet` here never talks to the user directly and is never a `sub_agent` of
`coordinator` — it's exposed as a tool named after `poet.name`
(AgentTool.__init__ sets `name=agent.name, description=agent.description`),
so the coordinator's LLM sees a callable named "poet", not another agent to
hand off to.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from adk_agent.config import load_secrets

load_secrets()

MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")

poet = LlmAgent(
    name="poet",
    model=LiteLlm(model=MODEL),
    description="Writes a short haiku about a given topic.",
    instruction=(
        "Write a 3-line haiku about the given topic. "
        "Output only the haiku, no commentary, no preamble."
    ),
)

root_agent = LlmAgent(
    name="coordinator",
    model=LiteLlm(model=MODEL),
    description="Answers questions directly, then always appends a haiku via the poet tool.",
    instruction=(
        "Answer the user's question directly and concisely, in 2-3 sentences. "
        "Then ALWAYS call the `poet` tool, passing the main topic of the "
        "question as the request, and append its haiku to your answer under "
        "a '---' line. Never skip the haiku, even for unrelated-seeming topics."
    ),
    tools=[AgentTool(agent=poet)],
)
