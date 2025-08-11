"""mygit command implementations"""

import grp
import os
import pwd
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Set

from .config import gitconfig_read, gitconfig_user_get
from .gitignore import check_ignore, gitignore_read
from .index import GitIndexEntry, index_read, index_write, tree_from_index
from .objects import (
    GitCommit,
    GitTag,
    object_find,
    object_hash,
    object_read,
    object_write,
)
from .refs import ref_create, ref_list, ref_resolve, show_ref
from .repository import GitRepository, create_repository, find_repository


def cmd_init(args: Any) -> None:
    """Set up a brand new git repository in the specified directory"""
    create_repository(args.path)


def cmd_cat_file(args: Any) -> None:
    """Show the raw content of any git object - blobs, trees, commits, etc."""
    repo = find_repository()
    cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo: GitRepository, obj: str, fmt: bytes | None = None) -> None:
    """Actually dump the object data to stdout so you can see what's inside"""
    obj_data = object_read(repo, object_find(repo, obj, fmt=fmt))
    if obj_data:
        sys.stdout.buffer.write(obj_data.serialize())


def cmd_hash_object(args: Any) -> None:
    """Take a file and calculate what its SHA-1 hash would be in git"""
    # Only get the repo if we're actually writing the object
    repo = find_repository() if args.write else None

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def cmd_log(args: Any) -> None:
    """Generate a visual graph of the commit history using graphviz format"""
    repo = find_repository()

    print("digraph mygitlog{")
    print("  node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")


def log_graphviz(repo: GitRepository, sha: str, seen: Set[str]) -> None:
    """Recursively walk through commits and build the graphviz representation"""
    # Avoid infinite loops by tracking what we've already processed
    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    if not commit or not hasattr(commit, 'kvlm'):
        return

    # Clean up the commit message for display
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace('"', '\\"')

    # Just show the first line if it's a multi-line message
    if "\n" in message:
        message = message[: message.index("\n")]

    print(f'  c_{sha} [label="{sha[0:7]}: {message}"]')

    # If this is the root commit, we're done
    if b"parent" not in commit.kvlm:
        return

    # Handle both single parents and merge commits with multiple parents
    parents = commit.kvlm[b"parent"]
    if not isinstance(parents, list):
        parents = [parents]

    # Draw arrows to parent commits and recursively process them
    for p in parents:
        p_str = p.decode("ascii")
        print(f"  c_{sha} -> c_{p_str};")
        log_graphviz(repo, p_str, seen)


def cmd_ls_tree(args: Any) -> None:
    """List everything inside a tree object, like doing 'ls' on a directory"""
    repo = find_repository()
    ls_tree(repo, args.tree, args.recursive)


def ls_tree(repo: GitRepository, ref: str, recursive: bool = False, prefix: str = "") -> None:
    """Walk through a tree and show all the files and subdirectories"""
    sha = object_find(repo, ref, fmt=b"tree")
    obj = object_read(repo, sha)
    if not obj or not hasattr(obj, 'items'):
        return

    for item in obj.items:
        # Figure out what kind of object this is based on its mode
        if len(item.mode) == 5:
            mode_type = item.mode[0:1]
        else:
            mode_type = item.mode[0:2]

        # Git uses different mode prefixes for different object types
        match mode_type:
            case b"04":
                obj_type = "tree"  # It's a subdirectory
            case b"10":
                obj_type = "blob"  # Regular file
            case b"12":
                obj_type = "blob"  # Symbolic link
            case b"16":
                obj_type = "commit"  # Git submodule reference
            case _:
                raise RuntimeError(f"Weird tree leaf mode {item.mode}")

        if not (recursive and obj_type == "tree"):
            # Format the mode properly with leading zeros
            mode_str = "0" * (6 - len(item.mode)) + item.mode.decode("ascii")
            path = os.path.join(prefix, item.path)
            print(f"{mode_str} {obj_type} {item.sha}\t{path}")
        else:
            # It's a subdirectory and we want to go deeper
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))


