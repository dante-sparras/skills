import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

STRIPPED_ENV = ("ANTHROPIC_", "OPENAI_", "XAI_", "CLAUDE", "CODEX_", "GROK_", "OPENCODE", "XDG_")


class CallError(Exception):
    pass


@dataclass(frozen=True)
class Reply:
    text: str
    models: tuple


@dataclass(frozen=True)
class Scratch:
    root: Path
    work: Path
    home: Path


@contextmanager
def scratch():
    root = Path(tempfile.mkdtemp(prefix="eval-skill-"))
    try:
        work, home = root / "work", root / "home"
        work.mkdir()
        home.mkdir()
        yield Scratch(root, work, home)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def child_env(home, **extra):
    env = {key: value for key, value in os.environ.items()
           if not key.endswith("_API_KEY") and not key.startswith(STRIPPED_ENV)}
    env.update(HOME=str(home), USERPROFILE=str(home), NO_COLOR="1", **extra)
    return env


def kill_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False)
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_process(command, cwd, env, stdin_text, timeout, cancel):
    process = subprocess.Popen(
        command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )
    deadline = time.monotonic() + timeout
    pending = stdin_text or ""
    while True:
        try:
            out, err = process.communicate(pending, timeout=1)
            return process.returncode, out, err
        except subprocess.TimeoutExpired:
            pending = None
            if cancel.is_set():
                reason = "cancelled"
            elif time.monotonic() > deadline:
                reason = f"timed out after {timeout}s"
            else:
                continue
            kill_tree(process)
            process.communicate()
            raise CallError(reason)


def last_json(text, what):
    candidates = ([text[text.find("{"):]] if "{" in text else []) + text.strip().splitlines()[-1:]
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    raise CallError(f"{what} printed no JSON: {text[-400:]}")


def json_lines(text):
    for line in text.splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


class SigninFile:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def copy_to(self, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            data = self.path.read_bytes()
        target.write_bytes(data)
        return data

    def write_back(self, target, original):
        if not target.is_file():
            return
        updated = target.read_bytes()
        if updated == original:
            return
        try:
            json.loads(updated)
        except ValueError:
            return
        with self.lock:
            if self.path.read_bytes() == original:
                temporary = self.path.with_suffix(".eval-skill.tmp")
                temporary.write_bytes(updated)
                temporary.replace(self.path)

    @contextmanager
    def lent(self, target):
        original = self.copy_to(target)
        try:
            yield
        finally:
            self.write_back(target, original)


class Adapter:
    name = ""

    def __init__(self, timeout):
        self.timeout = timeout

    def check_signin(self, seats):
        raise NotImplementedError

    def catalog(self):
        raise NotImplementedError

    def call(self, seat, system, prompt, place, cancel):
        raise NotImplementedError

    def ask(self, seat, system, prompt, cancel):
        if not shutil.which(self.name):
            raise CallError(f"the {self.name} CLI is not on PATH")
        with scratch() as place:
            return self.call(seat, system, prompt, place, cancel)

    def run(self, command, place, env, stdin_text, cancel):
        return run_process(command, place.work, env, stdin_text, self.timeout, cancel)
