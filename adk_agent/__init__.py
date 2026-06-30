"""adk_agent — a minimal Google ADK agent package.

ADK discovers agents by importing this package and looking for ``root_agent``
inside the ``agent`` module. We load credentials *before* importing ``agent``
so the model wrapper sees ANTHROPIC_API_KEY / ADK_MODEL at import time.
"""

from .config import load_secrets

load_secrets()

from . import agent  # noqa: E402  (must come after load_secrets)

__all__ = ["agent"]
