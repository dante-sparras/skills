import os
from pathlib import Path

from ..textutil import read_json
from .base import Adapter, CallError, Reply, SigninFile, child_env, json_lines

FEATURES_OFF = (
    "shell_tool", "unified_exec", "view_image", "apps", "plugins", "skill_search", "tool_suggest",
    "code_mode_host", "goals", "image_generation", "sleep_tool", "skill_mcp_dependency_install", "memories",
)
ALLOWED_ITEMS = ("agent_message", "reasoning", "error", None)


class Codex(Adapter):
    name = "codex"

    def __init__(self, timeout):
        super().__init__(timeout)
        self.home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        self.signin = SigninFile(self.home / "auth.json")
        self.host_skills = sorted(
            path.as_posix() for root in (Path.home() / ".agents" / "skills", self.home / "skills")
            if root.is_dir() for path in root.glob("*/SKILL.md")
        )

    def check_signin(self, seats):
        auth = read_json(self.home / "auth.json", {})
        if auth.get("auth_mode") != "chatgpt" or auth.get("OPENAI_API_KEY"):
            raise SystemExit("Codex must be signed in with ChatGPT, not an API key. Run codex login.")
        return "codex: ChatGPT sign-in copied into each call's temporary home, no API key"

    def catalog(self):
        cache = self.home / "models_cache.json"
        models = read_json(cache, {}).get("models", [])
        return f"From {cache}.", [
            (model["slug"], tuple(level["effort"] for level in model.get("supported_reasoning_levels", [])))
            for model in models if model.get("visibility") == "list"
        ]

    def config(self, instructions):
        lines = [
            f"model_instructions_file = '{instructions.as_posix()}'",
            'web_search = "disabled"',
            "[features]",
            *[f"{feature} = false" for feature in FEATURES_OFF],
            "[agents]",
            "enabled = false",
            "[skills]",
            "include_instructions = false",
        ]
        for path in self.host_skills:
            lines += ["[[skills.config]]", f"path = '{path}'", "enabled = false"]
        return "\n".join(lines) + "\n"

    def call(self, seat, system, prompt, place, cancel):
        codex_home = place.home / ".codex"
        instructions = place.root / "instructions.md"
        instructions.write_text(system, encoding="utf-8")
        output = place.root / "last.txt"
        command = [
            "codex", "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-rules", "-s", "read-only",
            "-m", seat.model, "-c", f'model_reasoning_effort="{seat.effort}"',
            "--color", "never", "--json", "-o", str(output), "-",
        ]
        with self.signin.lent(codex_home / "auth.json"):
            (codex_home / "config.toml").write_text(self.config(instructions), encoding="utf-8")
            code, out, err = self.run(command, place, child_env(place.home, CODEX_HOME=str(codex_home)), prompt, cancel)
        if code:
            raise CallError(f"codex exited {code}: {err[-400:]}")
        tools = sorted({item.get("type") for item in completed_items(out) if item.get("type") not in ALLOWED_ITEMS})
        if tools:
            raise CallError(f"codex used tools {tools}")
        return Reply(output.read_text(encoding="utf-8") if output.is_file() else "", (seat.model,))


def completed_items(out):
    return [event.get("item") or {} for event in json_lines(out) if event.get("type") == "item.completed"]
