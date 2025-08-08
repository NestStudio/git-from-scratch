"""Git reference management"""

from pathlib import Path
from typing import Dict, Optional, Union

from .repository import GitRepository


def ref_resolve(repo: GitRepository, ref: str) -> Optional[str]:
    """Resolve a reference to a SHA"""
    path = repo.file_path(ref)

    # Sometimes, an indirect reference may be broken. This is normal
    # in one specific case: we're looking for HEAD on a new repository
    # with no commits.
    if not path or not path.is_file():
        return None

    with path.open("r") as fp:
        data = fp.read().strip()

    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data


def ref_list(
        repo: GitRepository, path: Optional[Path] = None
        ) -> Dict[str, Union[str, Dict]]:
    """List all references in the repository"""
    if not path:
        refs_dir = repo.dir_path("refs")
        if not refs_dir:
            return {}
        path = refs_dir

    ret = {}
    # Git shows refs sorted
    try:
        for f in sorted(path.iterdir()):
            if f.is_dir():
                ret[f.name] = ref_list(repo, f)
            else:
                resolved = ref_resolve(repo, str(f.relative_to(repo.gitdir)))
                if resolved:
                    ret[f.name] = resolved
    except (OSError, PermissionError):
        pass

    return ret


def ref_create(repo: GitRepository, ref_name: str, sha: str) -> None:
    """Create a reference"""
    ref_path = repo.file_path("refs", ref_name)
    if ref_path:
        # Ensure parent directories exist
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(sha + "\n")


def show_ref(
    repo: GitRepository,
    refs: Dict[str, Union[str, Dict]],
    with_hash: bool = True,
    prefix: str = "",
) -> None:
    """Show references recursively"""
    if prefix:
        prefix = prefix + "/"

    for k, v in refs.items():
        if isinstance(v, str) and with_hash:
            print(f"{v} {prefix}{k}")
        elif isinstance(v, str):
            print(f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash, prefix=f"{prefix}{k}")
