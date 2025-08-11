"""Git object implementations."""

import zlib
import hashlib
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TextIO, List


from .repository import GitRepository
from .refs import ref_resolve


class GitObject(ABC):
    """Base class for all git objects"""

    fmt: bytes = b""

    def __init__(self, data: Optional[bytes] = None) -> None:
        if data is not None:
            self.deserialize(data)
        else:
            self.init()

    @abstractmethod
    def serialize(self) -> bytes:
        """Serialize object to bytes"""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        """Deserialize object from bytes"""
        pass

    def init(self) -> None:
        """Initialize empty object."""
        pass


class GitBlob(GitObject):
    """Git blob object (file content)"""

    fmt = b"blob"

    def __init__(self, data: Optional[bytes] = None) -> None:
        self.blobdata: bytes = b""
        super().__init__(data)

    def serialize(self) -> bytes:
        """Serialize blob data"""
        return self.blobdata

    def deserialize(self, data: bytes) -> None:
        """Deserialize blob data"""
        self.blobdata = data


class GitCommit(GitObject):
    """Git commit object"""

    fmt = b"commit"

    def __init__(self, data: Optional[bytes] = None) -> None:
        self.kvlm: Dict[Optional[bytes], Any] = {}
        super().__init__(data)

    def deserialize(self, data: bytes) -> None:
        """Deserialize commit data"""
        self.kvlm = kvlm_parse(data)

    def serialize(self) -> bytes:
        """Serialize commit data"""
        return kvlm_serialize(self.kvlm)

    def init(self) -> None:
        """Initialize empty commit"""
        self.kvlm = {}


class GitTreeLeaf:
    """A leaf in a Git tree"""

    def __init__(self, mode: bytes, path: str, sha: str) -> None:
        self.mode = mode
        self.path = path
        self.sha = sha


def tree_parse_one(raw: bytes, start: int = 0) -> tuple[int, GitTreeLeaf]:
    """Parse one tree entry"""
    # Find space terminator of mode
    x = raw.find(b" ", start)
    assert x - start in (5, 6)

    # Read mode
    mode = raw[start:x]
    if len(mode) == 5:
        # Normalize to six bytes
        mode = b"0" + mode

    # find NULL terminator of path
    y = raw.find(b"\x00", x)
    path = raw[x + 1:y]

    # Read SHA and convert to hex string
    raw_sha = int.from_bytes(raw[y + 1: y + 21], "big")
    sha = format(raw_sha, "040x")

    return y + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)


def tree_parse(raw: bytes) -> List[GitTreeLeaf]:
    """Parse tree data"""
    pos = 0
    max_len = len(raw)
    ret = []

    while pos < max_len:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)

    return ret


def tree_leaf_sort_key(leaf: GitTreeLeaf) -> str:
    """Sort key for tree leaves"""
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"


def tree_serialize(obj: "GitTree") -> bytes:
    """Serialize tree object."""
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b""

    for item in obj.items:
        ret += item.mode
        ret += b" "
        ret += item.path.encode("utf8")
        ret += b"\x00"
        sha = int(item.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")

    return ret


class GitTree(GitObject):
    """Git tree object"""

    fmt = b"tree"

    def __init__(self, data: Optional[bytes] = None) -> None:
        self.items: List[GitTreeLeaf] = []
        super().__init__(data)

    def deserialize(self, data: bytes) -> None:
        """Deserialize tree data"""
        self.items = tree_parse(data)

    def serialize(self) -> bytes:
        """Serialize tree data"""
        return tree_serialize(self)

    def init(self) -> None:
        """Initialize empty tree"""
        self.items = []


class GitTag(GitCommit):
    """Git tag object"""

    fmt = b"tag"


def kvlm_parse(
    raw: bytes,
    start: int = 0,
    dct: Optional[Dict[Optional[bytes], Any]] = None
) -> Dict[Optional[bytes], Any]:
    """Parse key-value list with message format used by commits and tags"""

    if dct is None:
        dct = {}

    # Find next space and newline
    spc = raw.find(b" ", start)
    nl = raw.find(b"\n", start)

    # If newline appears first (or no space), assume blank line
    # The remainder is the message
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start + 1:]
        return dct

    # Recursive case: read key-value pair
    key = raw[start:spc]

    # Find end of value (continuation lines begin with space)
    end = start
    while True:
        end = raw.find(b"\n", end + 1)
        if end + 1 >= len(raw) or raw[end + 1] != ord(" "):
            break

    # Grab value and drop leading space on continuation lines
    value = raw[spc + 1: end].replace(b"\n ", b"\n")

    # Handle multiple values for same key
    if key in dct:
        if isinstance(dct[key], list):
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end + 1, dct=dct)


