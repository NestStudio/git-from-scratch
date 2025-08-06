"""MyGit CLI entry point."""

import argparse
import sys
from typing import Sequence

from .commands import cmd_init


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command line argument parser"""

    parser = argparse.ArgumentParser(
        description="A Git implementation for learning"
        )
    subparsers = parser.add_subparsers(
        title="command", dest="command", required=True
        )

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new repository"
        )
    init_parser.add_argument(
        "path",
        metavar="directory",
        nargs="?",
        default=".",
        help="Where to create the repository",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = setup_parser()
    args = parser.parse_args(argv)

    try:
        match args.command:
            case "init":
                cmd_init(args)
            case _:
                print("Bad command.", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
