import json
import re
import shutil
import subprocess
import threading
import time

from .base import Adapter, CallError, Reply, child_env, json_lines, run_process, scratch

AGENT = "eval"
MODEL_LINE = re.compile(r"^(\S+/\S+)$", re.M)
SIGNIN_MARGIN = 7200


def config(system):
    return {
        "agent": {AGENT: {"mode": "primary", "prompt": system, "tools": {"*": False}, "permission": {"*": "deny"}}},
        "permission": {"*": "deny"},
        "tools": {"*": False},
        "mcp": {},
        "plugin": [],
        "instructions": [],
        "autoupdate": False,
        "share": "disabled",
    }


def environment(home, system):
    return child_env(
        home,
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_DATA_HOME=str(home / ".local" / "share"),
        XDG_CACHE_HOME=str(home / ".cache"),
        XDG_STATE_HOME=str(home / ".local" / "state"),
        OPENCODE_CONFIG_CONTENT=json.dumps(config(system)),
        OPENCODE_DISABLE_CLAUDE_CODE="1",
        OPENCODE_DISABLE_AUTOUPDATE="1",
    )


def provider(model):
    return model.split("/", 1)[0]


class Opencode(Adapter):
    name = "opencode"

    def __init__(self, timeout):
        super().__init__(timeout)
        self.free = set()
        self.signins = {}

    def free_models(self):
        with scratch() as place:
            code, out, err = run_process(["opencode", "models", "--standalone"], place.work,
                                         environment(place.home, ""), "", 120, threading.Event())
        if code:
            raise SystemExit(f"opencode models failed: {err[-300:]}")
        return set(MODEL_LINE.findall(out))

    def check_signin(self, seats):
        self.free = self.free_models()
        needed = sorted({provider(seat.model) for seat in seats if seat.model not in self.free})
        if "opencode" in needed:
            raise SystemExit("Only the free opencode/ models are allowed. The others are paid Zen models. "
                             "Run run.py panel --list to see the free ones.")
        if not needed:
            return "opencode: free models only, no sign-in passed"
        exported = subprocess.run(["opencode", "auth", "export"], stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
        entries = json.loads(exported.stdout or "[]")
        for name in needed:
            mine = [entry for entry in entries if entry.get("integrationID") == name and entry.get("active", True)]
            if not mine:
                raise SystemExit(f"opencode has no {name} sign-in. Run opencode auth login and sign in with a subscription.")
            for entry in mine:
                value = entry.get("value") or {}
                if value.get("type") != "oauth":
                    raise SystemExit(f"opencode's {name} sign-in is an API key. Only subscription sign-ins are allowed.")
                if value.get("expires", 0) / 1000 - time.time() < SIGNIN_MARGIN:
                    raise SystemExit(f"opencode's {name} sign-in expires within two hours. Run opencode once so it refreshes.")
            self.signins[name] = mine
        return f"opencode: free models need no sign-in, {', '.join(needed)} subscription sign-ins imported per call, no API key"

    def catalog(self):
        listing = subprocess.run(["opencode", "models"], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=120, check=False).stdout
        free = self.free or self.free_models()
        models = sorted(set(MODEL_LINE.findall(listing)) | free)
        note = ("Effort is a model variant such as high, or default for none. Only free opencode/ models and "
                "providers signed in with a subscription are allowed.")
        return note, [(model + ("  (free)" if model in free else ""), ("default",)) for model in models]

    def call(self, seat, system, prompt, place, cancel):
        env = environment(place.home, system)
        if seat.model not in self.free:
            code, _, err = self.run(["opencode", "auth", "import", "--standalone"], place, env,
                                    json.dumps(self.signins[provider(seat.model)]), cancel)
            if code:
                raise CallError(f"opencode could not import the sign-in: {err[-300:]}")
        if shutil.which("git"):
            subprocess.run(["git", "init", "-q"], cwd=place.work, capture_output=True, check=False)
        model = seat.model if seat.effort == "default" else f"{seat.model}#{seat.effort}"
        command = ["opencode", "run", "--standalone", "--agent", AGENT, "-m", model, "--format", "json"]
        code, out, err = self.run(command, place, env, prompt, cancel)
        texts, problems = [], []
        for event in json_lines(out):
            kind = event.get("type")
            part = event.get("part") or {}
            if kind == "text":
                texts.append(part.get("text", ""))
            elif kind == "error":
                problems.append(str((event.get("error") or {}).get("message", event))[:300])
            elif kind in ("tool_use", "tool") or part.get("type") == "tool":
                problems.append(f"used tool {part.get('tool', '?')}")
        if problems or code:
            raise CallError(f"opencode: {'; '.join(problems) or err[-300:]}")
        return Reply("".join(texts), (seat.model,))