def kvlm_serialize(kvlm: Dict[Optional[bytes], Any]) -> bytes:
    """Serialize key-value list with message"""
    ret = b""

    for k in kvlm.keys():
        if k is None:  # skip the message itself
            continue
        val = kvlm[k]
        # Normalize to list
        if not isinstance(val, list):
            val = [val]

        for v in val:
            if isinstance(v, str):
                v = v.encode("utf8")
            ret += k + b" " + v.replace(b"\b", b"\n ") + b"\n"

        # Append message
        if None in kvlm:
            message = kvlm[None]
            if isinstance(message, str):
                message = message.encode("utf8")
            ret += b"\n" + message

        return ret


def object_read(repo: GitRepository, sha: str) -> Optional[GitObject]:
    """Read object from repository"""

    path = repo.file_path("objects", sha[0:2], sha[2:])

    if not path or not path.is_file():
        return None

    with path.open("rb") as f:
        raw = zlib.decompress(f.read())

        # read object type
        x = raw.find(b" ")
        fmt = raw[0:x]

        # read and validate object size
        y = raw.find(b"\x00", x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw) - y - 1:
            raise RuntimeError(f"Malformed object {sha}: bad length")

        # Pick constructor
        match fmt:
            case b"commit":
                cls = GitCommit
            case b"tree":
                cls = GitTree
            case b"blob":
                cls = GitBlob
            case b"tag":
                cls = GitTag
            case _:
                raise RuntimeError(
                    f"Unknown type {fmt.decode('ascii')} for object {sha}"
                    )

        return cls(raw[y + 1:])


def object_write(obj: GitObject, repo: Optional[GitRepository] = None) -> str:
    """Write object to repository"""
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    # compute hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        # Compute path
        path = repo.file_path("objects", sha[0:2], sha[2:], mkdir=True)

        if path and not path.exists():
            with path.open("wb") as f:
                # Compress and write
                f.write(zlib.compress(result))

    return sha


def object_hash(fd, fmt: bytes, repo=None) -> str:
    """Hash object, writing it to repo if provided"""
    # Read the data properly
    data = fd.read()

    # Choose constructor according to fmt argument
    match fmt:
        case b"commit":
            obj = GitCommit(data)
        case b"tree":
            obj = GitTree(data)
        case b"blob":
            obj = GitBlob(data)
        case b"tag":
            obj = GitTag(data)
        case _:
            raise RuntimeError(f"Unknown type {fmt}!")

    return object_write(obj, repo)


def object_resolve(repo: GitRepository, name: str) -> List[str]:
    """Resolve name to object hash(es)"""
    candidates = []
    hash_re = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    # if empty string then abort
    if not name.strip():
        return []

    if name == "HEAD":
        head_ref = ref_resolve(repo, "HEAD")
        return [head_ref] if head_ref else []

    # If it's a hex string, try for a hash
    if hash_re.match(name):
        name = name.lower()
        prefix = name[0:2]
        objects_dir = repo.dir_path("objects", prefix, mkdir=False)
        if objects_dir:
            rem = name[2:]
            for f in objects_dir.iterdir():
                if f.name.startswith(rem):
                    candidates.append(prefix + f.name)

    # Try for references
    as_tag = ref_resolve(repo, f"refs/tags/{name}")
    if as_tag:
        candidates.append(as_tag)

    as_branch = ref_resolve(repo, f"refs/heads/{name}")
    if as_branch:
        candidates.append(as_branch)

    as_remote_branch = ref_resolve(repo, f"refs/remotes/{name}")
    if as_remote_branch:
        candidates.append(as_remote_branch)

    return candidates


def object_find(
        repo: GitRepository,
        name: str,
        fmt: Optional[bytes] = None,
        follow: bool = True
        ) -> str:
    """Find object by name"""
    shas = object_resolve(repo, name)

    if not shas:
        raise RuntimeError(f"No such reference {name}.")

    if len(shas) > 1:
        raise RuntimeError(f"Ambiguous reference {name}: Candidates are:\n - {chr(10) + ' - '.join(shas)}")

    sha = shas[0]

    if not fmt:
        return sha

    while True:
        obj = object_read(repo, sha)
        if not obj:
            return sha

        if obj.fmt == fmt:
            return sha

        if not follow:
            return sha

        if obj.fmt == b"tag":
            sha = obj.kvlm[b"object"].decode("ascii")
        elif obj.fmt == b"commit" and fmt == b"tree":
            sha = obj.kvlm[b"tree"].decode("ascii")
        else:
            return sha
