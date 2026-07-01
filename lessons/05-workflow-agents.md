# 5. Workflow agents — deterministic composition

## Concept

Everything in lessons 2–4 used **dynamic** control flow: the LLM itself
decides whether to call a tool, or whether to hand off to another agent.
Workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) are the
opposite mode — *you* author the order at write-time, and the LLM has no say
in what runs next.

## Analogy

If you know LangGraph: this is finally the mode you're used to — you author
the graph instead of trusting the model to route itself. `SequentialAgent` is
a straight-line chain of nodes; `ParallelAgent` is a fan-out; `LoopAgent` is a
loop with a stop condition. Everything before this lesson had no author-defined
graph at all — it was 100% "LLM decides."

If you don't: think of `transfer_to_agent` (lesson 4) as asking a smart
assistant "who should handle this?" every time, versus a workflow agent being
an assembly line — station 1 always feeds station 2, no judgment call
involved.

## How it works

1. `SequentialAgent(sub_agents=[a, b, c])` runs each sub-agent once, in that
   fixed order. No branching, no LLM decision about what's next.
2. Each `LlmAgent` in the chain has an `output_key` — its final text response
   gets written to `session.state[output_key]` automatically. This is a
   first taste of ADK's state model (full version is lesson 6/Chapter 4).
3. A later agent's plain string `instruction` can reference `{some_key}` and
   ADK substitutes it from session state before calling the model —
   confirmed by reading `google.adk.utils.instructions_utils.inject_session_state`,
   which runs on any *plain string* instruction (an `InstructionProvider`
   callable bypasses this and has to build its own prompt).
4. `ParallelAgent` (concurrent fan-out) and `LoopAgent` (repeat until a
   condition/`max_iterations`) are the other two primitives — same underlying
   idea of author-defined structure, covered in their own lesson:
   [05b](./05b-parallel-and-loop.md).

### Why is a workflow agent still called an *agent*?

It has no LLM, no instruction, no tools — so why is `SequentialAgent` in the
same family as `LlmAgent`? Checked the actual class hierarchy:
`LlmAgent`/`SequentialAgent`/`ParallelAgent`/`LoopAgent` are all **siblings**
directly under `BaseAgent` — not parent/child. `BaseAgent`'s entire contract
is one method: `run_async(context) -> yields events`. Read `SequentialAgent`'s
implementation of it and there's no model call anywhere:

```python
async def _run_async_impl(self, ctx):
    for sub_agent in self.sub_agents:
        async for event in sub_agent.run_async(ctx):
            yield event   # just re-yields each child's events
```

So "agent" in ADK means "implements the run-and-yield-events contract," not
"is LLM-backed." The payoff: because every workflow agent satisfies the exact
same interface as `LlmAgent`, they nest arbitrarily —
`SequentialAgent(sub_agents=[ParallelAgent(...), LlmAgent(...)])` just works,
no special-casing. Same reason a compiled LangGraph graph can be used as a
single node inside another graph.

## Look at

`writer_pipeline/agent.py` — three `LlmAgent`s (`drafter` → `critic` →
`reviser`), each with an `output_key`, chained by `{draft}`/`{critique}`
references in the later instructions, wrapped in one
`SequentialAgent(sub_agents=[drafter, critic, reviser])` as `root_agent`.

## Run this

```bash
make stage5-ask Q="explain how a hash map works"
```

`adk run` prints one `[agent_name]: ...` line per step — the fastest way to
see a pipeline without a browser. Look for the critic actually catching
something concrete, and the reviser visibly incorporating it (try a factual
or technical question — the critique tends to be a no-op on very simple
questions since there's nothing to catch).

Or `adk web` → pick `writer_pipeline` → **Events** trace: you'll see three
LLM calls in a fixed sequence, with **no** `transfer_to_agent` event anywhere
— that absence is the tell that this is deterministic, not delegated.

## You'll know it clicked when

You can explain what `{draft}` in the critic's instruction actually resolves
to at call time, and why that only works because `instruction` is a plain
string rather than a callable.
