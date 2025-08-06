from typing import Any

from .repository import create_repository


def cmd_init(args: Any) -> None:
    """Initialize a new repository."""
    create_repository(args.path)
