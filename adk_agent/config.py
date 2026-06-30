"""Credential loading.

Precedence (highest wins):
    1. real shell environment variables
    2. project-local ``.env``
    3. central store ``~/.config/secrets/secrets.env`` (shared across projects)

``load_dotenv`` never overrides a variable that is already set, so loading the
lower-priority sources *after* the higher-priority ones leaves the winners in
place.
"""

from pathlib import Path

from dotenv import load_dotenv

CENTRAL_SECRETS = Path.home() / ".config" / "secrets" / "secrets.env"


def load_secrets() -> None:
    """Populate os.environ from local then central dotenv files (idempotent)."""
    # Project-local overrides the shared store, but never the real shell env.
    load_dotenv(".env", override=False)
    if CENTRAL_SECRETS.is_file():
        load_dotenv(CENTRAL_SECRETS, override=False)
