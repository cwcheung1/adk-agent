# 5c. Agent-as-tool

## Concept

A control-flow choice, not a wire protocol: `AgentTool(agent=...)` wraps *any*
agent as a plain **tool** — calling it is a function call that returns a
value, and the caller keeps control afterward. This is a different axis from
lesson 4 (A2A), not a competitor to it — more on that below, since it's an
easy thing to conflate at first (it was for me too).

## Analogy

`transfer_to_agent` (lesson 4) is transferring a phone call to another
department — you're gone, they finish the conversation, possibly over many
exchanges. `AgentTool` is texting a specialist friend a question and getting
a text back — you're still on your original call the whole time, you just now
have their answer to use however you want, including saying more afterward.

## How it works

1. `AgentTool.__init__` sets `super().__init__(name=agent.name,
   description=agent.description)` — from the calling LLM's point of view,
   the wrapped agent is just a callable tool with that name/description.
2. Read `AgentTool.run_async` in the SDK: on each call it builds a
   **completely separate** `Runner` + fresh `InMemorySessionService` for the
   wrapped agent, runs it to completion, and returns just its final text as
   the tool's return value. The parent's own conversation/session is
   untouched.
3. Because it's "just a tool," the calling agent's LLM can call it, get a
   result, and keep generating — including producing more text afterward,
   which `transfer_to_agent` can't do (that hands off permanently for the
   turn).

### Is this just MCP with extra steps?

Fair instinct — it *feels* MCP-adjacent because both show up to the LLM as a
callable. That's not a coincidence, and it's not a redundancy either: `Tool`
is a generic contract in ADK, the exact same pattern as `Agent` being generic
(lesson 5's "why is a workflow agent still an agent" — same question, same
answer, one level over). Checked the class hierarchy:

```
AgentTool    -> BaseTool
McpTool      -> BaseTool
FunctionTool -> BaseTool
```

Three siblings. `BaseTool`'s whole contract is `_get_declaration()` (what to
tell the model) and `run_async(args, tool_context)` (what happens when
called). `McpTool` implements that by forwarding the call over the MCP wire
protocol to a separate process running arbitrary — usually non-agentic — code.
`AgentTool` implements the *same interface* by running an entire nested agent
to completion. Identical shape to the model, completely different thing
happening behind it: one is "ask a separate process," the other is "ask
another mind." ADK didn't invent a fourth mechanism for "get a bounded answer
from another LLM" because tool-calling already *is* the solved shape for
"bounded call, get a value, keep going" — reusing it means the parent LLM
never needs to know or care whether it's calling code or calling an agent.

### Is this a competitor to A2A?

No — orthogonal axis, and this is the part worth being precise about.
`RemoteA2aAgent` (lesson 4) is just another `BaseAgent` —
`issubclass(RemoteA2aAgent, BaseAgent)` is `True`. `AgentTool` wraps *any*
`BaseAgent`. So nothing stops you from wrapping a `RemoteA2aAgent` in an
`AgentTool` instead of putting it in `sub_agents` — same remote agent, same
A2A wire protocol underneath, different control-flow semantics on top:

|  | mechanism | control-flow |
|---|---|---|
| `sub_agents=[remote_agent]` | `transfer_to_agent` | open-ended hand-off — remote agent can own the rest of the conversation, possibly many turns |
| `tools=[AgentTool(remote_agent)]` | tool call | one bounded call-and-return — coordinator never loses control |

"Local vs. remote-over-A2A" (which agent) and "delegate vs. call-as-tool"
(how you invoke it) are independent choices. `a2a_as_tool/agent.py` proves
it: the exact same `RemoteA2aAgent` as `a2a_consumer/`, wrapped in
`AgentTool` instead of `sub_agents` — verified live, every event's `author`
stays `a2a_coordinator`, never `utility_agent`, even though the call crossed
the network exactly like `a2a_consumer` did.

## Look at

1. `agent_as_tool/agent.py` — `poet` (local `LlmAgent`) wrapped in
   `AgentTool`, never a `sub_agent` of `coordinator`.
2. `a2a_as_tool/agent.py` — the *same remote agent* as `a2a_consumer/agent.py`
   (`RemoteA2aAgent` pointed at the A2A server), but wrapped in `AgentTool`
   instead of put in `sub_agents`. Diff the two files — the only structural
   change is `sub_agents=[remote_utility_agent]` becoming
   `tools=[AgentTool(agent=remote_utility_agent)]`.

## Run this

```bash
make tool-ask Q="what is the speed of light?"
```
Look for **two** `[coordinator]:` lines — the direct answer, then (after the
tool call) the haiku, both attributed to `coordinator`. Never a `[poet]:`
line — `poet` never gets a turn of its own.

Then the A2A-as-tool version (needs `make a2a-serve` running in another
terminal first):
```bash
make a2a-tool-ask Q="what time is it?"
```
Same remote agent as lesson 4's `a2a_consumer`, but the coordinator restates
the answer and adds commentary afterward instead of going silent — proof it
kept control even though the call went over the network.

Confirm precisely with the raw event trace (works for either):
```bash
uv run adk run a2a_as_tool --jsonl "roll two dice" 2>/dev/null | \
  python3 -c "
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('{'): continue
    d = json.loads(line)
    for p in d.get('content', {}).get('parts', []):
        if 'functionCall' in p: print(d['author'], 'CALL', p['functionCall']['name'])
        if 'text' in p: print(d['author'], 'TEXT', p['text'][:60])
"
```
Every line's author is `a2a_coordinator` — compare against lesson 4's trace,
where the author literally becomes `utility_agent` after `transfer_to_agent`.

## You'll know it clicked when

You can explain why `AgentTool`, `McpTool`, and `FunctionTool` are siblings
rather than `AgentTool` being some special case of MCP — and, separately, how
you'd decide between `sub_agents=[remote_agent]` and
`tools=[AgentTool(remote_agent)]` for a *remote* agent specifically (hint:
does the remote agent ever need to ask the user a follow-up question mid-task,
or is one bounded request/response enough?).
