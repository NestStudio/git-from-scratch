"""MyGit CLI entry point."""


import argparse
import sys
from typing import Sequence

from .commands import (
    cmd_add,
    cmd_cat_file,
    cmd_check_ignore,
    cmd_checkout,
    cmd_commit,
    cmd_hash_object,
    cmd_init,
    cmd_log,
    cmd_ls_files,
    cmd_ls_tree,
    cmd_rev_parse,
    cmd_rm,
    cmd_show_ref,
    cmd_status,
    cmd_tag,
)


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command line argument parser"""
    parser = argparse.ArgumentParser(description="A Git implementation for learning")
    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new repository")
    init_parser.add_argument(
        "path",
        metavar="directory",
        nargs="?",
        default=".",
        help="Where to create the repository",
    )

    # cat-file command
    cat_file_parser = subparsers.add_parser(
        "cat-file", help="Provide content of repository objects"
    )
    cat_file_parser.add_argument(
        "type",
        metavar="type",
        choices=["blob", "commit", "tag", "tree"],
        help="Specify the type",
    )
    cat_file_parser.add_argument(
        "object", metavar="object", help="The object to display"
    )

    # hash-object command
    hash_object_parser = subparsers.add_parser(
        "hash-object", help="Compute object ID and optionally create a blob from a file"
    )
    hash_object_parser.add_argument(
        "-t",
        metavar="type",
        dest="type",
        choices=["blob", "commit", "tag", "tree"],
        default="blob",
        help="Specify the type",
    )
    hash_object_parser.add_argument(
        "-w",
        dest="write",
        action="store_true",
        help="Actually write the object into the database",
    )
    hash_object_parser.add_argument("path", help="Read object from <file>")

    # log command
    log_parser = subparsers.add_parser("log", help="Display history of a given commit")
    log_parser.add_argument(
        "commit", default="HEAD", nargs="?", help="Commit to start at"
    )

    # ls-tree command
    ls_tree_parser = subparsers.add_parser("ls-tree", help="Pretty-print a tree object")
    ls_tree_parser.add_argument(
        "-r",
        dest="recursive",
        action="store_true",
        help="Recurse into sub-trees",
    )
    ls_tree_parser.add_argument("tree", help="A tree-ish object")

    # checkout command
    checkout_parser = subparsers.add_parser(
        "checkout", help="Checkout a commit inside of a directory"
    )
    checkout_parser.add_argument("commit", help="The commit or tree to checkout")
    checkout_parser.add_argument("path", help="The EMPTY directory to checkout on")

    # show-ref command
    subparsers.add_parser("show-ref", help="List references")

    # tag command
    tag_parser = subparsers.add_parser("tag", help="List and create tags")
    tag_parser.add_argument(
        "-a",
        action="store_true",
        dest="create_tag_object",
        help="Whether to create a tag object",
    )
    tag_parser.add_argument("name", nargs="?", help="The new tag's name")
    tag_parser.add_argument(
        "object", default="HEAD", nargs="?", help="The object the new tag will point to"
    )

    # rev-parse command
    rev_parse_parser = subparsers.add_parser(
        "rev-parse", help="Parse revision (or other objects) identifiers"
    )
    rev_parse_parser.add_argument(
        "--mygit-type",
        metavar="type",
        dest="type",
        choices=["blob", "commit", "tag", "tree"],
        default=None,
        help="Specify the expected type",
    )
    rev_parse_parser.add_argument("name", help="The name to parse")

    # ls-files command
    ls_files_parser = subparsers.add_parser("ls-files", help="List all the stage files")
    ls_files_parser.add_argument(
        "--verbose", action="store_true", help="Show everything"
    )

    # check-ignore command
    check_ignore_parser = subparsers.add_parser(
        "check-ignore", help="Check path(s) against ignore rules"
    )
    check_ignore_parser.add_argument("path", nargs="+", help="Paths to check")

    # status command
    subparsers.add_parser("status", help="Show the working tree status")

    # rm command
    rm_parser = subparsers.add_parser(
        "rm", help="Remove files from the working tree and the index"
    )
    rm_parser.add_argument("path", nargs="+", help="Files to remove")

    # add command
    add_parser = subparsers.add_parser("add", help="Add files contents to the index")
    add_parser.add_argument("path", nargs="+", help="Files to add")

    # commit command
    commit_parser = subparsers.add_parser("commit", help="Record changes to the repository")
    commit_parser.add_argument(
        "-m",
        metavar="message",
        dest="message",
        help="Message to associate with this commit",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point"""
    if argv is None:
        argv = sys.argv[1:]

    parser = setup_parser()
    args = parser.parse_args(argv)

    try:
        match args.command:
            case "add":
                cmd_add(args)
            case "cat-file":
                cmd_cat_file(args)
            case "check-ignore":
                cmd_check_ignore(args)
            case "checkout":
                cmd_checkout(args)
            case "commit":
                cmd_commit(args)
            case "hash-object":
                cmd_hash_object(args)
            case "init":
                cmd_init(args)
            case "log":
                cmd_log(args)
            case "ls-files":
                cmd_ls_files(args)
            case "ls-tree":
                cmd_ls_tree(args)
            case "rev-parse":
                cmd_rev_parse(args)
            case "rm":
                cmd_rm(args)
            case "show-ref":
                cmd_show_ref(args)
            case "status":
                cmd_status(args)
            case "tag":
                cmd_tag(args)
            case _:
                print("Bad command.", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
