"""Langfuse tracing for the agent, via OpenInference's ADK instrumentation.

Every model completion and tool call ADK runs becomes an OpenTelemetry span and
is forwarded to Langfuse. This is a no-op when Langfuse keys are absent, so the
agent still runs fine without them. Idempotent — safe to call more than once.
"""

import atexit
import os

_initialized = False


def setup_observability() -> bool:
    """Instrument ADK -> Langfuse if credentials are present. Returns True if on."""
    global _initialized
    if _initialized:
        return True

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return False

    # The Langfuse SDK reads LANGFUSE_HOST; accept LANGFUSE_BASE_URL as an alias.
    if not os.getenv("LANGFUSE_HOST") and os.getenv("LANGFUSE_BASE_URL"):
        os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

    try:
        from langfuse import get_client
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    except ImportError:
        return False

    client = get_client()
    GoogleADKInstrumentor().instrument()
    # Short-lived CLI runs exit before spans flush in the background, so force it.
    atexit.register(client.flush)

    _initialized = True
    return True
