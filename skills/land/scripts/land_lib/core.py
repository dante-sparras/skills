import hashlib
import os
import posixpath
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MODES = ("human", "push", "local")
REMOTE_MODES = ("human", "push")


class LandError(Exception):
    pass


class Infrastructure(LandError):
    pass


def now():
    return datetime.now(timezone.utc)


def stamp(moment=None):
    return (moment or now()).isoformat(timespec="microseconds")


def state_home():
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "skills"


def git(*args, cwd, check=True):
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="surrogateescape", env=env)
    if check and result.returncode != 0:
        raise LandError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
    return result


def git_push(*args, cwd):
    return git("push", "--no-follow-tags", *args, cwd=cwd, check=False)


def gh(*args, cwd):
    command = shlex.split(os.environ.get("LAND_GH", "gh"))
    return subprocess.run([*command, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def git_reason(stderr):
    lines = [line.strip() for line in stderr.strip().splitlines() if line.strip()]
    remote = [line for line in lines if line.startswith("remote:")]
    return (remote or lines or ["no output"])[-1]


def tail(output):
    lines = output.strip().splitlines()[-3:]
    return " / ".join(lines) if lines else "no output"


def common_dir(path):
    found = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=path)
    return Path(found.stdout.strip()).resolve()


def canonical(path):
    value = posixpath.normpath(path.strip().replace("\\", "/")).lstrip("/")
    if value in (".", ""):
        return ""
    if value == ".." or value.startswith("../"):
        raise LandError(f"lease path {path!r} leaves the repository")
    return value


def overlaps(first, second):
    return any(a == "" or b == "" or a == b or a.startswith(b + "/") or b.startswith(a + "/")
               for a in first for b in second)


def covered(path, paths):
    return any(p == "" or path == p or path.startswith(p + "/") for p in paths)


def changed_paths(repo, base, head):
    raw = git("diff", "-z", "--name-only", "--no-renames", base, head, "--", cwd=repo).stdout
    return [p for p in raw.split("\0") if p]


def fingerprint(repo, base, head):
    diff = git("diff", "--binary", "--full-index", "--no-renames", "--no-textconv", "--no-ext-diff",
               "-U0", base, head, "--", cwd=repo).stdout
    if not diff:
        return ""
    lines = [line for line in diff.splitlines() if not line.startswith("index ")]
    lines = [re.sub(r"^@@ [^@]* @@", "@@", line) for line in lines]
    return hashlib.sha256("\n".join(lines).encode("utf-8", "surrogateescape")).hexdigest()


if os.name == "nt":
    import msvcrt

    def try_lock(handle):
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
else:
    import fcntl

    def try_lock(handle):
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def open_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    if try_lock(handle):
        return handle
    handle.close()
    return None
