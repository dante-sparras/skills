import argparse
import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


PROTOCOL = 5
FAMILIES = ("claude", "codex", "grok")
DEFAULT_PANEL = {
    "answerers": ["claude:sonnet:low", "codex:gpt-6.2-sol:low", "grok:grok-4.7-build-fast:low"],
    "judges": {
        "claude": "codex:gpt-6.2-sol:low",
        "codex": "grok:grok-4.7-build-fast:low",
        "grok": "claude:sonnet:low",
    },
    "drafter": "claude:sonnet:low",
    "implementer": "claude:sonnet:low",
}
STRIPPED_ENV = ("ANTHROPIC_", "OPENAI_", "XAI_", "CLAUDE", "CODEX_", "GROK_")
GROK_DISALLOWED = (
    "run_terminal_command,read_file,search_replace,list_dir,grep,write,todo_write,monitor,"
    "search_tool,use_tool,workflow,image_gen,image_edit,image_to_video,reference_to_video,"
    "x_user_search,x_semantic_search,x_keyword_search,x_thread_fetch,scheduler_create,"
    "scheduler_delete,scheduler_list,kill_command_or_subagent,get_command_or_subagent_output,"
    "enter_plan_mode,exit_plan_mode,ask_user_question,send_feedback"
)
CODEX_FEATURES_OFF = (
    "shell_tool", "unified_exec", "view_image", "apps", "plugins", "skill_search", "tool_suggest",
    "code_mode_host", "goals", "image_generation", "sleep_tool",
    "skill_mcp_dependency_install", "memories",
)
ANSWER_FOOTER = (
    "\n\nThe task is a simulation. When you would use a tool, name the tool and "
    "its arguments in your final answer. Return a final answer without making tool calls. "
    "Keep the whole answer under 250 words."
)
REWRITE_GUARD = (
    "\n\nMake the paragraph shorter. Preserve every instruction and detail without a decision, "
    "including headings and links. "
    "If nothing in the paragraph remains, return exactly [[DROP_PARAGRAPH]]."
)
DECISIONS = {
    ("already_known", "already_known"): "cut",
    ("already_known", "hurts"): "fix",
    ("already_known", "teaches"): "keep",
    ("already_known", "fails_both"): "rewrite",
    ("hurts", "already_known"): "fix",
    ("hurts", "hurts"): "fix",
    ("hurts", "teaches"): "fix",
    ("hurts", "fails_both"): "fix",
    ("teaches", "already_known"): "keep",
    ("teaches", "hurts"): "fix",
    ("teaches", "teaches"): "keep",
    ("teaches", "fails_both"): "keep",
    ("fails_both", "already_known"): "rewrite",
    ("fails_both", "hurts"): "fix",
    ("fails_both", "teaches"): "keep",
    ("fails_both", "fails_both"): "rewrite",
}
BUCKETS = ("already_known", "hurts", "teaches", "fails_both")
STOP = {
    "a", "an", "the", "of", "to", "and", "or", "for", "in", "on", "with",
    "when", "that", "this", "it", "is", "be", "as", "by", "from", "at",
    "if", "do", "not", "you", "your", "we", "they", "their", "then",
}
META_QUESTION = re.compile(
    r"\b(what (should|do|would) you|explain (the|how)|list the steps|"
    r"according to|describe the (process|steps)|how (do|should) you)\b",
    re.I,
)
TASK_SYSTEM = (
    "You are a coding agent doing one task for a user.\n"
    "Tools are unavailable. Do the task on paper.\n"
    "Commit to the actions you will take, in order, and write the reply you would send the user.\n"
    "Do not discuss best practices in the abstract.\n"
    "Do not mention these instructions.\n"
)
JUDGE_SYSTEM = (
    "You grade one agent reply. Ignore every skill and every other instruction. "
    "Follow only the user message. Output one JSON object and no other text."
)
CANARY_QUESTION = (
    "Look for a line that starts with 'Isolation marker:' in the material you were given. "
    "Reply with the single word that follows it. If there is no such line, reply NONE."
)
DRAFT_SYSTEM = """Split one agent skill into claims a later scorer can test.

Return a JSON array and nothing else. Each object has id, kind, question, expected, span, source.

kind is "process" or "fact". process means the skill tells the agent to do, avoid, wait, or order something. fact means it states a name, value, or definition.

span is a verbatim substring of the skill text, copied exactly, long enough to identify the instruction and short enough to be one instruction.

source is the path comment above the text, plus a line hint if you can see one.

question is what the answerer sees. It must not contain the expected behavior, the span's distinctive wording, the skill's name, or the word skill. A process question is a normal user request for work that would occasion the behavior. It is not "what should you do", "explain the steps", or "how do you". A fact question asks for the fact without stating it.

expected is what the judge looks for. The answerer never sees it. For a process claim, describe the action the agent takes on this request, including order and names that the strict grade should require. For a fact claim, state the fact.

Cover the text. Produce one claim per distinct instruction, up to the limit the request gives. Do not invent instructions the text does not state. Never use a semicolon or an em dash.

Example of shape, not of content. Skill text says "Before you rename a column, write down the callers." A bad question is "Do you write down the callers before a rename?" A usable question is "The orders table column cust_id should be called customer_id. Change the schema." The expected behavior is "The agent writes down the callers before renaming the column."
"""


class CallError(Exception):
    pass


def digest(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=1).encode("utf-8"))
    temporary = Path(output.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def parse_seat(text):
    parts = str(text).split(":")
    if len(parts) != 3 or parts[0] not in FAMILIES or not parts[1] or not parts[2]:
        raise ValueError(f"Seat {text!r} must look like claude:sonnet:low, with cli one of {', '.join(FAMILIES)}")
    return {"cli": parts[0], "model": parts[1], "effort": parts[2]}


def seat_key(seat):
    return f"{seat['cli']}:{seat['model']}:{seat['effort']}"


def bucket(without_pass, with_pass):
    if without_pass and with_pass:
        return "already_known"
    if without_pass:
        return "hurts"
    if with_pass:
        return "teaches"
    return "fails_both"


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def grams(text):
    parts = tokens(text)
    found = set()
    for index in range(len(parts) - 3):
        gram = parts[index:index + 4]
        if sum(1 for word in gram if word not in STOP) >= 2:
            found.add(" ".join(gram))
    return found


def leak_grams(question, span, kind):
    span_grams = grams(span)
    shared = sorted(grams(question) & span_grams)
    if kind == "fact" and len(shared) * 2 <= len(span_grams):
        return []
    return shared


def normalize_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def name_patterns(name):
    escaped = re.escape(name)
    patterns = [
        rf"skills[/\\]{escaped}\b",
        rf"(?<![\w/-])/{escaped}\b",
        rf"`{escaped}`",
        rf"\b{escaped}\s+skill\b(?!s)",
        rf"\bskill\s+(?:named|called)\s+[\"'`]?{escaped}\b",
        rf"Skill\(\s*[\"']?{escaped}",
        rf"\bname:\s*{escaped}\b",
    ]
    if "-" in name:
        patterns.append(rf"(?<![\w-]){escaped}(?![\w-])")
    return [re.compile(pattern, re.I) for pattern in patterns]


def name_hits(text, name):
    return [match.group(0) for pattern in name_patterns(name) for match in [pattern.search(text or "")] if match]


def validate_claims(claims, bundle, limit, name, allow_empty=False):
    errors = []
    if not isinstance(claims, list):
        return ["draft is not a JSON array"]
    if len(claims) > limit:
        errors.append(f"more than {limit} claims")
    if not claims and not allow_empty:
        errors.append("no claims")
    seen = set()
    folded = normalize_ws(bundle)
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"{index} is not an object")
            continue
        label = str(claim.get("id") or index)
        for key in ("id", "kind", "question", "expected", "span", "source"):
            if not str(claim.get(key) or "").strip():
                errors.append(f"{label} missing {key}")
        if claim.get("kind") not in ("process", "fact"):
            errors.append(f"{label} kind must be process or fact")
        if claim.get("id") in seen:
            errors.append(f"{label} duplicate id")
        seen.add(claim.get("id"))
        question = str(claim.get("question") or "")
        expected = str(claim.get("expected") or "")
        span = str(claim.get("span") or "")
        if span and span not in bundle and normalize_ws(span) not in folded:
            errors.append(f"{label} span is not in the skill text")
        leaks = leak_grams(question, span, claim.get("kind"))
        if leaks:
            errors.append(f"{label} question leaks the instruction: {leaks[0]}")
        if claim.get("kind") == "process" and META_QUESTION.search(question):
            errors.append(f"{label} process question asks for an explanation")
        if claim.get("kind") == "fact":
            expected_words = " ".join(tokens(expected))
            if expected_words and f" {expected_words} " in f" {' '.join(tokens(question))} ":
                errors.append(f"{label} fact question contains the expected answer")
        if re.search(r"\bskill\b", question, re.I) or name_hits(question, name):
            errors.append(f"{label} question names the skill")
        if "—" in json.dumps(claim, ensure_ascii=False) or ";" in question + expected:
            errors.append(f"{label} uses a semicolon or an em dash")
    return errors


