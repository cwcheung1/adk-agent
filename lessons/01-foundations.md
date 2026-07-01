# 1. Foundations — agent, Runner, event loop

## Concept

An ADK agent is a plain Python object (`LlmAgent`) describing *what* the agent
is (name, model, instructions, tools). A separate object, the `Runner`, is
*how you actually talk to it* — it drives the conversation and hands you back
a stream of events as things happen.

## Analogy

If you know LangGraph: `LlmAgent` is the node definition, `Runner` is
`graph.invoke`/`.stream()`. The split matters for the same reason it matters
there — the agent doesn't know or care how it's being invoked (CLI, web UI,
another agent calling it over A2A); the Runner is the thing that's different
per calling context.

If you don't: think of `LlmAgent` as a job description, and `Runner` as HR
actually assigning the work and reporting back progress. You never call the
agent directly — you always go through the Runner.

## How it works

1. `adk_agent/agent.py` exports one required name: `root_agent`. That's the
   entire contract — `adk run`, `adk web`, and our own CLI all just import the
   package and look for that name.
2. To actually run it (see `adk_agent/cli.py`), you need three things: a
   `SessionService` (here, `InMemorySessionService` — holds conversation
   state), a `Runner` (wraps the agent + session service together), and a
   message (`types.Content(role="user", parts=[types.Part(text=question)])`).
3. `runner.run_async(...)` doesn't return an answer — it yields a **stream of
   events**: tool calls, partial output, intermediate steps, and eventually
   one event where `event.is_final_response()` is `True`. That's the one with
   the actual answer. This event-stream shape is why later stages (MCP tool
   calls, A2A delegation) all show up as visible, inspectable steps instead of
   a black box.
4. The model is pluggable: `LiteLlm(model="anthropic/claude-haiku-4-5-...")`.
   ADK natively speaks Gemini as a bare model string; anything else (Claude,
   OpenAI, ...) goes through the `LiteLlm(...)` wrapper, which reads the
   provider's usual API key env var (`ANTHROPIC_API_KEY` here).

## Look at

1. `adk_agent/agent.py` — `root_agent = LlmAgent(...)`, the whole contract.
2. `adk_agent/cli.py` — the `ask()` function is the entire programmatic
   pattern: build a Runner, send a message, loop until `is_final_response()`.
3. `adk_agent/config.py` — credential loading (shell env > local `.env` >
   central store), called from `__init__.py` *before* `agent.py` reads any
   env var — ordering matters here, it's a common gotcha.

## Run this

```bash
make ask Q="what is 12 * 7?"
```

You should get a direct answer, no tool call — this is the simplest possible
path, useful as a sanity check before anything else in these lessons.

```bash
make web
```

Open the dev UI, pick `adk_agent`, ask something, then click into the
**Events** panel for that turn. Even with nothing but a plain LLM call, you'll
see the event-stream shape: request → response, both visible as discrete
steps. This is the same panel every later lesson uses to *watch* what's
happening instead of just trusting the output.

## You'll know it clicked when

You can explain why `cli.py` loops over events looking for
`is_final_response()` instead of just calling something like
`agent.ask(question)` directly.
