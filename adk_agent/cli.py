"""A minimal command-line interface around the ADK agent.

This is the *programmatic* way to drive an agent (as opposed to ``adk run`` /
``adk web``): we build a Runner with an in-memory session service, hand it a
user message, and stream the resulting events until the final response.

Usage:
    adk-agent "your question here"      # one-shot
    adk-agent                            # interactive REPL
"""

import argparse
import asyncio
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import MODEL, root_agent

APP_NAME = "adk_agent"
USER_ID = "local_user"


async def ask(question: str) -> str:
    """Run one question through the agent and return the final text response."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    message = types.Content(role="user", parts=[types.Part(text=question)])

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        # The final response carries the model's answer; earlier events are
        # intermediate (tool calls, partial streaming, etc.).
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text for part in event.content.parts if part.text)
    return final_text


def _check_credentials() -> None:
    """Fail early with a friendly message if the model can't authenticate."""
    if MODEL.startswith("anthropic/") and not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Add it to the central credential store:\n"
            "    echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.config/secrets/secrets.env\n"
            "(or export it in your shell, or put it in a local .env)."
        )


async def _repl() -> None:
    print(f"adk-agent ({MODEL}) — type a question, or 'exit' to quit.")
    while True:
        try:
            question = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if question.lower() in {"exit", "quit", ""}:
            return
        answer = await ask(question)
        print(f"\nagent> {answer}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="adk-agent",
        description="Ask a question to a minimal Google ADK agent.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="The question to ask. Omit to start an interactive session.",
    )
    args = parser.parse_args()

    _check_credentials()

    if args.question:
        question = " ".join(args.question)
        print(asyncio.run(ask(question)))
    else:
        asyncio.run(_repl())


if __name__ == "__main__":
    main()