def cmd_checkout(args: Any) -> None:
    """Extract all the files from a commit into a directory"""
    repo = find_repository()
    obj = object_read(repo, object_find(repo, args.commit))
    if not obj:
        raise RuntimeError(f"Object not found: {args.commit}")

    # If they gave us a commit, we need to get the tree it points to
    if obj.fmt == b"commit":
        tree_sha = obj.kvlm[b"tree"].decode("ascii")
        obj = object_read(repo, tree_sha)

    # Make sure we're not about to overwrite something important
    checkout_path = Path(args.path)
    if checkout_path.exists():
        if not checkout_path.is_dir():
            raise RuntimeError(f"Not a directory {args.path}!")
        if any(checkout_path.iterdir()):
            raise RuntimeError(f"Not empty {args.path}!")
    else:
        checkout_path.mkdir(parents=True, exist_ok=True)

    tree_checkout(repo, obj, checkout_path)


def tree_checkout(repo: GitRepository, tree: Any, path: Path) -> None:
    """Recursively extract all files from a tree object to the filesystem"""
    if not hasattr(tree, 'items'):
        return

    for item in tree.items:
        obj = object_read(repo, item.sha)
        if not obj:
            continue

        dest = path / item.path

        if obj.fmt == b"tree":
            # It's a directory, so create it and recurse
            dest.mkdir(exist_ok=True)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b"blob":
            # It's a file, so write out its contents
            with dest.open("wb") as f:
                f.write(obj.blobdata)


def cmd_show_ref(args: Any) -> None:
    """Show all the branches and tags in the repository"""
    repo = find_repository()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


def cmd_tag(args: Any) -> None:
    """Create a new tag or list existing ones"""
    repo = find_repository()

    if args.name:
        # They want to create a new tag
        tag_create(repo, args.name, args.object, create_tag_object=args.create_tag_object)
    else:
        # Just show all existing tags
        refs = ref_list(repo)
        if "tags" in refs:
            show_ref(repo, {"tags": refs["tags"]}, with_hash=False)


def tag_create(repo: GitRepository, name: str, ref: str, create_tag_object: bool = False) -> None:
    """Actually create a tag, either lightweight or annotated"""
    sha = object_find(repo, ref)

    if create_tag_object:
        # Create an annotated tag with metadata
        tag = GitTag()
        tag.kvlm = {}
        tag.kvlm[b"object"] = sha.encode()
        tag.kvlm[b"type"] = b"commit"
        tag.kvlm[b"tag"] = name.encode()
        tag.kvlm[b"tagger"] = b"Mymygit <mygit@example.com>"
        tag.kvlm[None] = b"A tag generated by mygit!\n"
        tag_sha = object_write(tag, repo)
        # Point the tag reference to the tag object
        ref_create(repo, f"tags/{name}", tag_sha)
    else:
        # Create a lightweight tag (just a reference)
        ref_create(repo, f"tags/{name}", sha)


def cmd_rev_parse(args: Any) -> None:
    """Turn a human-readable reference into a SHA-1 hash"""
    fmt = args.type.encode() if args.type else None
    repo = find_repository()
    print(object_find(repo, args.name, fmt, follow=True))


