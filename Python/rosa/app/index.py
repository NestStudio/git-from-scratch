from math import ceil
from pathlib import Path
from typing import Optional, Tuple, List

from .repository import GitRepository
from .objects import GitTree, GitTreeLeaf, object_write


class GitIndexEntry:
    """An entry in the Git index."""

    def __init__(
        self,
        ctime: Optional[Tuple[int, int]] = None,
        mtime: Optional[Tuple[int, int]] = None,
        dev: Optional[int] = None,
        ino: Optional[int] = None,
        mode_type: Optional[int] = None,
        mode_perms: Optional[int] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        fsize: Optional[int] = None,
        sha: Optional[str] = None,
        flag_assume_valid: Optional[bool] = None,
        flag_stage: Optional[int] = None,
        name: Optional[str] = None,
    ) -> None:
        # The last time a file's metadata changed
        self.ctime = ctime or (0, 0)
        # The last time a file's data changed
        self.mtime = mtime or (0, 0)
        # The ID of device containing this file
        self.dev = dev or 0
        # The file's inode number
        self.ino = ino or 0
        # The object type: b1000 (regular), b1010 (symlink), b1110 (gitlink)
        self.mode_type = mode_type or 0
        # The object permissions, an integer
        self.mode_perms = mode_perms or 0
        # User ID of owner
        self.uid = uid or 0
        # Group ID of owner
        self.gid = gid or 0
        # Size of this object, in bytes
        self.fsize = fsize or 0
        # The object's SHA
        self.sha = sha or ""
        self.flag_assume_valid = flag_assume_valid or False
        self.flag_stage = flag_stage or 0
        # Name of the object (full path)
        self.name = name or ""


class GitIndex:
    """Git index (staging area)"""

    def __init__(
            self, version: int = 2,
            entries: Optional[List[GitIndexEntry]] = None
            ) -> None:
        self.version = version
        self.entries = entries or []


def index_read(repo: GitRepository) -> GitIndex:
    """Read the index file"""
    index_file = repo.file_path("index")

    if not index_file or not index_file.exists():
        return GitIndex()

    with index_file.open("rb") as f:
        raw = f.read()

    header = raw[:12]
    signiture = header[:4]
    if signiture != b"DIRC":
        raise RuntimeError("Invalid index signature")

    version = int.from_bytes(header[4:8], "big")
    if version != 2:
        raise RuntimeError("mygit only supports index file version 2")

    count = int.from_bytes(header[8:12], "big")

    entries = []
    content = raw[12:]
    idx = 0

    for i in range(count):
        # Read creation time
        ctime_s = int.from_bytes(content[idx: idx + 4], "big")
        ctime_ns = int.from_bytes(content[idx + 4: idx + 8], "big")
        # Read modification time
        mtime_s = int.from_bytes(content[idx + 8: idx + 12], "big")
        mtime_ns = int.from_bytes(content[idx + 12: idx + 16], "big")
        # Device ID
        dev = int.from_bytes(content[idx + 16: idx + 20], "big")
        # Inode
        ino = int.from_bytes(content[idx + 20: idx + 24], "big")
        # Ignored
        unused = int.from_bytes(content[idx + 24: idx + 26], "big")
        if unused != 0:
            raise RuntimeError("Invalid index entry")

        mode = int.from_bytes(content[idx + 26: idx + 28], "big")
        mode_type = mode >> 12
        if mode_type not in [0b1000, 0b1010, 0b1110]:
            raise RuntimeError(f"Invalid mode type: {mode_type}")
        mode_perms = mode & 0b0000000111111111

        # User and Group ID
        uid = int.from_bytes(content[idx + 28: idx + 32], "big")
        gid = int.from_bytes(content[idx + 32: idx + 36], "big")
        # Size
        fsize = int.from_bytes(content[idx + 36: idx + 40], "big")
        # SHA (object ID)
        sha = format(
            int.from_bytes(content[idx + 40: idx + 60], "big"), "040x"
            )
        # Flags
        flags = int.from_bytes(content[idx + 60: idx + 62], "big")
        # Parse flags
        flag_assume_valid = (flags & 0b1000000000000000) != 0  # Check bit 15
        flag_extended = (flags & 0b0100000000000000) != 0  # Check bit 14
        if flag_extended:
            raise RuntimeError("Extended flags not supported")
        flag_stage = flags & 0b0011000000000000  # Extract bits 13-12
        name_length = flags & 0b0000111111111111   # Extract bits 11-0

        # We've read 62 bytes so far
        idx += 62

        if name_length < 0xFFF:  # If name length < 4095
            # Verify null termination
            if idx + name_length >= len(content) or content[idx + name_length] != 0x00:
                raise RuntimeError("Invalid name termination")
            raw_name = content[idx: idx + name_length]
            idx += name_length + 1  # +1 for null terminator
        else:
            # Name is 4095+ bytes, find null terminator manually
            null_idx = content.find(b"\x00", idx + 0xFFF)
            if null_idx == -1:
                raise RuntimeError("Name not null-terminated")
            raw_name = content[idx:null_idx]
            idx = null_idx + 1

        # Parse name as UTF-8
        name = raw_name.decode("utf8")

        # Data is padded on multiples of eight bytes
        idx = 8 * ceil(idx / 8)

        # Add entry to list
        entries.append(
            GitIndexEntry(
                ctime=(ctime_s, ctime_ns),
                mtime=(mtime_s, mtime_ns),
                dev=dev,
                ino=ino,
                mode_type=mode_type,
                mode_perms=mode_perms,
                uid=uid,
                gid=gid,
                fsize=fsize,
                sha=sha,
                flag_assume_valid=flag_assume_valid,
                flag_stage=flag_stage,
                name=name,
            )
        )

    return GitIndex(version=version, entries=entries)


