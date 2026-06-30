# adk-agent — common tasks. Run `make` or `make help` to see everything.

IMAGE        ?= adk-agent
TAG          ?= latest
SECRETS_FILE ?= $(HOME)/.config/secrets/secrets.env
PORT         ?= 18000
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

## web: launch the ADK dev web UI on PORT (default 18000)
web:
	uv run adk web --port $(PORT)

## docker-build: build the container image
docker-build:
	docker build -t $(IMAGE):$(TAG) .

## docker-run: run a one-shot question in the container, e.g. make docker-run Q="hello"
docker-run:
	docker run --rm --env-file $(SECRETS_FILE) $(IMAGE):$(TAG) $(Q)

## docker-chat: interactive REPL inside the container
docker-chat:
	docker run --rm -it --env-file $(SECRETS_FILE) $(IMAGE):$(TAG)

## secrets-check: verify the credential store has an Anthropic key
secrets-check:
	@grep -q '^ANTHROPIC_API_KEY=.\+' $(SECRETS_FILE) \
		&& echo "ANTHROPIC_API_KEY: present in $(SECRETS_FILE)" \
		|| echo "ANTHROPIC_API_KEY: MISSING — add it to $(SECRETS_FILE)"

## clean: remove build artifacts and caches
clean:
	rm -rf .venv dist build *.egg-info **/__pycache__ .ruff_cache .pytest_cache

.PHONY: help install ask chat web docker-build docker-run docker-chat secrets-check clean
