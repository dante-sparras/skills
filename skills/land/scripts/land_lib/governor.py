import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

from .core import LandError, now, open_lock, stamp, state_home

HELD = "LAND_SLOT_HELD"
REPORT_AFTER = 15
EXCLUSIVE_CAP = 600
EXCLUSIVE_MAX = 7200


def governor_dir():
    return state_home() / "governor"


def worker_slots():
    config = governor_dir() / "governor.json"
    try:
        slots = int(json.loads(config.read_text()).get("slots"))
    except (OSError, ValueError, TypeError, AttributeError):
        slots = max(1, min(4, (os.cpu_count() or 4) // 4))
    return max(1, slots)


def names(kind):
    if kind == "landing":
        return ["landing"]
    if kind == "exclusive":
        return ["landing", *(f"worker-{i}" for i in range(worker_slots()))]
    return [f"worker-{i}" for i in range(worker_slots())]


def holder_of(name):
    try:
        info = json.loads((governor_dir() / f"{name}.json").read_text())
        return f"pid {info['pid']} running {info['command'][:60]!r} since {info['since'][:19]}"
    except (OSError, ValueError, KeyError):
        return "unknown"


def take(kind, count, command):
    pool = names(kind)
    need = len(pool) if kind in ("exclusive", "landing") else count
    if need > len(pool):
        raise LandError(f"{count} slots asked, but the governor has {len(pool)} worker slots")
    ordered = kind in ("exclusive", "landing")
    started, reported, held = time.monotonic(), False, {}
    while True:
        for name in pool:
            if name in held:
                continue
            if len(held) == need:
                break
            handle = open_lock(governor_dir() / f"{name}.lock")
            if handle:
                held[name] = handle
            elif ordered:
                break
        if len(held) == need:
            break
        if not ordered:
            for handle in held.values():
                handle.close()
            held = {}
        if not reported and time.monotonic() - started > REPORT_AFTER:
            busy = [f"{name}: {holder_of(name)}" for name in pool if name not in held]
            print(f"land: waiting for a {kind} slot; held by " + "; ".join(busy), file=sys.stderr)
            reported = True
        time.sleep(0.5)
    record = json.dumps({"pid": os.getpid(), "command": command, "since": stamp(now())})
    for name in held:
        (governor_dir() / f"{name}.json").write_text(record)
    return held


def give_back(held):
    for name, handle in held.items():
        with contextlib.suppress(OSError):
            (governor_dir() / f"{name}.json").unlink()
        handle.close()


@contextlib.contextmanager
def slot(kind="worker", count=1, command=""):
    if os.environ.get(HELD):
        yield
        return
    held = take(kind, count, command)
    os.environ[HELD] = kind
    try:
        yield
    finally:
        os.environ.pop(HELD, None)
        give_back(held)


def spawn(command, cwd=None, capture=False):
    options = {"cwd": cwd, "env": {**os.environ, HELD: os.environ.get(HELD, "1")}}
    if capture:
        options.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    if isinstance(command, str):
        return subprocess.Popen(command, shell=True, **options)
    return subprocess.Popen([shutil.which(command[0]) or command[0], *command[1:]], **options)


def stop(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run_build(command, cwd, timeout):
    process = spawn(command, cwd=cwd, capture=True)
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output or ""
    except subprocess.TimeoutExpired:
        stop(process)
        output, _ = process.communicate()
        return None, output or ""


def run_slot(command, count, exclusive, seconds, reason):
    if exclusive:
        if os.environ.get(HELD):
            raise LandError("slot --exclusive must be the outermost slot")
        cap = EXCLUSIVE_CAP if seconds is None else seconds
        if cap <= 0 or cap > EXCLUSIVE_MAX:
            raise LandError(f"--for must be between 1 and {EXCLUSIVE_MAX} seconds")
        if cap > EXCLUSIVE_CAP and not reason:
            raise LandError(f"--for over {EXCLUSIVE_CAP} seconds needs --reason")
        text = " ".join(command) + (f" ({reason})" if reason else "")
        with slot("exclusive", command=text):
            process = spawn(command)
            try:
                return process.wait(timeout=cap)
            except subprocess.TimeoutExpired:
                stop(process)
                print(f"land: exclusive hold ended after {cap} seconds; stopped the command", file=sys.stderr)
                return 124
    if seconds is not None or reason is not None:
        raise LandError("--for and --reason are only for slot --exclusive")
    if count < 1:
        raise LandError(f"--slots {count} is not a positive count")
    with slot("worker", count, " ".join(command)):
        return spawn(command).wait()
