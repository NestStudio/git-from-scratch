"""Git repository management."""

import configparser
from pathlib import Path
from typing import Optional


class GitRepository:
    """A class to manage a Git repository."""

    def __init__(self, path: str | Path, force: bool = False) -> None:
        """Initialize a git repository

        Args:
            path:Path to the repository
            force: skip validation checks if True
        """
        self.worktree = Path(path).resolve()
        self.gitdir = self.worktree / ".git"
        self.conf: Optional[configparser.ConfigParser] = None

        if not force and not self.gitdir.is_dir():
            raise RuntimeError(f"Not a git repository: {path}")

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        config_file = self.file_path("config")

        if config_file and config_file.exist():
            self.conf.read([str(config_file)])
        elif not force:
            raise RuntimeError("Configuration file missing")

        if not force:
            try:
                version = int(self.conf.get("core", "repositoryformatversion"))
                if version != 0:
                    raise RuntimeError(
                        f"Unsupported repositoryformatversion: {version}"
                        )
            except (configparser.NoSectionError,
                    configparser.NoOptionError,
                    ValueError) as e:
                raise RuntimeError(f"Invalid configuration: {e}") from e

    def path(self, *path_parts: str) -> Path:
        """Compute path under repo's gitdir"""
        return self. gitdir.joinpath(*path_parts)

    def file_path(self, *path_parts: str,
                  mkdir: bool = False) -> Optional[Path]:
        """Same as path, but create parent directories if absent

        Args:
            path_parts: Path components
            mkdir: Create parent directories if True

        REturns:
            Path if successful, None if mkdir is False and parent doesn't exist
        """
        if self.dir_path(*path_parts[:-1], mkdir=mkdir):
            return self.path(*path_parts)

        return None

    def dir_path(self, *path_parts: str,
                 mkdir: bool = False) -> Optional[Path]:
        """Same as path, but mkdir path if absent if mkdir is True.

        Args:
            path_parts: Path components
            mkdir: Create directory if True

        Returns:
            Path if successful, None if mkdir is False and path doesn't exist
        """
        path = self.path(*path_parts)

        if path.exists():
            if path.is_dir():
                return path
            else:
                raise RuntimeError(f"Not a directory {path}")

        if mkdir:
            path.mkdir(parents=True, exist_ok=True)
            return path

        return None


def create_repository(path: str | Path) -> GitRepository:
    """Create a new repository at path."""
    repo = GitRepository(path, force=True)

    # First we have to make sure the path either
    # doens't exist or is an empty dir
    if repo.worktree.exists():
        if not repo.worktree.is_dir():
            raise RuntimeError(f"{path} is not a directory")
        if repo.gitdir.exists() and any(repo.gitdir.iterdir()):
            raise RuntimeError(f"{path} is not empty")
    else:
        repo.worktree.mkdir(parents=True, exist_ok=True)

    # Create necessary directories
    assert repo.dir_path("objects", mkdir=True)
    assert repo.dir_path("refs", "tags", mkdir=True)
    assert repo.dir_path("refs", "heads", mkdir=True)

    # .git/description
    description_file = repo.file_path("description")
    if description_file:
        description_file.write_text(
            "Unnamed repository; edit this file 'description'"
            "to name the repository.\n"
        )

    # .git/HEAD
    head_file = repo.file_path("HEAD")
    if head_file:
        head_file.write_text("ref: refs/heads/master\n")

    # .git/config
    config_file = repo.file_path("config")
    if config_file:
        config = default_config()
        with config_file.open("w") as f:
            config.write(f)

    return repo


def default_config() -> configparser.ConfigParser:
    """Create default Git configuration."""
    config = configparser.ConfigParser()

    config.add_section("core")
    config.set("core", "repositoryformatversion", "0")
    config.set("core", "filemode", "false")
    config.set("core", "bare", "false")

    return config


def find_repository(path: str | Path = ".",
                    required: bool = True) -> Optional[GitRepository]:
    """Find a Git repository by walking up the directory tree

    Args:
        path: Starting path
        required: Raise exception if repository not found

    Returns:
        GitRepository if found, None if not found and not required
    """
    path = Path(path).resolve()

    if (path / ".git").is_dir():
        return GitRepository(path)

    parent = path.parent

    if parent == path:
        # We have reached the root
        if required:
            raise RuntimeError("No git directory")
        else:
            return None

    # Recursive case
    return find_repository(parent, required)