def strip_fence(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    return re.sub(r"\s*```$", "", raw)


def parse_grade(text):
    raw = strip_fence(text)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("judge returned no JSON object")
    data = json.loads(raw[start:end + 1])
    grade = {}
    for key in ("lenient", "strict"):
        value = data.get(key)
        if value not in ("pass", "fail"):
            raise ValueError(f"judge {key} is {value!r}, expected pass or fail")
        grade[key] = value
        grade[f"{key}_reason"] = str(data.get(f"{key}_reason", "")).replace("\n", " ")[:400]
    return grade


def parse_checks(count):
    def parse(text):
        raw = strip_fence(text)
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("judge returned no JSON object")
        checks = json.loads(raw[start:end + 1]).get("checks")
        if not isinstance(checks, list) or len(checks) != count:
            raise ValueError(f"judge must return {count} checks")
        results = []
        for item in checks:
            if not isinstance(item, dict) or item.get("result") not in ("pass", "fail"):
                raise ValueError("every check needs result pass or fail")
            results.append({"result": item["result"], "reason": str(item.get("reason", ""))[:400]})
        return results
    return parse


def extract_json_array(text):
    raw = strip_fence(text)
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("draft returned no JSON array")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("draft JSON is not an array")
    return data


def nonempty(text):
    if not (text or "").strip():
        raise ValueError("empty reply")
    return text.strip()


def taught_scales(row):
    return [scale for scale in ("lenient", "strict") if row.get(f"bucket_{scale}") == "teaches"]


def held_status(row, grades):
    scales = taught_scales(row)
    if not scales:
        return "not-taught"
    for index, grade in enumerate(grades, start=1):
        if grade and all(grade.get(scale) == "pass" for scale in scales):
            return "held" if index == 1 else "held-on-retry"
    return "lost"


def split_frontmatter(text):
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", text
    line_end = text.find("\n", end + 1)
    if line_end < 0:
        return text, ""
    return text[:line_end + 1], text[line_end + 1:]


def read_keep_newlines(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"), newline


def write_keep_newlines(path, text, newline):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("utf-8"))


def skill_parts(skill_dir):
    files = [path for path in skill_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".sh"}]
    files.sort(key=lambda path: (path.name != "SKILL.md", path.relative_to(skill_dir).as_posix()))
    parts = []
    for path in files:
        text, _ = read_keep_newlines(path)
        relative = path.relative_to(skill_dir.parent.parent).as_posix()
        if path.name == "SKILL.md" and path.parent == skill_dir:
            parts.append((path, relative, split_frontmatter(text)[1], text))
        else:
            parts.append((path, relative, text, text))
    return parts


def skill_bundle(skill_dir):
    chunks = [f"<!-- {relative} -->\n{body.strip()}\n" for _, relative, body, _ in skill_parts(skill_dir)]
    return "\n".join(chunks).strip() + "\n"


def disk_chars(skill_dir):
    return sum(len(read_keep_newlines(path)[0]) for path, _, _, _ in skill_parts(skill_dir))


def paragraph_blocks(text):
    pieces = re.split(r"(\n[ \t]*\n)", text)
    return [(pieces[index], pieces[index + 1] if index + 1 < len(pieces) else "") for index in range(0, len(pieces), 2)]


def paragraphs_of(directory):
    result = {}
    for _, source, body, _ in skill_parts(directory):
        for paragraph, _ in paragraph_blocks(body):
            if paragraph.strip():
                result[digest(source, paragraph)] = (source, paragraph)
    return result


def claim_anchor(claim):
    source = re.split(r"(?<=\.md):|(?<=\.sh):", claim["source"], maxsplit=1)[0]
    return source, normalize_ws(claim["span"])


def claim_blocks(claim, paragraphs):
    span = normalize_ws(claim["span"])
    by_path = defaultdict(list)
    for key, (path, paragraph) in paragraphs.items():
        by_path[path].append((key, normalize_ws(paragraph)))
    matches = {}
    for path, pieces in by_path.items():
        body = " ".join(text for _, text in pieces)
        ranges = [(match.start(), match.end()) for match in re.finditer(re.escape(span), body)]
        start = 0
        for key, text in pieces:
            end = start + len(text)
            if any(left < end and start < right for left, right in ranges):
                matches.setdefault(path, []).append(key)
            start = end + 1
    if not matches:
        raise ValueError(f"claim {claim.get('id')} span matches no paragraph")
    declared, _ = claim_anchor(claim)
    return sorted(matches.get(declared) or [key for group in matches.values() for key in group])


def forbidden_punctuation(text):
    if "—" in text:
        return True
    fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = not fence
            continue
        if not fence and ";" in re.sub(r"`[^`]*`", "", line):
            return True
    return False


def rewrite_request(block, rows):
    keep = [row["span"] for row in rows if row["decision"] == "keep" and row.get("span")]
    lines = [
        "Edit the paragraph. Return only the edited paragraph.",
        "Do not add a semicolon or an em dash.",
        "Do not add a step the paragraph did not already contain.",
    ]
    if keep:
        lines.append("These spans must remain verbatim:")
        lines.extend(keep)
    for row in rows:
        if row["decision"] == "keep":
            continue
        lines.append(
            f"Decision {row['decision']} on this span: {row.get('span', '')}\n"
            f"Lenient was {row.get('bucket_lenient')} ({row.get('with_lenient_reason', '')}). "
            f"Strict was {row.get('bucket_strict')} ({row.get('with_strict_reason', '')})."
        )
        if row["decision"] == "cut":
            lines.append("Remove that span. The model already does it without being told.")
        elif row["decision"] == "fix":
            lines.append("Rewrite that span so it no longer pulls the model off the behavior it already had. Keep any taught detail.")
        else:
            lines.append("Rewrite that span so the behavior is explicit enough that an agent following the paragraph will do it.")
    lines.append("Paragraph:")
    lines.append(block)

    def accept(result):
        edited = "" if result.strip() == "[[DROP_PARAGRAPH]]" else strip_fence(result)
        if forbidden_punctuation(edited):
            raise ValueError("the edit added an em dash or a prose semicolon")
        for span in keep:
            if span not in edited and normalize_ws(span) not in normalize_ws(edited):
                raise ValueError(f"the edit dropped a span that must stay verbatim: {span}")
        return edited

    return "You edit one paragraph of an agent skill." + REWRITE_GUARD, "\n".join(lines), accept


