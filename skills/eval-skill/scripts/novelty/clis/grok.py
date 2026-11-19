import json
import os
import re
import subprocess
from pathlib import Path

from ..textutil import read_json
from .base import Adapter, CallError, Reply, SigninFile, child_env, last_json

EFFORTS = ("low", "medium", "high", "xhigh")
DISALLOWED = ",".join((
    "run_terminal_command", "read_file", "search_replace", "list_dir", "grep", "write", "todo_write", "monitor",
    "search_tool", "use_tool", "workflow", "image_gen", "image_edit", "image_to_video", "reference_to_video",
    "scheduler_create", "scheduler_delete", "scheduler_list", "kill_command_or_subagent",
    "get_command_or_subagent_output", "enter_plan_mode", "exit_plan_mode", "ask_user_question", "send_feedback",
))
FINISHED = (None, "end_turn", "stop", "completed")


class Grok(Adapter):
    name = "grok"

    def __init__(self, timeout):
        super().__init__(timeout)
        self.home = Path(os.environ.get("GROK_HOME") or Path.home() / ".grok")
        self.signin = SigninFile(self.home / "auth.json")

    def check_signin(self, seats):
        auth = read_json(self.home / "auth.json", {})
        modes = {entry.get("auth_mode") for entry in auth.values() if isinstance(entry, dict)}
        if not modes or any("key" in str(mode).lower() for mode in modes):
            raise SystemExit("Grok Build must be signed in with grok.com, not an API key. Run grok login.")
        return "grok: grok.com sign-in copied into each call's temporary home, no API key"

    def catalog(self):
        listing = subprocess.run(["grok", "models"], capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=60, check=False).stdout
        return "From grok models.", [(match.group(1), EFFORTS) for match in re.finditer(r"^\s*[-*]\s+(\S+)", listing, re.M)]

    def call(self, seat, system, prompt, place, cancel):
        grok_home = place.home / ".grok"
        ignore = [(grok_home / "bundled" / name).as_posix() for name in ("skills", "workflows")]
        ignore += ["~/.claude/skills", "~/.agents/skills", "~/.grok/skills"]
        prompt_file = place.root / "prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        command = [
            "grok", "-m", seat.model, "--effort", seat.effort, "--system-prompt-override", system,
            "--disallowed-tools", DISALLOWED, "--no-subagents", "--no-plan", "--disable-web-search",
            "--max-turns", "2", "--verbatim", "--output-format", "json", "--prompt-file", str(prompt_file),
        ]
        with self.signin.lent(grok_home / "auth.json"):
            (grok_home / "config.toml").write_text("[skills]\nignore = " + json.dumps(ignore) + "\n", encoding="utf-8")
            code, out, err = self.run(command, place, child_env(place.home, GROK_HOME=str(grok_home)), None, cancel)
        data = last_json(out, f"grok (exit {code}, {err[-200:]})")
        if code or data.get("stopReason") not in FINISHED:
            raise CallError(f"grok stopped with {data.get('stopReason')}: {err[-300:]}")
        return Reply(data.get("text", ""), tuple(sorted(data.get("modelUsage") or {})))
