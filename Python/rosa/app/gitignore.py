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


def gitignore_parse(lines: List[str]) -> List [Tuple[str, bool]]:
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
    repo_exclude_fiel = repo.gitdir / "info" / "exclude"
    if repo_exclude_fiel.exists():
        with repo_exclude_fiel.open("r") as f:
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

    return ret


def check_ignore1(rules: List[Tuple[str, bool]], path: str) -> Optional[bool]:
    """Check path against a single ruleset"""
    result = None
    for pattern, value in rules:
        if fnmatch(path, pattern):
            result = value
    return result


def check_ignore_scoped(rules: Dict[str, List[Tuple[str, bool]]], path: str) -> Optional[bool]:
    """Check path against scoped rules"""
    parent = str(Path(path).parent) if Path(path).parent != Path(".") else ""

    while True:
        if parent in rules:
            result = check_ignore1(rules[parent], path)
            if result is not None:
                return result
        if parent == "":
            break
        parent = str(Path(parent).parent) if Path(parent).parent != Path(".") else ""

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

    result = check_ignore_scoped(rules.scoped, path)
    if result is not None:
        return result

    return check_ignore_absolute(rules.absolute, path)