def arm_prompt(question, bundle):
    if bundle is None:
        return f"Task:\n{question}{ANSWER_FOOTER}"
    return (
        "Follow the skill below whenever it applies to the task.\n\n"
        f"<skill>\n{bundle}</skill>\n\nTask:\n{question}{ANSWER_FOOTER}"
    )


def judge_prompt(claim, answer):
    clipped = answer if len(answer) <= 12000 else answer[:12000] + "\n[truncated]"
    return (
        f"Kind: {claim['kind']}\n"
        "Grade the reply against the expected behavior. The reply's author was not shown the expected behavior.\n"
        "The author had no tools and was told to name each tool call it would make instead of making it. "
        "Count a named tool call or a step the reply commits to as done. "
        "Never fail a reply because nothing actually ran or no file was written.\n"
        "Lenient checks the general idea. Strict checks the specific names, counts, order, and values.\n"
        "For a process claim, the behavior has to be an action the agent commits to for this task. "
        "Naming it as advice, a definition, or an optional aside is a fail on both grades.\n"
        "For a fact claim, a paraphrase that keeps the meaning can pass lenient. "
        "Strict fails when a named detail is missing. Extra correct detail is fine.\n"
        "Reasons are one sentence each, with no newline.\n"
        "Return JSON of this shape and nothing else: "
        '{"lenient":"pass","strict":"fail","lenient_reason":"...","strict_reason":"..."}\n\n'
        f"User task:\n{claim['question']}\n\n"
        f"Expected behavior:\n{claim['expected']}\n\n"
        f"Agent reply:\n{clipped}\n"
    )


def task_judge_prompt(task, answer):
    checks = "\n".join(f"{index}. {check}" for index, check in enumerate(task["checks"], start=1))
    return (
        "Grade the agent reply against each numbered check. A check passes only when the reply commits to it for this task. "
        "The author had no tools and named each tool call instead of making it. Count a named call or committed step as done.\n"
        'Return JSON of this shape and nothing else: {"checks":[{"result":"pass","reason":"..."}]}, '
        "with one entry per check in order.\n\n"
        f"User task:\n{task['prompt']}\n\nChecks:\n{checks}\n\nAgent reply:\n{answer[:12000]}\n"
    )


def child_env(home):
    env = {key: value for key, value in os.environ.items()
           if not key.endswith("_API_KEY") and not key.startswith(STRIPPED_ENV)}
    env.update(HOME=str(home), USERPROFILE=str(home), NO_COLOR="1")
    return env


def kill_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
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
            reason = "cancelled" if cancel.is_set() else f"timed out after {timeout}s" if time.monotonic() > deadline else None
            if reason:
                kill_tree(process)
                process.communicate()
                raise CallError(reason)


