# adk-agent

A barebones [Google ADK](https://adk.dev) agent — the smallest useful shape:
one LLM-backed agent with a system prompt, driven by a CLI, and packaged to run
in Docker. Powered by **Anthropic Claude** through ADK's LiteLLM connector.

This is **Stage 1–2** of a learning project that grows in complexity. See
[NOTES.md](./NOTES.md) for the ADK ↔ LangGraph mental model and the roadmap.

## Layout

```
adk-agent/
├── adk_agent/
│   ├── __init__.py   # loads secrets, then exposes the agent package
│   ├── config.py     # central + local credential loading
│   ├── agent.py      # root_agent = LlmAgent(...)  ← the only required ADK export
│   └── cli.py        # programmatic Runner loop (one-shot + REPL)
├── pyproject.toml    # uv-managed; defines the `adk-agent` console script
├── Dockerfile        # slim image; secrets passed at runtime, never baked in
├── Makefile          # all common tasks
└── .env.example      # optional local overrides
```

## Credentials

The agent reads its API key from a **central, cross-project store**:

```
~/.config/secrets/secrets.env      # chmod 600, never committed
```

Add your key once and every project can use it:

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.config/secrets/secrets.env
make secrets-check        # confirm it's there
```

Precedence: real shell env > project-local `.env` > central store.

## Run it (local)

```bash
make install                       # uv sync
make ask Q="what is an LLM agent?" # one-shot
make chat                          # interactive REPL
make web                           # ADK dev web UI
```

Or without make:

```bash
uv run adk-agent "what is an LLM agent?"
```

## Run it (Docker)

```bash
make docker-build
make docker-run Q="explain Google ADK in one sentence"
make docker-chat                   # interactive, inside the container
```

The image contains no secrets; `make docker-run` injects them with
`--env-file ~/.config/secrets/secrets.env`.

## Switching models

The model is set by the `ADK_MODEL` env var (default
`anthropic/claude-haiku-4-5-20251001`). To use Gemini instead, set
`ADK_MODEL=gemini-2.0-flash` and provide a `GOOGLE_API_KEY` — note Gemini takes
a bare model string, so you'd also drop the `LiteLlm(...)` wrapper in
`agent.py`. See NOTES.md.
