import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROMPT_VERSION = "1"
CLAUDE_MODEL = "claude-opus-5-5"
GROK_MODEL = "grok-4.7"
REWRITE_EFFORT = "high"
BANNED_ENV = (
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "OPENAI_API_KEY",
)
GROUPS = ("already_known", "hurts", "teaches", "fails_both")
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
TASK_PREAMBLE = (
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
DRAFT_SYSTEM = """Split one agent skill into claims a later scorer can test.

Return a JSON array and nothing else. Each object has id, kind, question, expected, span, source.

kind is "process" or "fact". process means the skill tells the agent to do, avoid, wait, or order something. fact means it states a name, value, or definition.

span is a verbatim substring of the skill text, copied exactly, long enough to identify the instruction and short enough to be one instruction.

source is the path comment above the text, plus a line hint if you can see one.

question is what the answerer sees. It must not contain the expected behavior, the span's distinctive wording, or the word skill. A process question is a normal user request for work that would occasion the behavior. It is not "what should you do", "explain the steps", or "how do you". A fact question asks for the fact without stating it.

expected is what the judge looks for. The answerer never sees it. For a process claim, describe the action the agent takes on this request, including order and names that the strict grade should require. For a fact claim, state the fact.

Cover the skill. Produce 25 to 30 claims when the text has that many distinct instructions. When it does not, produce one claim per distinct instruction and do not invent any the text does not state. Never produce more than 30. Never use a semicolon or an em dash.

Example of shape, not of content. Skill text says "Before you rename a column, write down the callers." A bad question is "Do you write down the callers before a rename?" A usable question is "The orders table column cust_id should be called customer_id. Change the schema." The expected behavior is "The agent writes down the callers before renaming the column."
"""

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()
_THREAD = threading.local()


def lock_for(path):
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(str(path), threading.Lock())


def repo_root():
    return Path(__file__).resolve().parents[3]


def novelty_root():
    return repo_root() / "novelty"


def eprint(message):
    print(message, file=sys.stderr, flush=True)


def subscription_problems(env, claude_status, grok_models_text):
    problems = []
    for key in BANNED_ENV:
        if env.get(key):
            problems.append(f"{key} is set")
    if not isinstance(claude_status, dict):
        problems.append("claude auth status is not json")
    else:
        if claude_status.get("subscriptionType") != "max":
            problems.append("Claude subscription is not Max")
        if claude_status.get("authMethod") != "claude.ai":
            problems.append("Claude auth is not the claude.ai subscription")
    if "logged in with grok.com" not in (grok_models_text or "").lower():
        problems.append("Grok is not logged in with grok.com")
    return problems


def clean_env(base, extra=None):
    env = dict(base)
    for key in BANNED_ENV:
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def bucket(without_pass, with_pass):
    if without_pass and with_pass:
        return "already_known"
    if without_pass and not with_pass:
        return "hurts"
    if with_pass:
        return "teaches"
    return "fails_both"


def decide(lenient_bucket, strict_bucket):
    return DECISIONS[(lenient_bucket, strict_bucket)]


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def leak_grams(question, expected):
    def grams(parts):
        found = set()
        for index in range(len(parts) - 3):
            gram = parts[index:index + 4]
            if sum(1 for word in gram if word not in STOP) >= 2:
                found.add(" ".join(gram))
        return found
    return sorted(grams(tokens(question)) & grams(tokens(expected)))


def meta_question(question):
    return META_QUESTION.search(question or "") is not None


def normalize_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def validate_claims(claims, bundle):
    errors = []
    if not isinstance(claims, list):
        return ["draft is not a JSON array"]
    if len(claims) > 30:
        errors.append("more than 30 claims")
    if len(bundle) > 4000 and not 25 <= len(claims) <= 30:
        errors.append(f"{len(claims)} claims for a skill over 4000 characters")
    if len(claims) < 1:
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
        span = str(claim.get("span") or "")
        if span and span not in bundle and normalize_ws(span) not in folded:
            errors.append(f"{label} span is not in the skill text")
        leaks = leak_grams(str(claim.get("question") or ""), str(claim.get("span") or ""))
        if leaks:
            errors.append(f"{label} question leaks the instruction: {leaks[0]}")
        if claim.get("kind") == "process" and meta_question(claim.get("question")):
            errors.append(f"{label} process question asks for an explanation")
        if "\u2014" in json.dumps(claim) or ";" in str(claim.get("question") or "") + str(claim.get("expected") or ""):
            errors.append(f"{label} uses a semicolon or an em dash")
    return errors


def parse_grade(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("judge returned no JSON object")
    data = json.loads(raw[start:end + 1])
    grade = {}
    for key in ("lenient", "strict"):
        value = data.get(key)
        if value not in ("pass", "fail"):
            raise ValueError(f"judge {key} is {value!r}")
        grade[key] = value
        reason = data.get(f"{key}_reason", "")
        grade[f"{key}_reason"] = str(reason).replace("\n", " ")[:400]
    return grade


def taught_scales(row):
    scales = []
    if row.get("bucket_lenient") == "teaches":
        scales.append("lenient")
    if row.get("bucket_strict") == "teaches":
        scales.append("strict")
    return scales


def held_status(row, attempts):
    scales = taught_scales(row)
    if not scales:
        return "not-taught"
    for index, grade in enumerate(attempts, start=1):
        if grade and all(grade.get(scale) == "pass" for scale in scales):
            return "held" if index == 1 else "held-on-retry"
    return "lost"


def classify(claims, grades):
    by_arm = {}
    for grade in grades:
        if grade.get("ok"):
            by_arm[(grade["id"], grade["arm"])] = grade
    rows = []
    for claim in claims:
        without = by_arm.get((claim["id"], "without"))
        with_skill = by_arm.get((claim["id"], "with"))
        row = {
            "id": claim["id"],
            "kind": claim["kind"],
            "source": claim.get("source", ""),
            "span": claim.get("span", ""),
            "question": claim.get("question", ""),
            "expected": claim.get("expected", ""),
        }
        if not without or not with_skill:
            row["decision"] = "unscored"
            rows.append(row)
            continue
        lenient = bucket(without["lenient"] == "pass", with_skill["lenient"] == "pass")
        strict = bucket(without["strict"] == "pass", with_skill["strict"] == "pass")
        row["bucket_lenient"] = lenient
        row["bucket_strict"] = strict
        row["decision"] = decide(lenient, strict)
        row["without_lenient_reason"] = without.get("lenient_reason", "")
        row["without_strict_reason"] = without.get("strict_reason", "")
        row["with_lenient_reason"] = with_skill.get("lenient_reason", "")
        row["with_strict_reason"] = with_skill.get("strict_reason", "")
        rows.append(row)
    return rows


def skill_dirs(root):
    skills = root / "skills"
    found = []
    for path in sorted(skills.iterdir()):
        if path.is_dir() and (path / "SKILL.md").is_file():
            found.append(path)
    return found


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


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_keep_newlines(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return normalize_newlines(raw.decode("utf-8")), newline


def write_keep_newlines(path, text, newline):
    text = normalize_newlines(text)
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("utf-8"))


def skill_parts(skill_dir):
    files = []
    for path in skill_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".sh"}:
            files.append(path)
    files.sort(key=lambda path: (path.name != "SKILL.md", path.relative_to(skill_dir).as_posix()))
    parts = []
    for path in files:
        text, _newline = read_keep_newlines(path)
        relative = path.relative_to(repo_root()).as_posix()
        if path.name == "SKILL.md" and path.parent == skill_dir:
            _front, body = split_frontmatter(text)
            parts.append((path, relative, body, text))
        else:
            parts.append((path, relative, text, text))
    return parts


def skill_bundle(skill_dir):
    chunks = []
    for _path, relative, body, _full in skill_parts(skill_dir):
        chunks.append(f"<!-- {relative} -->\n{body.strip()}\n")
    return "\n".join(chunks).strip() + "\n"


def disk_chars(skill_dir):
    total = 0
    for path in skill_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".sh"}:
            total += len(path.read_text(encoding="utf-8"))
    return total