class Credentials:
    def __init__(self, clis):
        self.lock = threading.Lock()
        self.home = Path.home()
        self.codex_home = Path(os.environ.get("CODEX_HOME") or self.home / ".codex")
        self.grok_home = Path(os.environ.get("GROK_HOME") or self.home / ".grok")
        self.claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or self.home / ".claude")
        self.notes = []
        for cli in clis:
            if not shutil.which(cli):
                raise SystemExit(f"The {cli} CLI is not on PATH. Install it and sign in with its subscription.")
            getattr(self, f"check_{cli}")()

    def claude_oauth(self):
        path = self.claude_home / ".credentials.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")).get("claudeAiOauth") or {}
        if sys.platform == "darwin":
            result = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                                    capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return json.loads(result.stdout).get("claudeAiOauth") or {}
        return {}

    def check_claude(self):
        oauth = self.claude_oauth()
        if not oauth.get("accessToken"):
            raise SystemExit("Claude is not signed in with a subscription. Run claude and sign in with Claude Max.")
        if oauth.get("subscriptionType") != "max":
            raise SystemExit(f"Claude is signed in with {oauth.get('subscriptionType')!r}. Only Claude Max is allowed.")
        self.notes.append("claude: Claude Max OAuth token, passed per call, no API key")

    def check_codex(self):
        auth = read_json(self.codex_home / "auth.json", {})
        if auth.get("auth_mode") != "chatgpt" or auth.get("OPENAI_API_KEY"):
            raise SystemExit("Codex must be signed in with ChatGPT, not an API key. Run codex login.")
        self.notes.append("codex: ChatGPT sign-in copied into each call's temporary home, no API key")

    def check_grok(self):
        auth = read_json(self.grok_home / "auth.json", {})
        modes = {entry.get("auth_mode") for entry in auth.values() if isinstance(entry, dict)}
        if not modes or any("key" in str(mode).lower() for mode in modes):
            raise SystemExit("Grok must be signed in with grok.com, not an API key. Run grok login.")
        self.notes.append("grok: grok.com sign-in copied into each call's temporary home, no API key")

    def claude_token(self):
        with self.lock:
            oauth = self.claude_oauth()
            if oauth.get("expiresAt", 0) / 1000 - time.time() < 300:
                home = Path(tempfile.mkdtemp(prefix="eval-skill-refresh-"))
                try:
                    subprocess.run(
                        ["claude", "-p", "--model", "haiku", "--safe-mode", "--tools", "", "--no-session-persistence",
                         "--disable-slash-commands", "--strict-mcp-config", "Reply OK."],
                        cwd=home, capture_output=True, timeout=120, check=False,
                    )
                finally:
                    shutil.rmtree(home, ignore_errors=True)
                oauth = self.claude_oauth()
            if oauth.get("expiresAt", 0) / 1000 - time.time() < 60:
                raise CallError("the Claude sign-in expired. Run claude once to refresh it")
            return oauth["accessToken"]

    def copy_in(self, source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            data = source.read_bytes()
        target.write_bytes(data)
        return data

    def copy_back(self, source, target, original):
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
            if source.read_bytes() == original:
                temporary = source.with_suffix(".eval-skill.tmp")
                temporary.write_bytes(updated)
                temporary.replace(source)


class Harness:
    def __init__(self, credentials, timeout):
        self.credentials = credentials
        self.timeout = timeout
        self.host_skills = sorted(
            path.as_posix() for root in (Path.home() / ".agents" / "skills", credentials.codex_home / "skills")
            if root.is_dir() for path in root.glob("*/SKILL.md")
        )

    def ask(self, seat, system, prompt, cancel):
        root = Path(tempfile.mkdtemp(prefix="eval-skill-"))
        try:
            work, home = root / "work", root / "home"
            work.mkdir()
            home.mkdir()
            return getattr(self, f"ask_{seat['cli']}")(seat, system, prompt, root, work, home, cancel)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def ask_claude(self, seat, system, prompt, root, work, home, cancel):
        env = child_env(home)
        env.update(CLAUDE_CONFIG_DIR=str(home / ".claude"), CLAUDE_CODE_OAUTH_TOKEN=self.credentials.claude_token())
        command = [
            "claude", "-p", "--model", seat["model"], "--effort", seat["effort"], "--safe-mode", "--tools", "",
            "--disable-slash-commands", "--strict-mcp-config", "--no-session-persistence",
            "--system-prompt", system, "--output-format", "json",
        ]
        code, out, err = run_process(command, work, env, prompt, self.timeout, cancel)
        try:
            data = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise CallError(f"claude exited {code}: {(err or out)[-400:]}")
        if data.get("is_error") or code:
            raise CallError(f"claude error: {str(data.get('result') or err)[-400:]}")
        return data.get("result", ""), sorted(data.get("modelUsage") or {})

    def ask_codex(self, seat, system, prompt, root, work, home, cancel):
        codex_home = home / ".codex"
        original = self.credentials.copy_in(self.credentials.codex_home / "auth.json", codex_home / "auth.json")
        instructions = root / "instructions.md"
        instructions.write_text(system, encoding="utf-8")
        lines = [
            f"model_instructions_file = '{instructions.as_posix()}'",
            'web_search = "disabled"',
            "[features]",
            *[f"{feature} = false" for feature in CODEX_FEATURES_OFF],
            "[agents]",
            "enabled = false",
            "[skills]",
            "include_instructions = false",
        ]
        for path in self.host_skills:
            lines += ["[[skills.config]]", f"path = '{path}'", "enabled = false"]
        (codex_home / "config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        env = child_env(home)
        env["CODEX_HOME"] = str(codex_home)
        output = root / "last.txt"
        command = [
            "codex", "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-rules", "-s", "read-only",
            "-m", seat["model"], "-c", f'model_reasoning_effort="{seat["effort"]}"',
            "--color", "never", "--json", "-o", str(output), "-",
        ]
        try:
            code, out, err = run_process(command, work, env, prompt, self.timeout, cancel)
        finally:
            self.credentials.copy_back(self.credentials.codex_home / "auth.json", codex_home / "auth.json", original)
        if code:
            raise CallError(f"codex exited {code}: {err[-400:]}")
        tools = []
        for line in out.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") not in ("agent_message", "reasoning", "error", None):
                tools.append(item.get("type"))
        if tools:
            raise CallError(f"codex used tools {sorted(set(tools))}")
        return (output.read_text(encoding="utf-8") if output.is_file() else ""), [seat["model"]]

    def ask_grok(self, seat, system, prompt, root, work, home, cancel):
        grok_home = home / ".grok"
        original = self.credentials.copy_in(self.credentials.grok_home / "auth.json", grok_home / "auth.json")
        ignore = [(grok_home / "bundled" / name).as_posix() for name in ("skills", "workflows")]
        ignore += ["~/.claude/skills", "~/.agents/skills", "~/.grok/skills"]
        (grok_home / "config.toml").write_text("[skills]\nignore = " + json.dumps(ignore) + "\n", encoding="utf-8")
        prompt_file = root / "prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        env = child_env(home)
        env["GROK_HOME"] = str(grok_home)
        command = [
            "grok", "-m", seat["model"], "--effort", seat["effort"], "--system-prompt-override", system,
            "--disallowed-tools", GROK_DISALLOWED, "--no-subagents", "--no-plan", "--disable-web-search",
            "--max-turns", "2", "--verbatim", "--output-format", "json", "--prompt-file", str(prompt_file),
        ]
        try:
            code, out, err = run_process(command, work, env, None, self.timeout, cancel)
        finally:
            self.credentials.copy_back(self.credentials.grok_home / "auth.json", grok_home / "auth.json", original)
        try:
            data = json.loads(out[out.find("{"):])
        except ValueError:
            raise CallError(f"grok exited {code}: {(err or out)[-400:]}")
        if code or data.get("stopReason") not in (None, "end_turn", "stop", "completed"):
            raise CallError(f"grok stopped with {data.get('stopReason')}: {err[-300:]}")
        return data.get("text", ""), sorted(data.get("modelUsage") or {})


class Models:
    def __init__(self, harness, parallel, hedge):
        self.harness = harness
        self.hedge = hedge
        self.slots = {family: threading.Semaphore(parallel) for family in FAMILIES}
        self.records = []
        self.durations = defaultdict(list)
        self.lock = threading.Lock()

    def hedge_after(self, kind, seat):
        with self.lock:
            seen = list(self.durations[(kind.split("-")[0], seat_key(seat))])
        if len(seen) < 3:
            return self.hedge
        return min(self.hedge, max(15.0, 2 * statistics.median(seen)))

    def race(self, seat, system, prompt, kind, record):
        results = queue.Queue()
        cancels = []

        def worker(cancel, extra):
            try:
                results.put((True, self.harness.ask(seat, system, prompt, cancel)))
            except Exception as error:
                results.put((False, error if isinstance(error, CallError) else CallError(repr(error))))
            finally:
                if extra:
                    self.slots[seat["cli"]].release()

        def launch(extra):
            cancel = threading.Event()
            cancels.append(cancel)
            threading.Thread(target=worker, args=(cancel, extra), daemon=True).start()

        launch(False)
        running = 1
        try:
            try:
                ok, value = results.get(timeout=self.hedge_after(kind, seat))
            except queue.Empty:
                if self.slots[seat["cli"]].acquire(blocking=False):
                    launch(True)
                    running += 1
                    record["hedged"] = True
                ok, value = results.get()
            running -= 1
            while not ok and running:
                ok, value = results.get()
                running -= 1
            if not ok:
                raise value
            return value
        finally:
            for cancel in cancels:
                cancel.set()

    def call(self, seat, system, prompt, parse, kind, skill, attempts=3, repair=True):
        errors = []
        current = prompt
        for attempt in range(1, attempts + 1):
            queued = time.monotonic()
            with self.slots[seat["cli"]]:
                started = time.monotonic()
                record = {"skill": skill, "kind": kind, "seat": seat_key(seat), "attempt": attempt,
                          "queued_at": queued, "started_at": started}
                try:
                    text, models = self.race(seat, system, current, kind, record)
                    record["models"] = models
                    value = parse(text)
                    record["ok"] = True
                    with self.lock:
                        self.durations[(kind.split("-")[0], seat_key(seat))].append(time.monotonic() - started)
                    return value
                except (CallError, ValueError, KeyError, TypeError) as error:
                    record["ok"] = False
                    record["error"] = str(error)[:300]
                    errors.append(str(error))
                    if repair and isinstance(error, (ValueError, KeyError, TypeError)):
                        current = (
                            f"{prompt}\n\nA previous reply to this request was rejected: {str(error)[:1500]}\n"
                            "Reply again in full and fix that."
                        )
                finally:
                    record["ended_at"] = time.monotonic()
                    with self.lock:
                        self.records.append(record)
        raise CallError(f"{kind} on {seat_key(seat)} failed {attempts} times: {errors[-1][:300]}")


class Cache:
    def __init__(self, directory):
        self.directory = directory
        self.locks = defaultdict(threading.Lock)
        self.guard = threading.Lock()
        self.hits = Counter()

    def get(self, kind, key, compute):
        path = self.directory / kind / key[:2] / f"{key}.json"
        with self.guard:
            lock = self.locks[path]
        with lock:
            existing = read_json(path)
            if existing is not None:
                with self.guard:
                    self.hits[kind] += 1
                return existing["value"], True
            value = compute()
            save_json(path, {"value": value, "saved_at": now_iso()})
            return value, False


class Steps:
    def __init__(self, origin):
        self.origin = origin
        self.data = {}
        self.lock = threading.Lock()

    def start(self, name):
        with self.lock:
            self.data.setdefault(name, {"start": round(time.monotonic() - self.origin, 2)})

    def end(self, name):
        with self.lock:
            entry = self.data.setdefault(name, {"start": round(time.monotonic() - self.origin, 2)})
            entry["end"] = round(time.monotonic() - self.origin, 2)
            entry["seconds"] = round(entry["end"] - entry["start"], 2)


class Panel:
    def __init__(self, args):
        if args.model:
            seat = parse_seat(args.model)
            raw = {"answerers": [seat_key(seat)], "judges": {seat["cli"]: seat_key(seat)},
                   "drafter": seat_key(seat), "implementer": seat_key(seat)}
        elif args.panel:
            raw = read_json(args.panel)
            if raw is None:
                raise SystemExit(f"Panel file {args.panel} does not exist")
        else:
            raw = DEFAULT_PANEL
        self.answerers = [parse_seat(text) for text in raw["answerers"]]
        families = [seat["cli"] for seat in self.answerers]
        if not families or len(families) != len(set(families)):
            raise SystemExit("Give one or more answerers, at most one per CLI")
        self.judges = {family: parse_seat(text) for family, text in raw.get("judges", {}).items()}
        self.drafter = parse_seat(raw.get("drafter") or raw["answerers"][0])
        self.implementer = parse_seat(raw.get("implementer") or seat_key(self.drafter))
        roles = [*self.answerers, *self.judges.values(), self.drafter, self.implementer]
        self.single = len({seat_key(seat) for seat in roles}) == 1
        for family in families:
            judge = self.judges.get(family)
            if judge is None:
                raise SystemExit(f"Give a judge for {family} answers")
            if judge["cli"] == family and not self.single:
                raise SystemExit(
                    f"The judge for {family} answers is also {family}. Pick another family, "
                    "or pick one model for every role with --model"
                )
        self.clis = sorted({seat["cli"] for seat in roles})
        self.note = (
            f"Single-model panel: every role used {seat_key(self.drafter)} because one model was picked for every role. "
            "Each answer was judged by the model that gave it."
        ) if self.single else None

    def judges_for(self, answerer):
        if self.single:
            return [self.answerers[0]]
        primary = self.judges[answerer["cli"]]
        others = [seat for seat in [*self.judges.values(), *self.answerers, self.drafter, self.implementer]
                  if seat["cli"] != answerer["cli"]]
        ordered, seen = [], set()
        for seat in [primary, *others]:
            if seat_key(seat) not in seen:
                seen.add(seat_key(seat))
                ordered.append(seat)
        return ordered

    def describe(self):
        return {
            "answerers": [seat_key(seat) for seat in self.answerers],
            "judges": {family: seat_key(seat) for family, seat in self.judges.items()},
            "drafter": seat_key(self.drafter),
            "implementer": seat_key(self.implementer),
            "single_model_panel": self.single,
        }


class SkillRun:
    def __init__(self, context, name):
        self.context = context
        self.name = name
        self.models = context.models
        self.cache = context.cache
        self.panel = context.panel
        self.args = context.args
        self.steps = Steps(context.origin)
        self.state = context.state / "skills" / name
        self.output = context.run_dir / name
        self.before = self.output / "before" / "skills" / name
        self.candidate = self.output / "repo" / "skills" / name
        self.marker = "isomark" + secrets.token_hex(4)
        self.claims_lock = threading.Lock()
        self.dropped = 0

    def bundle(self, directory):
        return f"Isolation marker: {self.marker}\n\n{skill_bundle(directory)}"

    def run(self):
        shutil.copytree(self.context.root / "skills" / self.name, self.candidate)
        shutil.copytree(self.candidate, self.before)
        markers = read_json(self.state / "markers.json", [])
        markers.append(self.marker)
        save_json(self.state / "markers.json", markers)
        self.markers = markers
        self.base_bundle = self.bundle(self.before)
        canaries = {seat_key(seat): [self.context.arms.submit(self.canary, seat, arm) for arm in ("without", "with")]
                    for seat in self.panel.answerers}
        claims, futures, reused = self.draft_and_score()
        rows = self.collect(claims, futures)
        isolation = self.isolation(rows, canaries)
        summary = self.summarize(claims, rows, reused, isolation)
        if self.args.score_only:
            pass
        elif summary["unscored"] or not isolation["passed"]:
            summary["proposal"] = {"status": "none", "reason": "the run has unscored claims or failed isolation"}
        else:
            self.propose(rows, summary)
        save_json(self.output / "summary.json", summary)
        return summary

    def canary(self, seat, arm):
        self.steps.start("isolation canary")
        bundle = self.base_bundle if arm == "with" else None

        def parse(text):
            if arm == "with" and self.marker.lower() not in text.lower():
                raise CallError("the with-skill arm did not echo the marker")
            return text

        try:
            text = self.models.call(seat, TASK_SYSTEM, arm_prompt(CANARY_QUESTION, bundle), parse,
                                    "canary", self.name, repair=False)
            return {"seat": seat_key(seat), "arm": arm, "answer": text[:300], "ok": True}
        except CallError as error:
            return {"seat": seat_key(seat), "arm": arm, "error": str(error), "ok": False}
        finally:
            self.steps.end("isolation canary")

    def draft_and_score(self):
        manifest_path = self.state / f"claims-{digest(DRAFT_SYSTEM, seat_key(self.panel.drafter))[:12]}.json"
        previous = read_json(manifest_path, {"blocks": [], "claims": [], "next": 0})
        paragraphs = paragraphs_of(self.before)
        unchanged = set(previous["blocks"]) & paragraphs.keys()
        claims = [claim for claim in previous["claims"] if set(claim["_blocks"]) <= unchanged]
        reused = len(claims)
        retained = {claim["id"] for claim in claims}
        prior = {claim_anchor(row): row for row in previous["claims"] if row["id"] not in retained}
        self.next_id = previous["next"]
        futures = {claim["id"]: self.context.claims.submit(self.score_claim, claim) for claim in claims}
        changed = defaultdict(list)
        for key, (source, paragraph) in paragraphs.items():
            if key not in unchanged:
                changed[source].append(paragraph)
        budget = max(1, self.args.max_claims - len(claims))
        total = sum(len("\n\n".join(items)) for items in changed.values()) or 1
        self.steps.start("draft")
        drafts = []
        for source, items in changed.items():
            text = f"<!-- {source} -->\n" + "\n\n".join(items)
            limit = max(1, int(budget * len(text) / total)) if len(changed) > 1 else budget
            drafts.append(self.context.arms.submit(self.draft, text, limit, paragraphs, bool(claims)))
        for future in as_completed(drafts):
            for claim in future.result():
                with self.claims_lock:
                    old = prior.pop(claim_anchor(claim), None)
                    if old and old["kind"] == claim["kind"]:
                        claim.update(id=old["id"], question=old["question"], expected=old["expected"])
                    else:
                        claim["id"] = str(self.next_id)
                        self.next_id += 1
                claims.append(claim)
                futures[claim["id"]] = self.context.claims.submit(self.score_claim, claim)
        self.steps.end("draft")
        if not claims:
            raise SystemExit(f"{self.name}: no claims were drafted")
        save_json(manifest_path, {"blocks": list(paragraphs), "claims": claims, "next": self.next_id})
        self.paragraphs = paragraphs
        log(f"{self.name}: {len(claims)} claims, {reused} reused from unchanged paragraphs")
        return claims, futures, reused

    def draft(self, text, limit, paragraphs, allow_empty):
        prompt = f"Skill name: {self.name}\nReturn at most {limit} claims.\n\n{text}"
        salvage = []

        def parse(reply):
            drafted = extract_json_array(reply)
            errors = validate_claims(drafted, text, limit, self.name, allow_empty)
            if errors:
                valid = []
                for claim in drafted:
                    if isinstance(claim, dict) and not validate_claims([claim], text, limit, self.name):
                        try:
                            valid.append(dict(claim, _blocks=claim_blocks(claim, paragraphs)))
                        except ValueError:
                            pass
                salvage[:] = [valid[:limit], len(drafted) - len(valid[:limit])]
                raise ValueError("; ".join(errors[:12]))
            return [dict(claim, _blocks=claim_blocks(claim, paragraphs)) for claim in drafted]

        try:
            return self.models.call(self.panel.drafter, DRAFT_SYSTEM, prompt, parse, "draft", self.name)
        except CallError as error:
            if not salvage or not salvage[0]:
                raise
            log(f"{self.name}: kept {len(salvage[0])} valid claims and dropped {salvage[1]} after {error}")
            with self.claims_lock:
                self.dropped += salvage[1]
            return salvage[0]

    def route_path(self, claim):
        return self.state / "routes" / f"{digest(claim['id'], claim['_blocks'])}.json"

    def score_claim(self, claim):
        self.steps.start("score")
        answerers = self.panel.answerers
        start = read_json(self.route_path(claim), 0)
        errors = []
        try:
            for step in range(len(answerers)):
                offset = (start + step) % len(answerers)
                answerer = answerers[(int(claim["id"]) + offset) % len(answerers)]
                arms = [self.context.arms.submit(self.score_arm, claim, arm, answerer,
                                                 self.base_bundle if arm == "with" else None, claim["_blocks"])
                        for arm in ("without", "with")]
                try:
                    without, with_skill = [future.result() for future in arms]
                except CallError as error:
                    errors.append(str(error))
                    log(f"{self.name}: claim {claim['id']} moves off {seat_key(answerer)}: {error}")
                    continue
                save_json(self.route_path(claim), offset)
                return self.classify(claim, without, with_skill, answerer, offset != start)
            return {"id": claim["id"], "kind": claim["kind"], "decision": "unscored", "errors": errors}
        finally:
            self.steps.end("score")

    def score_arm(self, claim, arm, answerer, bundle, context):
        prompt = arm_prompt(claim["question"], bundle)
        key = digest("answer", PROTOCOL, seat_key(answerer), TASK_SYSTEM, arm_prompt(claim["question"], None),
                     None if bundle is None else context)
        answer, cached = self.cache.get("without" if bundle is None else "with", key, lambda: self.models.call(
            answerer, TASK_SYSTEM, prompt, nonempty, f"answer-{arm}", self.name))
        judged = judge_prompt(claim, answer)
        errors = []
        for judge in self.panel.judges_for(answerer):
            try:
                grade, _ = self.cache.get("grades", digest("grade", PROTOCOL, seat_key(judge), JUDGE_SYSTEM, judged), lambda: self.models.call(
                    judge, JUDGE_SYSTEM, judged, parse_grade, "judge", self.name))
                return {"arm": arm, "answer": answer, "cached": cached, "answerer": seat_key(answerer),
                        "judge": seat_key(judge), **grade}
            except CallError as error:
                errors.append(str(error))
        raise CallError(f"no judge could grade claim {claim['id']}: {errors[-1]}")

    def classify(self, claim, without, with_skill, answerer, moved):
        row = {key: claim.get(key, "") for key in ("id", "kind", "source", "span", "question", "expected")}
        row["_blocks"] = claim["_blocks"]
        row["answerer"] = seat_key(answerer)
        row["judges"] = sorted({without["judge"], with_skill["judge"]})
        row["moved_answerer"] = moved
        row["bucket_lenient"] = bucket(without["lenient"] == "pass", with_skill["lenient"] == "pass")
        row["bucket_strict"] = bucket(without["strict"] == "pass", with_skill["strict"] == "pass")
        decision = DECISIONS[(row["bucket_lenient"], row["bucket_strict"])]
        row["decision"] = "keep" if claim["kind"] == "process" and decision == "cut" else decision
        for arm, result in (("without", without), ("with", with_skill)):
            row[f"{arm}_answer"] = result["answer"]
            row[f"{arm}_cached"] = result["cached"]
            for scale in ("lenient", "strict"):
                row[f"{arm}_{scale}"] = result[scale]
                row[f"{arm}_{scale}_reason"] = result[f"{scale}_reason"]
        return row

    def collect(self, claims, futures):
        pending = defaultdict(set)
        for claim in claims:
            for block in claim["_blocks"]:
                pending[block].add(claim["id"])
        rows = {}
        self.rewrites = {}
        for future in as_completed(list(futures.values())):
            row = future.result()
            rows[row["id"]] = row
            if self.args.score_only:
                continue
            for block in [block for block, ids in pending.items() if row["id"] in ids]:
                pending[block].discard(row["id"])
                if not pending[block]:
                    matched = [rows[identifier] for identifier in sorted(
                        {claim["id"] for claim in claims if block in claim["_blocks"]}, key=int)]
                    if all(item["decision"] != "unscored" for item in matched) and any(
                            item["decision"] != "keep" for item in matched):
                        self.rewrites[block] = self.context.arms.submit(self.rewrite, block, matched)
        log(f"{self.name}: scored {len(rows)} claims")
        return [rows[claim["id"]] for claim in sorted(claims, key=lambda claim: int(claim["id"]))]

    def isolation(self, rows, canaries):
        hits = []
        without = [row for row in rows if "without_answer" in row]
        for row in without:
            text = row["without_answer"]
            for marker in self.markers:
                if marker.lower() in text.lower():
                    hits.append({"claim": row["id"], "found": marker})
            for found in name_hits(text, self.name):
                hits.append({"claim": row["id"], "found": found})
        results = {seat: [future.result() for future in pair] for seat, pair in canaries.items()}
        problems = []
        for seat, pair in results.items():
            for result in pair:
                if not result["ok"]:
                    problems.append(f"{seat} {result['arm']} canary failed: {result['error']}")
                elif result["arm"] == "without" and (
                        any(marker.lower() in result["answer"].lower() for marker in self.markers)):
                    problems.append(f"{seat} without-skill canary returned the marker")
        problems += [f"claim {hit['claim']} without-skill answer contains {hit['found']!r}" for hit in hits]
        return {
            "marker": self.marker,
            "markers_checked": len(self.markers),
            "without_answers_checked": len(without),
            "canary": {seat: {result["arm"]: result.get("answer", result.get("error", ""))[:120] for result in pair}
                       for seat, pair in results.items()},
            "passed": not problems,
            "problems": problems,
        }

    def summarize(self, claims, rows, reused, isolation):
        scored = [row for row in rows if row["decision"] != "unscored"]
        counts = {scale: {name: sum(1 for row in scored if row[f"bucket_{scale}"] == name) for name in BUCKETS}
                  for scale in ("lenient", "strict")}
        for scale, values in counts.items():
            if sum(values.values()) != len(scored):
                raise RuntimeError(f"{self.name}: {scale} buckets do not sum to the scored claims")
        by_answerer = defaultdict(list)
        for row in scored:
            by_answerer[row["answerer"]].append(row)
        write_jsonl(self.output / "claims.jsonl", rows)
        return {
            "skill": self.name,
            "claims": len(claims),
            "reused_claims": reused,
            "dropped_claims": self.dropped,
            "scored": len(scored),
            "unscored": [row["id"] for row in rows if row["decision"] == "unscored"],
            "moved_answerer": [row["id"] for row in scored if row["moved_answerer"]],
            "buckets": counts,
            "buckets_by_answerer": {
                seat: {scale: dict(Counter(row[f"bucket_{scale}"] for row in items)) for scale in ("lenient", "strict")}
                for seat, items in by_answerer.items()
            },
            "decisions": dict(Counter(row["decision"] for row in rows)),
            "isolation": isolation,
            "rows": [{key: row.get(key) for key in (
                "id", "kind", "source", "span", "answerer", "judges", "bucket_lenient", "bucket_strict", "decision",
                "without_cached", "with_cached")} for row in rows],
            "steps": self.steps.data,
        }

    def rewrite(self, block, rows):
        self.steps.start("rewrite")
        try:
            source, paragraph = self.paragraphs[block]
            if all(row["decision"] == "cut" for row in rows) and any(
                    normalize_ws(row["span"]) == normalize_ws(paragraph) for row in rows):
                return ""
            system, prompt, accept = rewrite_request(paragraph, rows)
            key = digest("rewrite", PROTOCOL, seat_key(self.panel.implementer), system, prompt)
            try:
                edited, _ = self.cache.get("rewrites", key, lambda: self.models.call(
                    self.panel.implementer, system, prompt, accept, "rewrite", self.name))
                return edited
            except CallError as error:
                log(f"{self.name}: kept a paragraph of {source} unchanged because the rewrite failed: {error}")
                return paragraph
        finally:
            self.steps.end("rewrite")

    def apply_rewrites(self):
        edited = {block: future.result() for block, future in self.rewrites.items()}
        for path, source, body, full in skill_parts(self.candidate):
            front = full[:-len(body)] if body and body != full else ""
            pieces = []
            for paragraph, separator in paragraph_blocks(body):
                replacement = edited.get(digest(source, paragraph), paragraph) if paragraph.strip() else paragraph
                if replacement and replacement != paragraph:
                    replacement = replacement.strip() + paragraph[len(paragraph.rstrip()):]
                pieces.append(replacement + separator if replacement or not paragraph else "")
            text = front + "".join(pieces)
            if text.strip() and text != full:
                write_keep_newlines(path, text, read_keep_newlines(path)[1])

    def run_checks(self):
        failures = []
        for check in ("no-em-dashes.py", "no-semicolons.py", "use-when-descriptions.py"):
            script = self.context.root / "scripts" / check
            if script.is_file():
                result = subprocess.run([sys.executable, str(script), str(self.candidate)],
                                        capture_output=True, text=True, check=False)
                if result.returncode:
                    failures.append(f"{check}: {result.stdout.strip()[-400:]}")
        return failures

    def validate(self, rows):
        bundle = self.bundle(self.candidate)
        version = digest(skill_bundle(self.candidate))
        answerers = {seat_key(seat): seat for seat in self.panel.answerers}

        def check(row):
            grades = []
            for attempt in (1, 2):
                result = self.score_arm(row, "with", answerers[row["answerer"]], bundle, [version, attempt])
                grades.append(result)
                if held_status(row, grades) != "lost":
                    break
            return {"id": row["id"], "scales": taught_scales(row), "status": held_status(row, grades)}

        taught = [row for row in rows if taught_scales(row)]
        return list(self.context.claims.map(check, taught))

    def run_tasks(self):
        path = Path(self.args.tasks) / f"{self.name}.json" if self.args.tasks else None
        if not path or not path.is_file():
            return {"status": "not run", "reason": f"no task file at {path}" if path else "no --tasks directory"}
        tasks = read_json(path)
        versions = {"original": skill_bundle(self.before), "candidate": skill_bundle(self.candidate)}

        def run_one(task, seat, version):
            prompt = arm_prompt(task["prompt"], versions[version])
            key = digest("task", PROTOCOL, seat_key(seat), TASK_SYSTEM, task, versions[version])
            answer, _ = self.cache.get("tasks", key, lambda: self.models.call(
                seat, TASK_SYSTEM, prompt, nonempty, "task", self.name))
            judge = self.panel.judges_for(seat)[0]
            judged = task_judge_prompt(task, answer)
            checks, _ = self.cache.get("grades", digest("checks", PROTOCOL, seat_key(judge), JUDGE_SYSTEM, judged), lambda: self.models.call(
                judge, JUDGE_SYSTEM, judged, parse_checks(len(task["checks"])), "task-judge", self.name))
            return task["id"], seat_key(seat), version, checks

        jobs = [(task, seat, version) for task in tasks for seat in self.panel.answerers for version in versions]
        results = {}
        for task_id, seat, version, checks in self.context.claims.map(lambda job: run_one(*job), jobs):
            results[(task_id, seat, version)] = checks
        regressions = []
        for task in tasks:
            for seat in self.panel.answerers:
                before = results[(task["id"], seat_key(seat), "original")]
                after = results[(task["id"], seat_key(seat), "candidate")]
                for index, (old, new) in enumerate(zip(before, after), start=1):
                    if old["result"] == "pass" and new["result"] == "fail":
                        regressions.append({"task": task["id"], "seat": seat_key(seat), "check": index,
                                            "reason": new["reason"]})
        return {"status": "passed" if not regressions else "regressed", "tasks": len(tasks),
                "regressions": regressions}

    def propose(self, rows, summary):
        self.steps.start("rewrite")
        self.apply_rewrites()
        self.steps.end("rewrite")
        before, after = disk_chars(self.before), disk_chars(self.candidate)
        summary.update(before_chars=before, proposed_chars=after)
        if after >= before:
            summary["proposal"] = {"status": "none", "reason": "the rewrite did not make the skill shorter"}
            return
        self.steps.start("checks")
        failures = self.run_checks()
        self.steps.end("checks")
        if failures:
            summary["proposal"] = {"status": "rejected", "reason": "repo checks failed", "failures": failures}
            return
        self.steps.start("validate")
        kept = self.validate(rows)
        self.steps.end("validate")
        write_jsonl(self.output / "kept.jsonl", kept)
        lost = [item["id"] for item in kept if item["status"] == "lost"]
        summary.update(checked_taught=len(kept), lost_taught=lost)
        if lost:
            summary["proposal"] = {"status": "rejected", "reason": "the shorter skill lost taught claims", "lost": lost}
            return
        self.steps.start("tasks")
        tasks = self.run_tasks()
        self.steps.end("tasks")
        diff = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", f"before/skills/{self.name}", f"repo/skills/{self.name}"],
            cwd=self.output, capture_output=True, check=False,
        )
        patch = self.output / "candidate.patch"
        patch.write_bytes(diff.stdout)
        status = "rejected" if tasks["status"] == "regressed" else "proposed"
        summary["proposal"] = {"status": status, "patch": str(patch), "task_evals": tasks}


class Context:
    def __init__(self, args):
        self.args = args
        self.origin = time.monotonic()
        self.root = args.root.resolve()
        self.panel = Panel(args)
        self.credentials = Credentials(self.panel.clis)
        self.models = Models(Harness(self.credentials, args.timeout), args.parallel, args.hedge)
        self.state = args.state.expanduser().resolve() / f"v{PROTOCOL}"
        self.cache = Cache(self.state / "cache")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = self.state / "runs" / f"{stamp}-{secrets.token_hex(2)}"
        self.run_dir.mkdir(parents=True)
        width = args.parallel * len(FAMILIES)
        self.arms = ThreadPoolExecutor(max_workers=max(64, width * 8), thread_name_prefix="arm")
        self.claims = ThreadPoolExecutor(max_workers=max(32, width * 4), thread_name_prefix="claim")


def call_stats(records, origin):
    groups = defaultdict(list)
    for record in records:
        groups[(record["kind"], record["seat"])].append(record)
    rows = []
    for (kind, seat), items in sorted(groups.items()):
        seconds = sorted(item["ended_at"] - item["started_at"] for item in items)
        waits = [item["started_at"] - item["queued_at"] for item in items]
        rows.append({
            "kind": kind, "seat": seat, "calls": len(items), "failed": sum(1 for item in items if not item["ok"]),
            "hedged": sum(1 for item in items if item.get("hedged")),
            "p50": round(statistics.median(seconds), 1),
            "p90": round(seconds[min(len(seconds) - 1, int(len(seconds) * 0.9))], 1),
            "max": round(seconds[-1], 1), "mean_slot_wait": round(statistics.mean(waits), 1),
            "models": sorted({model for item in items for model in item.get("models", [])}),
        })
    return rows


def render_report(result):
    lines = [
        f"# Novelty run {result['run']}",
        "",
        f"Wall time {result['wall_seconds']}s. Panel: answerers {', '.join(result['panel']['answerers'])}. "
        f"Judges {', '.join(f'{family} answers by {seat}' for family, seat in result['panel']['judges'].items())}. "
        f"Drafter {result['panel']['drafter']}. Implementer {result['panel']['implementer']}.",
    ]
    if result.get("panel_note"):
        lines += ["", result["panel_note"]]
    lines += ["", "Billing: " + ". ".join(result["billing"]) + "."]
    for summary in result["skills"]:
        isolation = summary["isolation"]
        lines += [
            "", f"## {summary['skill']}", "",
            f"Claims {summary['claims']} ({summary['reused_claims']} reused, {summary['dropped_claims']} invalid drafts dropped). "
            f"Unscored {len(summary['unscored'])}.",
            f"Isolation {'passed' if isolation['passed'] else 'FAILED'}: marker {isolation['marker']} absent from "
            f"{isolation['without_answers_checked']} without-skill answers, checked against {isolation['markers_checked']} "
            "markers and the skill name. "
            + " ".join(f"{seat} echoed {pair.get('with', '')[:40]!r} with the skill and {pair.get('without', '')[:40]!r} without."
                       for seat, pair in isolation["canary"].items()),
        ]
        lines += [f"- {problem}" for problem in isolation["problems"]]
        lines += ["", "| Grade | already known | hurts | teaches | fails both |", "|---|---|---|---|---|"]
        for scale in ("lenient", "strict"):
            values = summary["buckets"][scale]
            lines.append(f"| {scale} | " + " | ".join(str(values[name]) for name in BUCKETS) + " |")
        lines += ["", "| Claim | Kind | Answerer | Lenient | Strict | Decision | Span |", "|---|---|---|---|---|---|---|"]
        for row in summary["rows"]:
            span = (row.get("span") or "").replace("|", "/").replace("\n", " ")[:90]
            lines.append(f"| {row['id']} | {row['kind']} | {row.get('answerer') or ''} | {row.get('bucket_lenient') or ''} | "
                         f"{row.get('bucket_strict') or ''} | {row['decision']} | {span} |")
        proposal = summary.get("proposal")
        if proposal:
            lines += ["", f"Proposal: {proposal['status']}. {proposal.get('reason', '')} "
                          f"{summary.get('before_chars')} to {summary.get('proposed_chars')} characters."]
            if proposal.get("patch"):
                lines.append(f"Patch: {proposal['patch']}. Task evals: {proposal['task_evals']['status']}.")
        lines += ["", "| Step | Start s | End s | Seconds |", "|---|---|---|---|"]
        for step, entry in summary["steps"].items():
            lines.append(f"| {step} | {entry.get('start')} | {entry.get('end')} | {entry.get('seconds')} |")
    lines += ["", "| Call | Seat | Calls | Failed | Hedged | p50 s | p90 s | Max s | Mean slot wait s |", "|---|---|---|---|---|---|---|---|---|"]
    for row in result["calls"]:
        lines.append(f"| {row['kind']} | {row['seat']} | {row['calls']} | {row['failed']} | {row['hedged']} | {row['p50']} | "
                     f"{row['p90']} | {row['max']} | {row['mean_slot_wait']} |")
    lines.append(f"\nCache hits: {json.dumps(result['cache_hits'])}.")
    return "\n".join(lines) + "\n"


def resolve_skills(args):
    skills_dir = args.root.resolve() / "skills"
    if args.all:
        return sorted(path.parent.name for path in skills_dir.glob("*/SKILL.md"))
    for name in args.skill:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or not (skills_dir / name / "SKILL.md").is_file():
            raise SystemExit(f"No skill named {name!r} under {skills_dir}")
    return args.skill


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run the novelty method on skills through subscription CLIs.")
    parser.add_argument("--skill", action="append", default=[], help="Skill directory name. Repeat for more skills.")
    parser.add_argument("--all", action="store_true", help="Evaluate every skill under skills/.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root that holds skills/.")
    parser.add_argument("--panel", type=Path, help="JSON panel with answerers, judges, drafter, and implementer seats.")
    parser.add_argument("--model", help="One cli:model:effort seat for every role.")
    parser.add_argument("--state", type=Path, default=Path.home() / ".cache" / "eval-skill")
    parser.add_argument("--parallel", type=int, default=8, help="Concurrent calls per CLI.")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds before a call is killed and retried.")
    parser.add_argument("--hedge", type=float, default=45, help="Seconds before a slow call gets a duplicate. Later calls use twice the median.")
    parser.add_argument("--max-claims", type=int, default=30)
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--tasks", type=Path, help="Directory with <skill>.json task evals.")
    args = parser.parse_args()
    if not args.all and not args.skill:
        parser.error("Pass --skill or --all")
    if args.panel and args.model:
        parser.error("Pass --panel or --model, not both")
    if args.parallel < 1 or args.timeout < 1 or args.max_claims < 1 or args.hedge <= 0:
        parser.error("--parallel, --timeout, --hedge, and --max-claims must be positive")
    skills = resolve_skills(args)
    context = Context(args)
    log(f"Run directory: {context.run_dir}")
    log(f"Panel: {json.dumps(context.panel.describe())}")
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=len(skills)) as pool:
        futures = {pool.submit(SkillRun(context, name).run): name for name in skills}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                failures.append(f"{futures[future]}: {error}")
                log(f"{futures[future]} failed: {error}")
    context.arms.shutdown(wait=True)
    context.claims.shutdown(wait=True)
    result = {
        "run": context.run_dir.name,
        "wall_seconds": round(time.monotonic() - context.origin, 1),
        "panel": context.panel.describe(),
        "panel_note": context.panel.note,
        "billing": context.credentials.notes + ["API key variables are removed from every child environment"],
        "skills": sorted(results, key=lambda summary: summary["skill"]),
        "failures": failures,
        "calls": call_stats(context.models.records, context.origin),
        "cache_hits": dict(context.cache.hits),
    }
    write_jsonl(context.run_dir / "calls.jsonl", [
        dict(record, queued_at=round(record["queued_at"] - context.origin, 2),
             started_at=round(record["started_at"] - context.origin, 2),
             ended_at=round(record["ended_at"] - context.origin, 2)) for record in context.models.records])
    save_json(context.run_dir / "summary.json", result)
    report = context.run_dir / "report.md"
    report.write_text(render_report(result), encoding="utf-8")
    log(f"Report: {report}")
    print(json.dumps({key: result[key] for key in ("run", "wall_seconds", "failures")} | {
        "report": str(report),
        "skills": {summary["skill"]: {
            "buckets": summary["buckets"], "unscored": summary["unscored"],
            "isolation": summary["isolation"]["passed"], "proposal": summary.get("proposal", {}).get("status"),
        } for summary in result["skills"]},
    }, ensure_ascii=False))
    bad = failures or any(summary["unscored"] or not summary["isolation"]["passed"] for summary in results)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
