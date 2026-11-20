import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .base import Adapter, CallError, Reply, child_env, last_json

MODELS = ("opus", "sonnet", "haiku")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


class Claude(Adapter):
    name = "claude"

    def __init__(self, timeout):
        super().__init__(timeout)
        self.config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
        self.lock = threading.Lock()

    def oauth(self):
        path = self.config_dir / ".credentials.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")).get("claudeAiOauth") or {}
        if sys.platform == "darwin":
            result = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                                    capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return json.loads(result.stdout).get("claudeAiOauth") or {}
        return {}

    def check_signin(self, seats):
        oauth = self.oauth()
        if not oauth.get("accessToken"):
            raise SystemExit("Claude Code is not signed in with a subscription. Run claude and sign in with Claude Max.")
        if oauth.get("subscriptionType") != "max":
            raise SystemExit(f"Claude Code is signed in with {oauth.get('subscriptionType')!r}. Only Claude Max is allowed.")
        return "claude: Claude Max OAuth token, passed per call, no API key"

    def catalog(self):
        return "Aliases. A full model ID such as claude-sonnet-5-5 also works.", [(model, EFFORTS) for model in MODELS]

    def token(self):
        with self.lock:
            oauth = self.oauth()
            if oauth.get("expiresAt", 0) / 1000 - time.time() < 300:
                self.refresh()
                oauth = self.oauth()
            if oauth.get("expiresAt", 0) / 1000 - time.time() < 60:
                raise CallError("the Claude sign-in expired. Run claude once to refresh it")
            return oauth["accessToken"]

    def refresh(self):
        folder = tempfile.mkdtemp(prefix="eval-skill-refresh-")
        try:
            subprocess.run(
                ["claude", "-p", "--model", "haiku", "--safe-mode", "--tools", "", "--no-session-persistence",
                 "--disable-slash-commands", "--strict-mcp-config", "Reply OK."],
                cwd=folder, capture_output=True, timeout=120, check=False,
                env=child_env(Path.home(), CLAUDE_CONFIG_DIR=str(self.config_dir)),
            )
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def call(self, seat, system, prompt, place, cancel):
        env = child_env(place.home, CLAUDE_CONFIG_DIR=str(place.home / ".claude"), CLAUDE_CODE_OAUTH_TOKEN=self.token())
        command = [
            "claude", "-p", "--model", seat.model, "--effort", seat.effort, "--safe-mode", "--tools", "",
            "--disable-slash-commands", "--strict-mcp-config", "--no-session-persistence",
            "--system-prompt", system, "--output-format", "json",
        ]
        code, out, err = self.run(command, place, env, prompt, cancel)
        data = last_json(out, f"claude (exit {code}, {err[-200:]})")
        if data.get("is_error") or code:
            raise CallError(f"claude error: {str(data.get('result') or err)[-400:]}")
        return Reply(data.get("result", ""), tuple(sorted(data.get("modelUsage") or {})))