def cmd_ls_files(args: Any) -> None:
    """Show all the files that are currently staged in the index"""
    repo = find_repository()
    index = index_read(repo)

    if args.verbose:
        print(f"Index file format v{index.version}, containing {len(index.entries)} entries.")

    for e in index.entries:
        print(e.name)
        if args.verbose:
            # Decode the file type from the mode bits
            entry_type = {
                0b1000: "regular file",
                0b1010: "symlink",
                0b1110: "mygit link"
            }[e.mode_type]
            print(f"  {entry_type} with perms: {e.mode_perms:o}")
            print(f"  on blob: {e.sha}")

            # Show timestamps in human-readable format
            ctime_str = datetime.fromtimestamp(e.ctime[0]).strftime("%Y-%m-%d %H:%M:%S")
            mtime_str = datetime.fromtimestamp(e.mtime[0]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  created: {ctime_str}.{e.ctime[1]}, modified: {mtime_str}.{e.mtime[1]}")
            print(f"  device: {e.dev}, inode: {e.ino}")

            # Try to show user/group names instead of just IDs
            try:
                user_name = pwd.getpwuid(e.uid).pw_name
                group_name = grp.getgrgid(e.gid).gr_name
                print(f"  user: {user_name} ({e.uid})  group: {group_name} ({e.gid})")
            except (KeyError, OSError):
                print(f"  user: {e.uid}  group: {e.gid}")
            print(f"  flags: stage={e.flag_stage} assume_valid={e.flag_assume_valid}")


def cmd_check_ignore(args: Any) -> None:
    """Check if certain paths would be ignored by .gitignore rules"""
    repo = find_repository()
    rules = gitignore_read(repo)
    for path in args.path:
        if check_ignore(rules, path):
            print(path)


def cmd_status(args: Any) -> None:
    """Show what's changed - the classic 'git status' command"""
    repo = find_repository()
    index = index_read(repo)

    cmd_status_branch(repo)

    # First check what's different between HEAD and the index (staged changes)
    has_staged_changes = cmd_status_head_index(repo, index)

    # Then check what's different between index and working tree (unstaged changes)
    has_unstaged_changes = cmd_status_index_worktree(repo, index)

    # If there's nothing to report, let them know everything's clean
    if not has_staged_changes and not has_unstaged_changes:
        print("\nnothing to commit, working tree clean")


def branch_get_active(repo: GitRepository) -> str | bool:
    """Figure out which branch we're currently on"""
    head_file = repo.file_path("HEAD")
    if not head_file or not head_file.exists():
        return False

    with head_file.open("r") as f:
        head = f.read().strip()

    if head.startswith("ref: refs/heads/"):
        # HEAD points to a branch
        return head[16:]
    else:
        # HEAD points directly to a commit (detached)
        return False


def cmd_status_branch(repo: GitRepository) -> None:
    """Show which branch we're on or if HEAD is detached"""
    branch = branch_get_active(repo)
    if branch:
        print(f"On branch {branch}.")
    else:
        print(f"HEAD detached at {object_find(repo, 'HEAD')}")


def tree_to_dict(repo: GitRepository, ref: str, prefix: str = "") -> Dict[str, str]:
    """Convert a tree into a flat dictionary mapping file paths to their SHAs"""
    ret = {}
    tree_sha = object_find(repo, ref, fmt=b"tree")
    tree = object_read(repo, tree_sha)
    if not tree or not hasattr(tree, 'items'):
        return ret

    for leaf in tree.items:
        full_path = os.path.join(prefix, leaf.path)
        is_subtree = leaf.mode.startswith(b"04")

        if is_subtree:
            # It's a directory, so recurse into it
            ret.update(tree_to_dict(repo, leaf.sha, full_path))
        else:
            # It's a file, add it to our map
            ret[full_path] = leaf.sha

    return ret


def cmd_status_head_index(repo: GitRepository, index: Any) -> bool:
    """Compare HEAD with the index to find staged changes. Returns True if anything's staged."""
    try:
        head = tree_to_dict(repo, "HEAD")
    except RuntimeError:
        # This is probably a brand new repo with no commits yet
        head = {}

    # Keep track of what we've looked at
    processed_files = set()
    has_changes = False

    staged_changes = []

    # Check each file in the index against what's in HEAD
    for entry in index.entries:
        processed_files.add(entry.name)
        if entry.name in head:
            if head[entry.name] != entry.sha:
                staged_changes.append(("modified", entry.name))
                has_changes = True
        else:
            # File exists in index but not in HEAD - it's new
            staged_changes.append(("new file", entry.name))
            has_changes = True

    # Any files that are in HEAD but missing from index are deleted
    for file_path in head:
        if file_path not in processed_files:
            staged_changes.append(("deleted", file_path))
            has_changes = True

    if staged_changes:
        print("Changes to be committed:")
        print("  (use \"mygit restore --staged <file>...\" to unstage)")
        print()
        for change_type, file_path in staged_changes:
            print(f"  {change_type}:   {file_path}")
        print()

    return has_changes


def cmd_status_index_worktree(repo: GitRepository, index: Any) -> bool:
    """Compare index with working tree to find unstaged changes. Returns True if anything's modified."""
    ignore = gitignore_read(repo)
    gitdir_prefix = str(repo.gitdir) + os.path.sep
    all_files = []

    # Walk through all files in the working directory
    for root, _, files in os.walk(repo.worktree, topdown=True):
        # Skip the .git directory itself
        if root == str(repo.gitdir) or root.startswith(gitdir_prefix):
            continue
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(repo.worktree)
            all_files.append(str(rel_path))

    modified_files = []
    deleted_files = []
    has_changes = False

    # Check each indexed file against what's actually on disk
    for entry in index.entries:
        full_path = repo.worktree / entry.name

        if not full_path.exists():
            # File is in index but missing from working tree
            deleted_files.append(entry.name)
            has_changes = True
        else:
            # File exists - check if contents have changed
            try:
                # IMPORTANT: Always open files in binary mode for consistent hashing
                with full_path.open("rb") as fd:
                    new_sha = object_hash(fd, b"blob", None)
                    if entry.sha != new_sha:
                        modified_files.append(entry.name)
                        has_changes = True
            except (OSError, PermissionError):
                # If we can't read it, assume it's modified
                modified_files.append(entry.name)
                has_changes = True

        # Remove this file from our list of all files
        if entry.name in all_files:
            all_files.remove(entry.name)

    # Show files that have been modified but not staged
    if modified_files or deleted_files:
        print("Changes not staged for commit:")
        print("  (use \"mygit add <file>...\" to update what will be committed)")
        print()

        for file_path in modified_files:
            print(f"  modified:   {file_path}")

        for file_path in deleted_files:
            print(f"  deleted:    {file_path}")

        print()

    # Show files that exist but aren't tracked
    untracked = [f for f in all_files if not check_ignore(ignore, f)]
    if untracked:
        print("Untracked files:")
        print("  (use \"mygit add <file>...\" to include in what will be committed)")
        print()
        for f in untracked:
            print(f"  {f}")
        print()
        has_changes = True

    return has_changes


def cmd_rm(args: Any) -> None:
    """Remove files from both the working tree and the index"""
    repo = find_repository()
    rm(repo, args.path)


def rm(repo: GitRepository, paths: list[str], delete: bool = True, skip_missing: bool = False) -> None:
    """The real work of removing files - from index and optionally the filesystem"""
    # Load the current index
    index = index_read(repo)
    worktree = str(repo.worktree)

    # Convert all paths to absolute and make sure they're safe
    abspaths = set()
    for path in paths:
        # Handle both relative and absolute paths
        path_obj = Path(path)
        if path_obj.is_absolute():
            abspath = path_obj.resolve()
        else:
            # Relative paths are relative to the worktree
            abspath = (repo.worktree / path_obj).resolve()

        # Security check - make sure they're not trying to remove stuff outside the repo
        try:
            abspath.relative_to(repo.worktree)
            abspaths.add(str(abspath))
        except ValueError:
            if not skip_missing:
                raise RuntimeError(f"Cannot remove paths outside of worktree: {path}")

    # Figure out which index entries to keep and which files to remove
    kept_entries = []
    remove = []

    # Go through each index entry and see if it should be removed
    for e in index.entries:
        full_path = str(repo.worktree / e.name)

        if full_path in abspaths:
            remove.append(full_path)
            abspaths.remove(full_path)
        else:
            kept_entries.append(e)

    # If there are paths left in abspaths, they weren't in the index
    if abspaths and not skip_missing:
        raise RuntimeError(f"Cannot remove paths not in the index: {abspaths}")

    # Actually delete the files from disk
    if delete:
        for path in remove:
            Path(path).unlink()

    # Update the index with the remaining entries
    index.entries = kept_entries
    index_write(repo, index)


def add(repo: GitRepository, paths: list[str], delete: bool = True, skip_missing: bool = False) -> None:
    """Add files to the index, handling directories and respecting gitignore"""
    # Start with the current index
    index = index_read(repo)

    # Load gitignore rules so we know what to skip
    ignore_rules = gitignore_read(repo)

    # Collect all the files we need to add
    files_to_add = set()

    for path in paths:
        path_obj = Path(path)

        # Convert to absolute path
        if path_obj.is_absolute():
            abs_path = path_obj.resolve()
        else:
            abs_path = (repo.worktree / path_obj).resolve()

        # Make sure the path is actually inside our repository
        try:
            rel_path_check = abs_path.relative_to(repo.worktree)
        except ValueError:
            if not skip_missing:
                raise RuntimeError(f"Path outside worktree: {path}")
            continue

        # Never add the .git directory itself
        if abs_path == repo.gitdir or str(abs_path).startswith(str(repo.gitdir) + os.sep):
            continue

        if abs_path.is_file():
            # Single file - check if it's ignored
            rel_path = abs_path.relative_to(repo.worktree)
            if not check_ignore(ignore_rules, str(rel_path)):
                files_to_add.add((abs_path, str(rel_path)))
        elif abs_path.is_dir():
            # Directory - walk through it recursively
            for root, dirs, files in os.walk(abs_path):
                root_path = Path(root)

                # Skip .git directory completely
                if root_path == repo.gitdir or str(root_path).startswith(str(repo.gitdir) + os.sep):
                    dirs.clear()  # Don't recurse into .git
                    continue

                # Remove ignored directories from the list so we don't recurse into them
                dirs_to_remove = []
                for dirname in dirs:
                    dir_path = root_path / dirname
                    try:
                        rel_dir_path = dir_path.relative_to(repo.worktree)
                        if check_ignore(ignore_rules, str(rel_dir_path)):
                            dirs_to_remove.append(dirname)
                    except ValueError:
                        dirs_to_remove.append(dirname)

                for dirname in dirs_to_remove:
                    dirs.remove(dirname)

                # Add files that aren't ignored
                for filename in files:
                    file_path = root_path / filename
                    try:
                        rel_file_path = file_path.relative_to(repo.worktree)
                        if not check_ignore(ignore_rules, str(rel_file_path)):
                            files_to_add.add((file_path, str(rel_file_path)))
                    except ValueError:
                        continue
        else:
            if not skip_missing:
                raise RuntimeError(f"Path does not exist: {path}")

    # Build a lookup table of existing index entries
    existing_entries = {e.name: e for e in index.entries}
    new_entries = []

    # Process each file we're adding
    for abs_path, rel_path in files_to_add:
        try:
            # Calculate the SHA for this file - IMPORTANT: binary mode!
            with abs_path.open("rb") as fd:
                new_sha = object_hash(fd, b"blob", repo)

            # If this file is already in the index with the same content, keep the existing entry
            if rel_path in existing_entries:
                existing_entry = existing_entries[rel_path]
                if existing_entry.sha == new_sha:
                    # File hasn't changed, no need to update
                    new_entries.append(existing_entry)
                    continue

            # File is new or has changed, create a new index entry
            stat = abs_path.stat()
            ctime_s = int(stat.st_ctime)
            ctime_ns = int(stat.st_ctime_ns % 10**9)
            mtime_s = int(stat.st_mtime)
            mtime_ns = int(stat.st_mtime_ns % 10**9)

            entry = GitIndexEntry(
                ctime=(ctime_s, ctime_ns),
                mtime=(mtime_s, mtime_ns),
                dev=stat.st_dev,
                ino=stat.st_ino,
                mode_type=0b1000,  # Regular file
                mode_perms=0o644,  # Standard permissions
                uid=stat.st_uid,
                gid=stat.st_gid,
                fsize=stat.st_size,
                sha=new_sha,
                flag_assume_valid=False,
                flag_stage=0,
                name=rel_path,
            )
            new_entries.append(entry)
            print(f"add '{rel_path}'")

        except Exception as e:
            print(f"Warning: Could not add {rel_path}: {e}")
            continue

    # Keep any existing index entries that we didn't touch
    processed_paths = {rel_path for _, rel_path in files_to_add}
    for entry in index.entries:
        if entry.name not in processed_paths:
            new_entries.append(entry)

    # Sort by name (Git requires this for compatibility)
    new_entries.sort(key=lambda e: e.name)

    # Write the updated index back to disk
    index.entries = new_entries
    index_write(repo, index)


def cmd_add(args: Any) -> None:
    """Add files to the staging area"""
    repo = find_repository()
    add(repo, args.path)


def commit_create(
    repo: GitRepository,
    tree: str,
    parent: str | None,
    author: str,
    timestamp: datetime,
    message: str,
) -> str:
    """Create a new commit object with all the metadata"""
    commit = GitCommit()
    commit.kvlm = {}
    commit.kvlm[b"tree"] = tree.encode("ascii")

    # Add parent if this isn't the first commit
    if parent:
        commit.kvlm[b"parent"] = parent.encode("ascii")

    # Clean up the commit message
    message = message.strip() + "\n"

    # Format the timezone info properly
    offset = int(timestamp.astimezone().utcoffset().total_seconds())
    hours = abs(offset) // 3600
    minutes = (abs(offset) % 3600) // 60
    tz = "{}{:02d}{:02d}".format("+" if offset >= 0 else "-", hours, minutes)

    author_line = author + timestamp.strftime(" %s ") + tz

    # Set both author and committer to the same thing for now
    commit.kvlm[b"author"] = author_line.encode("utf8")
    commit.kvlm[b"committer"] = author_line.encode("utf8")
    commit.kvlm[None] = message.encode("utf8")

    return object_write(commit, repo)


def cmd_commit(args: Any) -> None:
    """Create a new commit from whatever's currently staged"""
    repo = find_repository()
    index = index_read(repo)

    # Don't create empty commits
    if not index.entries:
        print("nothing to commit, working tree clean")
        return

    # Build a tree from the current index
    tree = tree_from_index(repo, index)

    # Find the parent commit (if any)
    try:
        parent = object_find(repo, "HEAD")
        # Check if we're actually making any changes
        parent_commit = object_read(repo, parent)
        if parent_commit and hasattr(parent_commit, 'kvlm'):
            parent_tree = parent_commit.kvlm[b"tree"].decode("ascii")
            if parent_tree == tree:
                print("nothing to commit, working tree clean")
                return
    except RuntimeError:
        # No HEAD yet - this is the first commit
        parent = None

    # Get the user's name and email from config
    config = gitconfig_read()
    author = gitconfig_user_get(config)
    if not author:
        raise RuntimeError("No user configured. Set user.name and user.email in mygit config.")

    if not args.message:
        raise RuntimeError("No commit message provided. Use -m to specify a message.")

    # Actually create the commit
    commit_sha = commit_create(repo, tree, parent, author, datetime.now(), args.message)

    # Update the current branch or HEAD to point to the new commit
    active_branch = branch_get_active(repo)
    if active_branch:
        # We're on a branch, so update the branch reference
        branch_file = repo.file_path("refs", "heads", active_branch)
        if branch_file:
            branch_file.write_text(commit_sha + "\n")
    else:
        # Detached HEAD, so update HEAD directly
        head_file = repo.file_path("HEAD")
        if head_file:
            head_file.write_text(commit_sha + "\n")

    print(f"[master (root-commit) {commit_sha[:7]}] {args.message}")
    print(f" {len(index.entries)} files changed")