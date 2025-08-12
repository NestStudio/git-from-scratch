"""Git ignore functionality"""

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .index import index_read
from .objects import object_read
from .repository import GitRepository


def gitignore_parse1(raw: str) -> Optional[Tuple[str, bool]]:
    """Parse a single gitignore line"""
    raw = raw.strip()  # Remove leading/trailing spaces

    if not raw or raw[0] == "#":
        return None
    elif raw[0] == "!":
        return (raw[1:], False)
    elif raw[0] == "\\":
        return (raw[1:], True)
    else:
        return (raw, True)


def gitignore_parse(lines: List[str]) -> List[Tuple[str, bool]]:
    """Parse gitignore rules from lines"""
    ret = []

    for line in lines:
        parsed = gitignore_parse1(line)
        if parsed:
            ret.append(parsed)

    return ret


class GitIgnore:
    """Git ignore rules container"""

    def __init__(
            self,
            absolute: Optional[List[List[Tuple[str, bool]]]] = None,
            scoped: Optional[Dict[str, List[Tuple[str, bool]]]] = None
            ):
        self.absolute = absolute or []
        self.scoped = scoped or {}


def gitignore_read(repo: GitRepository) -> GitIgnore:
    """Read gitignore rules from repository"""
    ret = GitIgnore()

    # Read local configuration in .git/info/exclude
    repo_exclude_file = repo.gitdir / "info" / "exclude"
    if repo_exclude_file.exists():
        with repo_exclude_file.open("r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))

    # Global configuration
    config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    global_file = Path(config_home) / "git" / "ignore"

    if global_file.exists():
        with global_file.open("r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))

    # .gitignore files in the index
    index = index_read(repo)

    for entry in index.entries:
        if entry.name == ".gitignore" or entry.name.endswith("/.gitignore"):
            dir_name = str(Path(entry.name).parent) if Path(entry.name).parent != Path(".") else ""
            contents = object_read(repo, entry.sha)
            if contents and hasattr(contents, 'blobdata'):
                lines = contents.blobdata.decode("utf8").splitlines()
                ret.scoped[dir_name] = gitignore_parse(lines)

    # Also read .gitignore files from the working tree
    for root, dirs, files in os.walk(repo.worktree):
        # Skip .git directory
        if str(Path(root)).startswith(str(repo.gitdir)):
            continue

        if ".gitignore" in files:
            gitignore_path = Path(root) / ".gitignore"
            try:
                with gitignore_path.open("r") as f:
                    lines = f.readlines()
                    rel_root = Path(root).relative_to(repo.worktree)
                    dir_name = str(rel_root) if rel_root != Path(".") else ""
                    ret.scoped[dir_name] = gitignore_parse(lines)
            except (IOError, UnicodeDecodeError):
                # Skip unreadable .gitignore files
                continue

    return ret


def check_ignore1(rules: List[Tuple[str, bool]], path: str) -> Optional[bool]:
    """Check path against a single ruleset"""
    result = None
    for pattern, value in rules:
        # Convert gitignore patterns to fnmatch patterns
        if pattern.endswith('/'):
            # Directory-only pattern
            pattern = pattern.rstrip('/')
            if fnmatch(path, pattern) or fnmatch(path, pattern + "/*") or ("/" + pattern + "/") in ("/" + path + "/"):
                result = value
        elif '/' in pattern:
            # Pattern with path separators - match against full path
            if fnmatch(path, pattern) or path.endswith("/" + pattern):
                result = value
        else:
            # Simple pattern - match against filename or any component
            if fnmatch(Path(path).name, pattern) or fnmatch(path, pattern) or fnmatch(path, "*/" + pattern):
                result = value
            # Also check if any path component matches
            parts = Path(path).parts
            for part in parts:
                if fnmatch(part, pattern):
                    result = value
                    break
    return result


def check_ignore_scoped(rules: Dict[str, List[Tuple[str, bool]]], path: str) -> Optional[bool]:
    """Check path against scoped rules"""
    path_obj = Path(path)


    current_dir = str(path_obj.parent) if path_obj.parent != Path(".") else ""

    while True:
        if current_dir in rules:
            # For scoped rules, make path relative to the directory containing .gitignore
            if current_dir == "":
                rel_path = path
            else:
                rel_path = str(Path(path).relative_to(current_dir)) if Path(path).is_relative_to(Path(current_dir)) else path

            result = check_ignore1(rules[current_dir], rel_path)
            if result is not None:
                return result

        if current_dir == "":
            break

        parent = Path(current_dir).parent
        current_dir = str(parent) if parent != Path(".") else ""

    return None


def check_ignore_absolute(rules: List[List[Tuple[str, bool]]], path: str) -> bool:
    """Check path against absolute rules"""
    for ruleset in rules:
        result = check_ignore1(ruleset, path)
        if result is not None:
            return result
    return False


def check_ignore(rules: GitIgnore, path: str) -> bool:
    """Check if path should be ignored"""
    if Path(path).is_absolute():
        raise RuntimeError("This function requires path to be relative to the repository's root")

    # First check scoped rules
    result = check_ignore_scoped(rules.scoped, path)
    if result is not None:
        return result

    # Then check absolute rules
    return check_ignore_absolute(rules.absolute, path)