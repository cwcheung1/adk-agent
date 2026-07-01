"""Chapter 4, Stage 6: state scoping + persistence across separate sessions,
not just separate turns within one session.

Every agent so far used `output_key` to write **unprefixed** state keys —
those live in the `sessions` table, scoped to one session_id. Start a new
session (a genuinely separate conversation) and they're gone. `State` defines
three prefixes (`google.adk.sessions.state.State`: `APP_PREFIX = "app:"`,
`USER_PREFIX = "user:"`, `TEMP_PREFIX = "temp:"`) that change *where* a key is
stored, confirmed by reading `SqliteSessionService._merge_state`: on session
load, `app_state` (one row per app) and `user_state` (one row per app+user_id)
get merged into the session dict ahead of `session_state` (one row per
session_id) — so a `user:`-prefixed key set in session A is visible in a
brand-new session B, as long as it's the same user_id. Plain keys are not.

Also the first place this repo uses a *persistent* SessionService instead of
`InMemorySessionService` — except we've actually been using one all along
without knowing it: `adk run`'s default local storage IS
`SqliteSessionService` at `.adk/session.db` (see
`google.adk.cli.utils.local_storage.create_local_database_session_service`).
`adk run` also always uses the same fixed `user_id = 'test_user'`
(`google.adk.cli.cli`) across separate invocations, which is exactly what
makes the demo below work with plain `adk run`/`make persist-ask` calls — no
custom Runner/SessionService wiring needed for this one, unlike every
previous stage.

`{user:name?}` in the instruction — the `?` suffix is required for a key that
might not exist yet (first-ever conversation): without it, a missing key
raises `KeyError` instead of substituting empty string (see
`google.adk.utils.instructions_utils.inject_session_state`).
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

from adk_agent.config import load_secrets

load_secrets()

MODEL = os.getenv("ADK_MODEL", "anthropic/claude-haiku-4-5-20251001")


def remember_name(name: str, tool_context: ToolContext) -> str:
    """Permanently remember the user's name, across all future conversations
    (not just this one). Call this as soon as the user tells you their name.
    """
    tool_context.state["user:name"] = name
    return f"Saved — I'll remember your name is {name} in future conversations too."


root_agent = LlmAgent(
    name="persistent_agent",
    model=LiteLlm(model=MODEL),
    description="A personal assistant whose memory of your name survives across separate conversations.",
    instruction=(
        "You are a personal assistant. "
        "What you already remember about this user, persisted from past "
        "conversations: name={user:name?} (empty means you don't know it yet). "
        "If you already know their name, greet them by it warmly and do not "
        "ask again. If you don't know it, ask for it, and as soon as they "
        "tell you, call `remember_name` to save it permanently, then greet "
        "them using it."
    ),
    tools=[remember_name],
)
