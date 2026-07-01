# 6. Observability — seeing what actually happened

## Concept

Every model call and tool call ADK makes gets turned into an OpenTelemetry
span and shipped to Langfuse. This is what lets you inspect a run *after the
fact* — full prompts, tool inputs/outputs, timing, cost — instead of only
whatever the CLI happened to print.

## Analogy

The `adk web` **Events** panel (used in every lesson above) is the live view —
useful while a session is open, gone once it closes. Langfuse is the
black-box flight recorder: every run, kept, searchable, comparable across
time. Same underlying event data, different lifespan.

## How it works

1. `adk_agent/observability.py`'s `setup_observability()` checks for
   `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` in the environment. Absent →
   no-op, the agent runs exactly the same without them.
2. If present, `GoogleADKInstrumentor().instrument()` (from
   `openinference-instrumentation-google-adk`) patches ADK's internals so
   every model/tool call automatically becomes a span — no changes needed
   anywhere else in the codebase, including `writer_pipeline/` and
   `a2a_consumer/`.
3. `atexit.register(client.flush)` exists because short-lived CLI runs
   (`make ask`) can exit before background-buffered spans finish sending —
   without the explicit flush, traces would silently go missing for one-shot
   commands specifically (long-running processes like `make web` don't have
   this problem).

## Look at

`adk_agent/__init__.py` — calls `setup_observability()` before importing
`agent.py`, same ordering concern as credential loading (lesson 1): anything
that needs to patch/read config before the agent object gets built has to run
first.

## Run this

```bash
make langfuse-check
```

Then run anything from the earlier lessons (`make ask`, `make stage5-ask`,
etc.) and check https://us.cloud.langfuse.com — each call should produce a
trace with nested spans per model/tool call. For `writer_pipeline`
specifically, you should see three separate model-call spans nested under one
trace — a good way to visually confirm the sequential structure from lesson 5
without reading `adk run`'s text output.

## You'll know it clicked when

You can explain why `make ask` needs the explicit `atexit.register(flush)`
call but `make web` doesn't.
