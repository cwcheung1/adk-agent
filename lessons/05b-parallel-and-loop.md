# 5b. ParallelAgent and LoopAgent

## Concept

The other two deterministic-composition primitives (lesson 5 covered
`SequentialAgent`). `ParallelAgent` runs its sub-agents **concurrently**
instead of one after another. `LoopAgent` runs its sub-agents **repeatedly**
until something tells it to stop.

## Analogy

`ParallelAgent` is three people researching independently at the same time,
then reconvening — you'd never make them take turns if their work doesn't
depend on each other. `LoopAgent` is "keep revising until your editor says
it's good" — with a hard cap on drafts so you don't loop forever if the
editor's impossible to please.

## How it works

### ParallelAgent

`ParallelAgent(sub_agents=[a, b, c])` runs all three at once. Use it when
sub-agents *don't* need each other's output — `SequentialAgent` would just add
waiting for no reason. Each sub-agent still writes its own `output_key`, so a
following step (typically a `SequentialAgent`-wrapped synthesizer) can read
all of them once they've all finished.

This isn't just "probably faster" — it's verifiable. ADK writes every model
call to a log file (`/tmp/agents_log/agent.<timestamp>.log`); grepping it for
`LiteLLM completion()` lines shows the three calls firing **milliseconds
apart**, not seconds apart the way sequential calls would.

### LoopAgent

`LoopAgent(sub_agents=[...], max_iterations=N)` re-runs its sub-agents in
order, restarting from the top each time, until either `max_iterations` is
hit or any event in that pass carries `event.actions.escalate = True` — read
straight from `LoopAgent._run_async_impl` in the installed SDK, not inferred.

Nothing about a plain `LlmAgent` sets `escalate` on its own — you need a tool
for that. ADK ships one: `google.adk.tools.exit_loop_tool.exit_loop`, whose
entire body is:

```python
def exit_loop(tool_context: ToolContext):
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
```

Give an `LlmAgent` that tool and instruct it when to call it — the **model**
decides when the loop should stop; `LoopAgent` just enforces the mechanics
(and `max_iterations` is the safety net for "never satisfied").

One gotcha `skip_summarization` causes: the step that calls `exit_loop`
produces **no** printed `[agent_name]: ...` line in `adk run`'s output — don't
mistake the missing line for that step not having run.

## Look at

1. `research_fanout/agent.py` — `ParallelAgent(sub_agents=[pros_agent,
   cons_agent, risks_agent])`, each with its own `output_key`, wrapped in
   `SequentialAgent(sub_agents=[fanout, synthesizer])` — a workflow agent
   nesting another workflow agent (works because both are just `BaseAgent`s,
   see lesson 5).
2. `refine_loop/agent.py` — `critic` has `tools=[exit_loop]`; `critic` and
   `reviser` both use `output_key="draft"` — same key, so each loop iteration
   critiques whatever the *previous* iteration revised it into.

## Run this

```bash
make fanout-ask Q="should I switch frameworks for a solo side project?"
```
Then check concurrency for real:
```bash
LOGFILE=$(ls -t /tmp/agents_log/agent.*.log | head -1)
grep "LiteLLM completion" "$LOGFILE"
```
The three timestamps for `pros_agent`/`cons_agent`/`risks_agent` should be
within a few milliseconds of each other.

```bash
make refine-ask Q="explain how a hash map works"
```
Watch for: a first-round critique that finds something concrete, a revision
that addresses it, then either a visible second critique or — if the critic
was satisfied on the very first pass — no second `[critic]` line at all
(that's `skip_summarization`, not a bug). To see the raw mechanism instead of
inferring it from missing output:
```bash
uv run adk run refine_loop --jsonl "explain what tcp is" 2>/dev/null | \
  python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line)
    for p in d.get('content', {}).get('parts', []):
        if 'functionCall' in p: print(d['author'], 'CALL', p['functionCall']['name'])
    if d.get('actions', {}).get('escalate'): print(d['author'], 'ESCALATE=True')
"
```
You should see `critic CALL exit_loop` followed by `critic ESCALATE=True`.

## You'll know it clicked when

You can explain why `research_fanout`'s three angle-agents are safe to
parallelize but `writer_pipeline`'s drafter/critic/reviser (lesson 5) are not
— what's the structural difference between the two that makes one obviously
sequential and the other obviously parallelizable?