def index_write(repo: GitRepository, index: GitIndex) -> None:
    """Write the index file"""
    index_file = repo.file_path("index")
    if not index_file:
        raise RuntimeError("Cannot create index file")

    with index_file.open("wb") as f:
        # HEADER
        # write magic bytes
        f.write(b"DIRC")
        # write vesion number
        f.write(index.version.to_byes(4, "big"))
        # write number from entries
        f.write(len(index.entries).to_bytes(4, "big"))

        # ENTRIES
        idx = 0
        for e in index.entries:
            f.write(e.ctime[0].to_bytes(4, "big"))
            f.write(e.ctime[1].to_bytes(4, "big"))
            f.write(e.mtime[0].to_bytes(4, "big"))
            f.write(e.mtime[1].to_bytes(4, "big"))
            f.write(e.dev.to_bytes(4, "big"))
            f.write(e.ino.to_bytes(4, "big"))

            # Mode
            mode = (e.mode_type << 12) | e.mode_perms
            f.write(mode.to_bytes(4, "big"))

            f.write(e.uid.to_bytes(4, "big"))
            f.write(e.gid.to_bytes(4, "big"))
            f.write(e.fsize.to_bytes(4, "big"))

            # SHA
            f.write(int(e.sha, 16).to_bytes(20, "big"))

            # Flags
            flag_assume_valid = 0x1 << 15 if e.flag_assume_valid else 0

            name_bytes = e.name.encode("utf8")
            bytes_len = len(name_bytes)
            name_length = min(bytes_len, 0xFFF)  # Max 4095

            # Merge flags and name length
            f.write((flag_assume_valid | e.flag_stage | name_length).to_bytes(2, "big"))

            # Write name and null terminator
            f.write(name_bytes)
            f.write(b"\x00")

            idx += 62 + len(name_bytes) + 1

            # Add padding if necessary
            if idx % 8 != 0:
                pad = 8 - (idx % 8)
                f.write(b"\x00" * pad)
                idx += pad


def tree_from_index(repo: GitRepository, index: GitIndex) -> str:
    """Create a tree object from the index"""
    contents = {"": []}

    # Enumerate entries and organize by directory
    for entry in index.entries:
        dirname = str(Path(entry.name).parent) if Path(entry.name).parent != Path(".") else ""

        # Create all dictionary entries up to root
        key = dirname
        while key != "":
            if key not in contents:
                contents[key] = []
            key = str(Path(key).parent) if Path(key).parent != Path(".") else ""

        # Store entry in the appropriate directory
        contents[dirname].append(entry)

    # Sort directories by length (longest first)
    sorted_paths = sorted(contents.keys(), key=len, reverse=True)

    # Process directories from deepest to shallowest
    sha = None
    for path in sorted_paths:
        # Create new tree object
        tree = GitTree()

        # Add each entry to the tree
        for entry in contents[path]:
            if isinstance(entry, GitIndexEntry):
                # Regular file entry
                leaf_mode = f"{entry.mode_type:02o}{entry.mode_perms:04o}".encode("ascii")
                leaf = GitTreeLeaf(
                    mode=leaf_mode,
                    path=Path(entry.name).name,
                    sha=entry.sha
                )
            else:
                # Subdirectory (stored as tuple: basename, SHA)
                leaf = GitTreeLeaf(
                    mode=b"040000",
                    path=entry[0],
                    sha=entry[1]
                )

            tree.items.append(leaf)

        # Write tree to repository
        sha = object_write(tree, repo)

        # Add tree to parent directory
        parent = str(Path(path).parent) if path and Path(path).parent != Path(".") else ""
        base = Path(path).name if path else ""
        if base:  # Don't add root to itself
            contents[parent].append((base, sha))

    return sha if sha else ""