def snapshot_sizes():
    dest = novelty_root() / "sizes-before.json"
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))
    sizes = {path.name: disk_chars(path) for path in skill_dirs(repo_root())}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(sizes, indent=2) + "\n", encoding="utf-8")
    return sizes


def load_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, ensure_ascii=False) + "\n"
    with lock_for(path):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def claims_path(skill):
    return novelty_root() / skill / "claims.jsonl"


def run_path(skill, run):
    return novelty_root() / skill / run


def load_claims(skill):
    return load_jsonl(claims_path(skill))


def extract_json_array(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("draft returned no JSON array")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("draft JSON is not an array")
    return data


def discover_skill_names():
    names = set()
    roots = [
        Path.home() / ".grok" / "skills",
        Path.home() / ".grok" / "bundled" / "skills",
        Path.home() / ".claude" / "skills",
        Path.home() / ".agents" / "skills",
        Path.home() / ".cursor" / "skills",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and re.fullmatch(r"[A-Za-z0-9_.-]+", path.name):
                names.add(path.name)
    return sorted(names)


def make_grok_home(dest):
    if (dest / "config.toml").is_file() and (dest / "auth.json").is_file():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    source = Path.home() / ".grok" / "auth.json"
    if not source.is_file():
        raise SystemExit("Grok auth.json is missing, so the subscription CLI cannot run")
    shutil.copyfile(source, dest / "auth.json")
    (dest / "skills").mkdir(exist_ok=True)
    disabled = ",\n".join(f'  "{name}"' for name in discover_skill_names())
    dest.joinpath("config.toml").write_text(
        "\n".join([
            "[cli]",
            "auto_update = false",
            "",
            "[plugins]",
            "enabled = []",
            "",
            "[skills]",
            "disabled = [",
            disabled,
            "]",
            "",
            "[compat.cursor]",
            "skills = false",
            "rules = false",
            "agents = false",
            "mcps = false",
            "hooks = false",
            "",
            "[compat.claude]",
            "skills = false",
            "rules = false",
            "agents = false",
            "mcps = false",
            "hooks = false",
            "",
            "[models]",
            f'default = "{GROK_MODEL}"',
            "",
        ]),
        encoding="utf-8",
    )
    return dest


def work_dir():
    path = Path(tempfile.gettempdir()) / "novelty-scorer" / "cwd"
    path.mkdir(parents=True, exist_ok=True)
    return path


def grok_home_for_thread():
    home = getattr(_THREAD, "grok_home", None)
    if home is None:
        base = Path(tempfile.gettempdir()) / "novelty-scorer" / f"home-{threading.get_ident()}"
        home = make_grok_home(base)
        _THREAD.grok_home = home
    return home


def run_cli(args, env, cwd, timeout):
    last = None
    for attempt in range(4):
        try:
            completed = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            last = f"timeout after {timeout}s"
            eprint(f"retry {attempt + 1}: {last} :: {args[0]}")
            time.sleep(15 * (attempt + 1))
            continue
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        try:
            parsed = parse_cli_json(stdout) if stdout.strip().startswith("{") or "{" in stdout else None
        except (ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict) and not parsed.get("is_error") and (parsed.get("result") or parsed.get("text")):
            return stdout, ""
        message = stderr.lower()
        if isinstance(parsed, dict):
            message += "\n" + str(parsed.get("result") or parsed.get("error") or "").lower()
        limited = any(mark in message for mark in ("rate limit", "usage limit", "overloaded", "too many requests"))
        if completed.returncode != 0 or limited:
            last = stderr.strip()[:500] or stdout.strip()[:500] or f"exit {completed.returncode}"
            if limited or completed.returncode != 0:
                eprint(f"retry {attempt + 1}: {args[0]} {last[:180]}")
                time.sleep(20 * (attempt + 1))
                if limited:
                    continue
                if attempt < 1:
                    continue
                return stdout, last
        return stdout, ""
    return "", last or "cli failed"


def parse_cli_json(stdout):
    raw = (stdout or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("cli returned no JSON")
        return json.loads(raw[start:end + 1])


def claude_command(system_path, prompt, effort=None):
    args = [
        "claude",
        "-p",
        prompt,
        "--system-prompt-file",
        str(system_path),
        "--tools",
        "",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--permission-mode",
        "dontAsk",
        "--output-format",
        "json",
        "--setting-sources",
        "",
        "--model",
        CLAUDE_MODEL,
    ]
    if effort:
        args.extend(["--effort", effort])
    return args


def claude_text(system, prompt, timeout, effort=None):
    env = clean_env(os.environ)
    with tempfile.TemporaryDirectory(prefix="novelty-claude-") as directory:
        system_path = Path(directory) / "system.txt"
        system_path.write_text(system, encoding="utf-8")
        user = prompt
        args = claude_command(system_path, user, effort)
        if sum(len(part) + 3 for part in args) > 7000:
            system_path.write_text(system + "\n\nUser task:\n" + prompt, encoding="utf-8")
            args[2] = "Do the user task in your instructions."
        stdout, error = run_cli(args, env, work_dir(), timeout)
        if error and not stdout:
            raise RuntimeError(error)
        data = parse_cli_json(stdout)
        if data.get("is_error"):
            raise RuntimeError(str(data.get("result") or "claude error")[:500])
        result = data.get("result")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("claude returned an empty result")
        return result, data.get("modelUsage") or {}


def grok_text(prompt, timeout):
    home = grok_home_for_thread()
    env = clean_env(os.environ, {
        "GROK_HOME": str(home),
        "GROK_CLAUDE_SKILLS_ENABLED": "false",
        "GROK_CURSOR_SKILLS_ENABLED": "false",
    })
    with tempfile.TemporaryDirectory(prefix="novelty-grok-") as directory:
        prompt_path = Path(directory) / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        args = [
            "grok",
            "--prompt-file",
            str(prompt_path),
            "--system-prompt-override",
            JUDGE_SYSTEM,
            "--tools",
            "",
            "--no-subagents",
            "--disable-web-search",
            "--max-turns",
            "1",
            "--output-format",
            "json",
            "--model",
            GROK_MODEL,
            "--cwd",
            str(work_dir()),
            "--no-leader",
            "--leader-socket",
            str(home / "leader.sock"),
        ]
        stdout, error = run_cli(args, env, work_dir(), timeout)
        if error and not stdout:
            raise RuntimeError(error)
        data = parse_cli_json(stdout)
        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("grok returned an empty result")
        return text, data.get("modelUsage") or {}


def judge_prompt(claim, answer):
    clipped = answer if len(answer) <= 12000 else answer[:12000] + "\n[truncated]"
    kind = claim["kind"]
    return (
        f"Kind: {kind}\n"
        "Grade the reply against the expected behavior. The reply's author was not shown the expected behavior.\n"
        "Lenient checks the general idea. Strict checks the specific names, counts, order, and values.\n"
        "For a process claim, the behavior has to be an action the agent commits to for this task. "
        "Naming it as advice, a definition, or an optional aside is a fail on both grades.\n"
        "For a fact claim, a paraphrase that keeps the meaning can pass lenient. "
        "Strict fails when a named detail is missing. Extra correct detail is fine.\n"
        "Reasons are one sentence each, with no newline.\n"
        "Return JSON of this shape and nothing else: "
        '{"lenient":"pass","strict":"fail","lenient_reason":"...","strict_reason":"..."}\n\n'
        f"Expected behavior:\n{claim['expected']}\n\n"
        f"Agent reply:\n{clipped}\n"
    )


def answer_system(bundle):
    if not bundle:
        return TASK_PREAMBLE
    return (
        TASK_PREAMBLE
        + "\nFollow the skill below whenever it applies to the task.\n\n"
        + bundle
    )


def require_subscription():
    env = clean_env(os.environ)
    status_run = subprocess.run(
        ["claude", "auth", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    try:
        status = json.loads(status_run.stdout or "")
    except json.JSONDecodeError:
        status = None
    models_run = subprocess.run(
        ["grok", "models"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    problems = subscription_problems(os.environ, status, (models_run.stdout or "") + (models_run.stderr or ""))
    if problems:
        raise SystemExit("refusing to run: " + "; ".join(problems))


def selected_skills(names):
    by_name = {path.name: path for path in skill_dirs(repo_root())}
    if not names:
        return [by_name[name] for name in sorted(by_name)]
    missing = [name for name in names if name not in by_name]
    if missing:
        raise SystemExit("unknown skill: " + ", ".join(missing))
    return [by_name[name] for name in names]


def draft_skill(skill_dir, timeout):
    bundle = skill_bundle(skill_dir)
    errors = []
    draft = None
    for _round in range(3):
        prompt = "Skill text follows.\n\n" + bundle
        if errors:
            prompt += "\n\nThe previous draft was rejected.\n" + "\n".join(errors[:30])
            prompt += "\nReturn a corrected JSON array."
        text, _usage = claude_text(DRAFT_SYSTEM, prompt, timeout)
        try:
            draft = extract_json_array(text)
        except (ValueError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
            continue
        errors = validate_claims(draft, bundle)
        if not errors:
            break
    if draft is None or errors:
        raise RuntimeError(f"{skill_dir.name} draft failed: {errors[:8]}")
    path = claims_path(skill_dir.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for claim in draft:
            claim["skill"] = skill_dir.name
            handle.write(json.dumps(claim, ensure_ascii=False) + "\n")
    eprint(f"drafted {skill_dir.name} {len(draft)} claims")
    return len(draft)


def grade_answer(claim, answer, timeout):
    last_error = ""
    for _attempt in range(2):
        try:
            text, usage = grok_text(judge_prompt(claim, answer), timeout)
            grade = parse_grade(text)
            grade["judge_model"] = GROK_MODEL
            grade["usage"] = usage
            return grade
        except (ValueError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = str(exc)
    raise RuntimeError(last_error or "judge failed")


def answer_claim(claim, arm, bundle, timeout):
    system = answer_system(bundle if arm == "with" else "")
    text, usage = claude_text(system, claim["question"], timeout)
    return {
        "id": claim["id"],
        "arm": arm,
        "answer": text,
        "answerer_model": CLAUDE_MODEL,
        "usage": usage,
        "ok": True,
    }


def score_skill(skill_dir, run, limit, arms, claim_ids, timeout, concurrency):
    claims = load_claims(skill_dir.name)
    if not claims:
        raise RuntimeError(f"{skill_dir.name} has no claims")
    if claim_ids:
        wanted = set(claim_ids)
        claims = [claim for claim in claims if claim["id"] in wanted]
    if limit:
        claims = claims[:limit]
    bundle = skill_bundle(skill_dir)
    directory = run_path(skill_dir.name, run)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.json"
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("prompt_version") != PROMPT_VERSION:
            raise SystemExit(f"{directory} was scored with prompt {existing.get('prompt_version')}")
    else:
        write_json(manifest, {
            "prompt_version": PROMPT_VERSION,
            "answerer": CLAUDE_MODEL,
            "judge": GROK_MODEL,
            "skill_chars": len(bundle),
        })
    answers_path = directory / "answers.jsonl"
    grades_path = directory / "grades.jsonl"
    have_answers = {(row["id"], row["arm"]) for row in load_jsonl(answers_path) if row.get("ok")}
    have_grades = {(row["id"], row["arm"], row.get("attempt", 1)) for row in load_jsonl(grades_path) if row.get("ok")}
    jobs = []
    for claim in claims:
        for arm in arms:
            if (claim["id"], arm) not in have_answers:
                jobs.append((claim, arm))
    eprint(f"score {skill_dir.name} {len(jobs)} answers")

    def run_job(job):
        claim, arm = job
        try:
            row = answer_claim(claim, arm, bundle, timeout)
        except (RuntimeError, ValueError, json.JSONDecodeError, OSError) as exc:
            row = {"id": claim["id"], "arm": arm, "ok": False, "error": str(exc)[:500]}
        append_jsonl(answers_path, row)
        if not row.get("ok"):
            return
        attempt = 1
        if (claim["id"], arm, attempt) in have_grades:
            return
        try:
            grade = grade_answer(claim, row["answer"], timeout)
            grade.update({"id": claim["id"], "arm": arm, "attempt": attempt, "ok": True})
        except (RuntimeError, ValueError, json.JSONDecodeError, OSError) as exc:
            grade = {"id": claim["id"], "arm": arm, "attempt": attempt, "ok": False, "error": str(exc)[:500]}
        append_jsonl(grades_path, grade)
        if grade.get("ok"):
            eprint(f"{skill_dir.name} {claim['id']} {arm} {grade['lenient']}/{grade['strict']}")

    workers = max(1, concurrency)
    if jobs:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(run_job, jobs))
    pending_grades = []
    answers = {(row["id"], row["arm"]): row for row in load_jsonl(answers_path) if row.get("ok")}
    graded = {(row["id"], row["arm"]) for row in load_jsonl(grades_path) if row.get("ok")}
    for claim in claims:
        for arm in arms:
            if (claim["id"], arm) in answers and (claim["id"], arm) not in graded:
                pending_grades.append((claim, answers[(claim["id"], arm)]["answer"], arm))

    def run_grade(item):
        claim, answer, arm = item
        try:
            grade = grade_answer(claim, answer, timeout)
            grade.update({"id": claim["id"], "arm": arm, "attempt": 1, "ok": True})
        except (RuntimeError, ValueError, json.JSONDecodeError, OSError) as exc:
            grade = {"id": claim["id"], "arm": arm, "attempt": 1, "ok": False, "error": str(exc)[:500]}
        append_jsonl(grades_path, grade)

    if pending_grades:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(run_grade, pending_grades))
    grades = [row for row in load_jsonl(grades_path) if row.get("ok") and row.get("attempt", 1) == 1]
    rows = classify(claims, grades)
    decisions = directory / "decisions.jsonl"
    with decisions.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    unscored = sum(1 for row in rows if row["decision"] == "unscored")
    eprint(f"classified {skill_dir.name} unscored {unscored}")
    return rows


def paragraph_blocks(text):
    pieces = re.split(r"(\n[ \t]*\n)", text)
    blocks = []
    index = 0
    while index < len(pieces):
        chunk = pieces[index]
        separator = pieces[index + 1] if index + 1 < len(pieces) else ""
        blocks.append((chunk, separator))
        index += 2
    return blocks


def block_claims(block, rows):
    folded = normalize_ws(block)
    matched = []
    for row in rows:
        span = row.get("span") or ""
        if not span:
            continue
        if span in block or normalize_ws(span) in folded:
            matched.append(row)
    return matched


def forbidden_punctuation(text):
    if "\u2014" in text:
        return True
    fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        visible = re.sub(r"`[^`]*`", "", line)
        if ";" in visible:
            return True
    return False


def rewrite_paragraph(block, rows, timeout):
    keep = [row["span"] for row in rows if row["decision"] == "keep" and row.get("span")]
    change = [row for row in rows if row["decision"] in {"fix", "rewrite", "cut"}]
    if not change:
        return block
    lines = [
        "Edit the paragraph. Return only the edited paragraph.",
        "Do not add a semicolon or an em dash.",
        "Do not add a step the paragraph did not already contain.",
    ]
    if keep:
        lines.append("These spans must remain verbatim:")
        lines.extend(keep)
    for row in change:
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
    text, _usage = claude_text(
        "You edit one paragraph of an agent skill. Return only the paragraph.",
        "\n".join(lines),
        timeout,
        effort=REWRITE_EFFORT,
    )
    edited = text.strip()
    if forbidden_punctuation(edited):
        raise RuntimeError("rewrite added an em dash or a prose semicolon")
    for span in keep:
        if span not in edited and normalize_ws(span) not in normalize_ws(edited):
            raise RuntimeError("rewrite dropped a kept span")
    return edited


def apply_skill(skill_dir, run, timeout):
    rows = load_jsonl(run_path(skill_dir.name, run) / "decisions.jsonl")
    if any(row["decision"] == "unscored" for row in rows):
        raise RuntimeError(f"{skill_dir.name} still has unscored claims")
    originals = {
        path: path.read_bytes()
        for path in skill_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".sh"}
    }
    changed = []
    for path, _relative, body, full in skill_parts(skill_dir):
        if path.name == "SKILL.md" and path.parent == skill_dir:
            front, text = split_frontmatter(full)
        else:
            front, text = "", full
        blocks = paragraph_blocks(text)
        rebuilt = []
        file_changed = False
        for block, separator in blocks:
            matched = block_claims(block, rows)
            actions = {row["decision"] for row in matched}
            if matched and actions <= {"cut"}:
                file_changed = True
                continue
            if matched and actions & {"fix", "rewrite", "cut"} and not actions <= {"cut"}:
                try:
                    edited = rewrite_paragraph(block, matched, timeout)
                except RuntimeError as exc:
                    eprint(f"{skill_dir.name} left a paragraph in place: {exc}")
                    edited = block
                if edited != block:
                    file_changed = True
                rebuilt.append(edited + separator)
                continue
            rebuilt.append(block + separator)
        if file_changed:
            _original, newline = read_keep_newlines(path)
            new_text = front + "".join(rebuilt)
            if _original.endswith("\n") and new_text and not new_text.endswith("\n"):
                new_text += "\n"
            if not new_text.strip():
                eprint(f"{skill_dir.name} left {path.name} in place: edit would empty the file")
                continue
            write_keep_newlines(path, new_text, newline)
            changed.append(path.relative_to(repo_root()).as_posix())
    problems = punctuation_problems(skill_dir)
    if problems:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise RuntimeError(f"{skill_dir.name} punctuation check failed\n{problems[0][:500]}")
    eprint(f"applied {skill_dir.name} files {len(changed)}")
    return changed


def punctuation_problems(root):
    problems = []
    scripts = repo_root() / "scripts"
    for name in ("no-em-dashes.py", "no-semicolons.py", "use-when-descriptions.py"):
        completed = subprocess.run(
            [sys.executable, str(scripts / name), str(root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            problems.append((completed.stdout or "") + (completed.stderr or ""))
    return problems


def counts_for(rows, key):
    counts = {group: 0 for group in GROUPS}
    for row in rows:
        group = row.get(key)
        if group in counts:
            counts[group] += 1
    return counts


def report_skill(skill, before, after_chars):
    rows = load_jsonl(run_path(skill, "baseline") / "decisions.jsonl")
    kept = load_jsonl(run_path(skill, "after") / "kept.jsonl")
    lenient = counts_for(rows, "bucket_lenient")
    strict = counts_for(rows, "bucket_strict")
    decisions = {}
    for row in rows:
        decisions[row["decision"]] = decisions.get(row["decision"], 0) + 1
    held = sum(1 for row in kept if row.get("status") in {"held", "held-on-retry"})
    lost = sum(1 for row in kept if row.get("status") == "lost")
    taught = sum(1 for row in rows if taught_scales(row))
    lines = [
        f"### {skill}",
        "",
        "| Group | Lenient | Strict |",
        "| --- | ---: | ---: |",
    ]
    for group in GROUPS:
        label = group.replace("_", " ")
        lines.append(f"| {label} | {lenient[group]} | {strict[group]} |")
    lines.extend([
        "",
        f"Claims: {len(rows)}. Decisions: "
        + ", ".join(f"{name} {decisions.get(name, 0)}" for name in ("cut", "fix", "keep", "rewrite", "unscored"))
        + f". Characters before: {before}. Characters after: {after_chars}.",
        f"Taught claims still held after the cut: {held} of {taught}. Lost: {lost}.",
        "",
    ])
    return "\n".join(lines), held, lost, taught


def write_report():
    before = {}
    sizes_path = novelty_root() / "sizes-before.json"
    if sizes_path.exists():
        before = json.loads(sizes_path.read_text(encoding="utf-8"))
    sections = [
        "# Novelty cuts",
        "",
        f"Answerer `{CLAUDE_MODEL}` on the Claude Max subscription. "
        f"Judge `{GROK_MODEL}` on the grok.com subscription. "
        "Each claim was asked with the skill and without it. "
        "The judge graded each reply leniently and strictly. "
        "A process claim counts as known only when the reply does the step without being asked to explain it.",
        "",
        "A claim is kept when either grade teaches, fixed when either grade hurts, "
        "cut when both grades are already known, and rewritten otherwise. "
        "Frontmatter is unchanged.",
        "",
        f"Skill text was rewritten by `{CLAUDE_MODEL}` on the Claude Max subscription at effort {REWRITE_EFFORT}. "
        f"The judge stayed `{GROK_MODEL}` on the grok.com subscription.",
        "",
    ]
    total_lost = 0
    for skill_dir in skill_dirs(repo_root()):
        section, _held, lost, _taught = report_skill(
            skill_dir.name,
            before.get(skill_dir.name, ""),
            disk_chars(skill_dir),
        )
        sections.append(section)
        total_lost += lost
    path = novelty_root() / "report.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    eprint(f"wrote {path}")
    return total_lost


def rescore_skill(skill_dir, timeout, concurrency):
    baseline = load_jsonl(run_path(skill_dir.name, "baseline") / "decisions.jsonl")
    taught = [row for row in baseline if taught_scales(row)]
    if not taught:
        kept_path = run_path(skill_dir.name, "after") / "kept.jsonl"
        kept_path.parent.mkdir(parents=True, exist_ok=True)
        kept_path.write_text("", encoding="utf-8")
        eprint(f"{skill_dir.name} taught nothing")
        return []
    score_skill(
        skill_dir,
        "after",
        limit=0,
        arms=("with",),
        claim_ids=[row["id"] for row in taught],
        timeout=timeout,
        concurrency=concurrency,
    )
    grades = load_jsonl(run_path(skill_dir.name, "after") / "grades.jsonl")
    by_id = {}
    for grade in grades:
        if grade.get("ok") and grade.get("arm") == "with":
            by_id.setdefault(grade["id"], []).append(grade)
    retry = []
    for row in taught:
        status = held_status(row, by_id.get(row["id"], []))
        if status == "lost":
            retry.append(row)
    if retry:
        for row in retry:
            claim = next(item for item in load_claims(skill_dir.name) if item["id"] == row["id"])
            try:
                answer = answer_claim(claim, "with", skill_bundle(skill_dir), timeout)
                append_jsonl(run_path(skill_dir.name, "after") / "answers.jsonl", answer)
                grade = grade_answer(claim, answer["answer"], timeout)
                grade.update({"id": claim["id"], "arm": "with", "attempt": 2, "ok": True})
            except RuntimeError as exc:
                grade = {"id": row["id"], "arm": "with", "attempt": 2, "ok": False, "error": str(exc)[:500]}
            append_jsonl(run_path(skill_dir.name, "after") / "grades.jsonl", grade)
            if grade.get("ok"):
                by_id.setdefault(row["id"], []).append(grade)
    kept_rows = []
    for row in taught:
        status = held_status(row, [grade for grade in by_id.get(row["id"], []) if grade.get("ok")])
        kept_rows.append({"id": row["id"], "status": status, "scales": taught_scales(row)})
        eprint(f"kept {skill_dir.name} {row['id']} {status}")
    path = run_path(skill_dir.name, "after") / "kept.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in kept_rows:
            handle.write(json.dumps(row) + "\n")
    return kept_rows


def calibrate(timeout):
    claim = {
        "id": "cal",
        "kind": "process",
        "question": "unused",
        "expected": "The agent writes down the callers before renaming the column.",
    }
    does = "I will list every caller of cust_id, then rename the column to customer_id in the migration."
    explains = "Best practice is to think about callers. I will rename cust_id to customer_id now."
    do_grade = grade_answer(claim, does, timeout)
    explain_grade = grade_answer(claim, explains, timeout)
    eprint(f"calibrate does {do_grade['lenient']}/{do_grade['strict']}")
    eprint(f"calibrate explains {explain_grade['lenient']}/{explain_grade['strict']}")
    if do_grade["lenient"] != "pass" or do_grade["strict"] != "pass":
        raise SystemExit("calibration failed: a reply that does the step was not graded pass")
    if explain_grade["lenient"] != "fail" or explain_grade["strict"] != "fail":
        raise SystemExit("calibration failed: an explanation was graded as doing the step")


def self_test():
    assert subscription_problems({"ANTHROPIC_API_KEY": "x"}, {"subscriptionType": "max", "authMethod": "claude.ai"}, "logged in with grok.com")
    assert subscription_problems({}, {"subscriptionType": "pro", "authMethod": "claude.ai"}, "logged in with grok.com")
    assert subscription_problems({}, {"subscriptionType": "max", "authMethod": "api"}, "logged in with grok.com")
    assert not subscription_problems({}, {"subscriptionType": "max", "authMethod": "claude.ai"}, "You are logged in with grok.com.")
    for pair, decision in DECISIONS.items():
        assert decide(*pair) == decision
    assert bucket(True, True) == "already_known"
    assert bucket(True, False) == "hurts"
    assert bucket(False, True) == "teaches"
    assert bucket(False, False) == "fails_both"
    assert leak_grams(
        "The orders table column cust_id should be called customer_id. Change the schema.",
        "The agent writes down the callers before renaming the column.",
    ) == []
    assert leak_grams(
        "Write down the callers before renaming the column.",
        "The agent writes down the callers before renaming the column.",
    )
    bundle = "Before you rename a column, write down the callers.\n"
    good = [{
        "id": "01",
        "kind": "process",
        "question": "The orders table column cust_id should be called customer_id. Change the schema.",
        "expected": "The agent writes down the callers before renaming the column.",
        "span": "write down the callers",
        "source": "skills/example/SKILL.md",
    }]
    assert validate_claims(good, bundle) == []
    bad = [dict(good[0], question="Do you write down the callers before a rename?")]
    assert any("leaks" in error or "explanation" in error for error in validate_claims(bad, bundle))
    shared = [dict(good[0], question="Change src/lib/money.ts so totals round half away from zero.", expected="In src/lib/money.ts the agent writes a failing test before editing the function.")]
    assert validate_claims(shared, bundle) == []
    grade = parse_grade('```json\n{"lenient":"pass","strict":"fail","lenient_reason":"idea","strict_reason":"no order"}\n```')
    assert grade["lenient"] == "pass" and grade["strict"] == "fail"
    claims = good
    grades = [
        {"id": "01", "arm": "without", "ok": True, "lenient": "fail", "strict": "fail", "lenient_reason": "", "strict_reason": ""},
        {"id": "01", "arm": "with", "ok": True, "lenient": "pass", "strict": "pass", "lenient_reason": "", "strict_reason": ""},
    ]
    rows = classify(claims, grades)
    assert rows[0]["decision"] == "keep"
    assert held_status(rows[0], [{"lenient": "pass", "strict": "pass"}]) == "held"
    assert held_status(rows[0], [{"lenient": "fail", "strict": "fail"}, {"lenient": "pass", "strict": "pass"}]) == "held-on-retry"
    assert held_status(rows[0], [{"lenient": "fail", "strict": "pass"}]) == "lost"
    front, body = split_frontmatter("---\nname: x\n---\n\nBody line.\n")
    assert "name: x" in front and body.strip() == "Body line."
    assert forbidden_punctuation("keep this, and that") is False
    assert forbidden_punctuation("keep this; drop that") is True
    assert forbidden_punctuation("keep `\u003b` inside ticks") is False
    blocks = paragraph_blocks("one\n\ntwo\n")
    assert blocks[0][0] == "one" and "two" in blocks[1][0]
    crlf_blocks = paragraph_blocks(normalize_newlines("alpha\r\n\r\nbeta\r\n"))
    assert len(crlf_blocks) == 2 and crlf_blocks[0][0] == "alpha" and "beta" in crlf_blocks[1][0]
    with tempfile.TemporaryDirectory() as directory:
        sample = Path(directory) / "sample.md"
        sample.write_bytes(b"alpha\r\n\r\nbeta\r\n")
        sample_text, sample_newline = read_keep_newlines(sample)
        assert sample_newline == "\r\n" and "\r" not in sample_text
        write_keep_newlines(sample, sample_text, sample_newline)
        assert sample.read_bytes() == b"alpha\r\n\r\nbeta\r\n"
    rewrite = claude_command(Path("system.txt"), "paragraph", effort=REWRITE_EFFORT)
    assert rewrite[rewrite.index("--model") + 1] == "claude-opus-5-5"
    assert rewrite[rewrite.index("--effort") + 1] == "high"
    assert "--effort" not in claude_command(Path("system.txt"), "question")
    print("self-test passed")


def add_common(parser):
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=3)


def main(argv):
    parser = argparse.ArgumentParser(description="Score skill novelty and apply the four-way cut.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    for name in ("draft", "score", "apply", "rescore", "report", "calibrate"):
        add_common(sub.add_parser(name))
    score = sub.choices["score"]
    score.add_argument("--run", default="baseline")
    score.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)
    if args.command == "self-test":
        self_test()
        return 0
    if args.command == "report":
        lost = write_report()
        return 1 if lost else 0
    require_subscription()
    snapshot_sizes()
    if args.command == "calibrate":
        calibrate(args.timeout)
        return 0
    skills = selected_skills(args.skill)
    failures = []
    if args.command == "draft":
        workers = max(1, args.concurrency)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(draft_skill, skill, args.timeout): skill for skill in skills}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    failures.append(f"{futures[future].name}: {exc}")
                    eprint(failures[-1])
        if failures:
            raise SystemExit("\n".join(failures))
        return 0
    if args.command == "score":
        for skill in skills:
            try:
                score_skill(skill, args.run, args.limit, ("without", "with"), None, args.timeout, args.concurrency)
            except Exception as exc:
                failures.append(f"{skill.name}: {exc}")
                eprint(failures[-1])
        if failures:
            raise SystemExit("\n".join(failures))
        return 0
    if args.command == "apply":
        for skill in skills:
            try:
                apply_skill(skill, "baseline", args.timeout)
            except Exception as exc:
                failures.append(f"{skill.name}: {exc}")
                eprint(failures[-1])
        problems = punctuation_problems(repo_root() / "skills")
        if problems:
            sys.stderr.write("\n".join(problems))
            return 1
        if failures:
            raise SystemExit("\n".join(failures))
        return 0
    if args.command == "rescore":
        lost = 0
        for skill in skills:
            try:
                rows = rescore_skill(skill, args.timeout, args.concurrency)
            except Exception as exc:
                failures.append(f"{skill.name}: {exc}")
                eprint(failures[-1])
                continue
            for row in rows:
                if row["status"] == "lost":
                    lost += 1
        write_report()
        if failures:
            raise SystemExit("\n".join(failures))
        return 1 if lost else 0
    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
