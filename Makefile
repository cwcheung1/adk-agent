# adk-agent — common tasks. Run `make` or `make help` to see everything.

IMAGE        ?= adk-agent
TAG          ?= latest
SECRETS_FILE ?= $(HOME)/.config/secrets/secrets.env
HOST         ?= 0.0.0.0
PORT         ?= 18000
A2A_PORT     ?= 18001
MCP_HTTP_PORT ?= 18002
Q            ?=

.DEFAULT_GOAL := help

## help: show this help
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed -e 's/## //' | awk -F': ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## install: create the venv and install deps (uv)
install:
	uv sync

## ask: one-shot question, e.g. make ask Q="what is an LLM agent?"
ask:
	@uv run adk-agent $(Q)

## chat: start an interactive REPL session
chat:
	uv run adk-agent

## web: launch the ADK dev web UI on HOST:PORT (0.0.0.0:18000 — reachable from Windows under WSL)
web:
	uv run adk web --host $(HOST) --port $(PORT)

## docker-build: build the container image
docker-build:
	docker build -t $(IMAGE):$(TAG) .

## docker-run: run a one-shot question in the container, e.g. make docker-run Q="hello"
docker-run:
	docker run --rm --env-file $(SECRETS_FILE) $(IMAGE):$(TAG) $(Q)

## docker-chat: interactive REPL inside the container
docker-chat:
	docker run --rm -it --env-file $(SECRETS_FILE) $(IMAGE):$(TAG)

## a2a-serve: expose the agent over A2A (card at /.well-known/agent-card.json). Override port with A2A_PORT=
a2a-serve:
	A2A_PORT=$(A2A_PORT) uv run uvicorn adk_agent.a2a_server:a2a_app --host $(HOST) --port $(A2A_PORT)

## a2a-card: fetch the served agent card (a2a-serve must be running)
a2a-card:
	@curl -s http://localhost:$(A2A_PORT)/.well-known/agent-card.json | uv run python -m json.tool

## mcp-serve: run mcp_server.py standalone over streamable-http (not stdio). Override port with MCP_HTTP_PORT=
mcp-serve:
	MCP_TRANSPORT=streamable-http MCP_HTTP_HOST=$(HOST) MCP_HTTP_PORT=$(MCP_HTTP_PORT) uv run python adk_agent/mcp_server.py

## mcp-http-check: initialize + list_tools + call current_time against the running mcp-serve
mcp-http-check:
	@MCP_HTTP_PORT=$(MCP_HTTP_PORT) uv run python adk_agent/mcp_http_check.py

## langfuse-check: verify Langfuse credentials + connectivity
langfuse-check:
	@uv run python -c "from adk_agent.config import load_secrets; load_secrets(); from langfuse import get_client; print('Langfuse auth_check:', get_client().auth_check())"

## secrets-check: verify the credential store has an Anthropic key
secrets-check:
	@grep -q '^ANTHROPIC_API_KEY=.\+' $(SECRETS_FILE) \
		&& echo "ANTHROPIC_API_KEY: present in $(SECRETS_FILE)" \
		|| echo "ANTHROPIC_API_KEY: MISSING — add it to $(SECRETS_FILE)"

## clean: remove build artifacts and caches
clean:
	rm -rf .venv dist build *.egg-info **/__pycache__ .ruff_cache .pytest_cache

.PHONY: help install ask chat web a2a-serve a2a-card mcp-serve mcp-http-check langfuse-check docker-build docker-run docker-chat secrets-check clean
