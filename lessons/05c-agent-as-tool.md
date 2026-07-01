# 5c. Agent-as-tool

## Concept

A third way to combine two agents, distinct from both lesson 4 (A2A —
`transfer_to_agent` hands off the entire conversation turn) and lessons
5/5b (workflow agents — no LLM decision at all). `AgentTool(agent=...)` wraps
an agent as a plain **tool**: calling it is a function call that returns a
value, and the caller keeps control afterward to do more with it.

## Analogy

`transfer_to_agent` (A2A) is transferring a phone call to another department
— you're gone, they finish the conversation. `AgentTool` is more like texting
a specialist friend a question and getting a text back — you're still on your
original call the whole time, you just now have their answer to use however
you want, including saying more afterward.

## How it works

1. `AgentTool.__init__` sets `super().__init__(name=agent.name,
   description=agent.description)` — from the calling LLM's point of view,
   the wrapped agent is just a callable tool with that name/description, not
   another agent it could hand off to.
2. Read `AgentTool.run_async` in the SDK: on each call it builds a
   **completely separate** `Runner` + fresh `InMemorySessionService` for the
   wrapped agent, runs it to completion, and returns just its final text as
   the tool's return value. The parent's own conversation/session is
   untouched by any of this.
3. Because it's "just a tool," the calling agent's LLM can call it, get a
   result, and keep generating — including producing more text afterward,
   which `transfer_to_agent` can't do (that hands off permanently for the
   turn).

## Look at

`agent_as_tool/agent.py` — `poet` is a plain `LlmAgent`, never listed as a
`sub_agent` of anything. `coordinator` has `tools=[AgentTool(agent=poet)]`
and is instructed to always call it and append the result to its own answer.

## Run this

```bash
make tool-ask Q="what is the speed of light?"
```
Look for **two** `[coordinator]:` lines — the direct answer, then (after the
tool call) the haiku, both attributed to `coordinator`. You should never see
a `[poet]:` line — `poet` never gets a turn of its own.

Confirm precisely with the raw event trace:
```bash
uv run adk run agent_as_tool --jsonl "what is the speed of light?" 2>/dev/null | \
  python3 -c "
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('{'): continue
    d = json.loads(line)
    for p in d.get('content', {}).get('parts', []):
        if 'functionCall' in p: print(d['author'], 'CALL', p['functionCall']['name'])
        if 'text' in p: print(d['author'], 'TEXT', p['text'][:40])
"
```
Every line's author is `coordinator` — compare this against lesson 4's A2A
trace, where the author literally becomes the sub-agent's name after
`transfer_to_agent`.

## You'll know it clicked when

You can explain, for a task you're designing yourself, how to decide between
`sub_agents=[...]` (A2A/delegation) and `AgentTool(...)` — hint: does the
coordinator need to *do anything else* with the result, or is handing off the
whole turn fine?
