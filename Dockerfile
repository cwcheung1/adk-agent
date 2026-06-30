# Barebones image for the ADK agent CLI.
# Secrets are NEVER baked in — pass them at runtime with --env-file (see Makefile).
FROM python:3.12-slim

# Bring in uv (fast, reproducible installs) from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install dependencies + the package itself into the system environment.
COPY pyproject.toml README.md ./
COPY adk_agent ./adk_agent
RUN uv pip install --system --no-cache .

# `adk-agent` is the console script defined in pyproject.toml [project.scripts].
ENTRYPOINT ["adk-agent"]
