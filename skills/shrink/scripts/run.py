import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path


DRIVERS = {"claudeAgent": "claude", "grok": "grok", "codex": "gpt"}
PROTOCOL = 3
ANSWER_FOOTER = (
    "\n\nThe task is a simulation. When you would use a tool, name the tool and "
    "its arguments in your final answer. Return a final answer without making tool calls."
)
REWRITE_GUARD = (
    "\n\nMake the paragraph shorter. Preserve every instruction and detail without a decision, "
    "including headings and links. "
    "If nothing in the paragraph remains, return exactly [[DROP_PARAGRAPH]]."
)
MASKED_ENV = {
    "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDECODE",
    "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY", "CODEX_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE",
    "OPENAI_ORG_ID", "OPENAI_PROJECT_ID", "XAI_BASE_URL", "GROK_BASE_URL",
}


def digest(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        output.write(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    temporary = Path(output.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def install_transport(scorer, scratch, families):
    env = scorer.clean_env(os.environ)
    for key in MASKED_ENV:
        env.pop(key, None)
    cwd = scratch / "empty"
    cwd.mkdir()
    codex_env = {}
    if "gpt" in families:
        live_codex = Path(env.get("CODEX_HOME") or Path.home() / ".codex")
        codex_home = scratch / "codex"
        codex_home.mkdir()
        auth = live_codex / "auth.json"
        if not auth.is_file():
            raise RuntimeError("A file-backed ChatGPT CLI login is required for isolated evaluation")
        shutil.copyfile(auth, codex_home / "auth.json")
        codex_env = {"CODEX_HOME": str(codex_home)}
    local = threading.local()
    stats = Counter()
    lock = threading.Lock()
    authenticated = False

    def command(args, timeout, prompt=None, overrides=None):
        process = subprocess.run(
            args, input=prompt, capture_output=True, encoding="utf-8", errors="replace",
            cwd=cwd, env={**env, **(overrides or {})}, timeout=timeout, check=False,
        )
        return process

    def strict_command(args, environment, _cwd, timeout):
        args = list(args)
        model, effort, system = local.seat["model"], local.seat["effort"], local.system
        args[args.index("--model") + 1] = model
        if args[0] == "claude":
            args.append("--safe-mode")
            if "--effort" in args:
                args[args.index("--effort") + 1] = effort
            else:
                args.extend(["--effort", effort])
        else:
            args[args.index("--system-prompt-override") + 1] = system
            args[args.index("--tools") + 1] = "none"
            args[args.index("--max-turns") + 1] = "3"
            args.extend(["--permission-mode", "dontAsk"])
            args.extend(["--reasoning-effort", effort])
        process = command(args, timeout, overrides={key: value for key, value in environment.items()
                          if key in {"GROK_HOME", "GROK_CLAUDE_SKILLS_ENABLED", "GROK_CURSOR_SKILLS_ENABLED"}})
        if process.returncode:
            detail = (process.stderr or process.stdout).strip().splitlines()
            raise RuntimeError(f"{args[0]} exited {process.returncode}: {detail[-1][:250] if detail else 'no output'}")
        return process.stdout, ""

    def grok_home():
        if not hasattr(local, "home"):
            local.home = scorer.make_grok_home(Path(tempfile.mkdtemp(dir=scratch)))
        return local.home

    def check_auth():
        nonlocal authenticated
        if authenticated:
            return
        if "claude" in families:
            claude = command(["claude", "auth", "status"], 30)
            status = json.loads(claude.stdout) if not claude.returncode else {}
            if status.get("authMethod") != "claude.ai" or status.get("subscriptionType") != "max":
                raise RuntimeError("Claude requires a Claude Max subscription login")
        if "grok" in families:
            grok = command(["grok", "models"], 30, overrides={"GROK_HOME": str(grok_home())})
            if grok.returncode or "logged in with grok.com" not in (grok.stdout + grok.stderr).lower():
                raise RuntimeError("Grok requires a grok.com subscription login")
        if "gpt" in families:
            codex = command(["codex", "login", "status"], 30, overrides=codex_env)
            if codex.returncode or "logged in using chatgpt" not in (codex.stdout + codex.stderr).lower():
                raise RuntimeError("Codex requires a ChatGPT subscription login")
        authenticated = True

    def call(seat, system, prompt, timeout, parse):
        family = DRIVERS[seat["driverKind"]]
        local.seat, local.system = seat, system
        for attempt in range(3):
            with lock:
                stats[f"{family}_calls"] += 1
            try:
                if family == "claude":
                    text, usage = claude_text(system, prompt, timeout)
                elif family == "grok":
                    text, usage = grok_text(prompt, timeout)
                else:
                    process = command([
                        "codex", "exec", "--skip-git-repo-check", "--ephemeral",
                        "--ignore-user-config", "--ignore-rules", "--disable", "plugins",
                        "--disable", "shell_tool", "--enable", "skip_host_skill_discovery",
                        "--enable", "omit_skill_descriptions", "--sandbox", "read-only",
                        "-c", 'forced_login_method="chatgpt"', "-c", 'web_search="disabled"',
                        "-c", 'approval_policy="never"', "-m", seat["model"],
                        "-c", f'model_reasoning_effort={json.dumps(seat["effort"])}', "-",
                    ], timeout, prompt=system + "\n\nUser task:\n" + prompt, overrides=codex_env)
                    if process.returncode or not process.stdout.strip():
                        raise RuntimeError("Codex failed")
                    text, usage = process.stdout.strip(), {}
                return parse(text), usage
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                with lock:
                    stats["failed_calls"] += 1
                if attempt == 2:
                    raise RuntimeError(f"{family} failed after 3 attempts: {error}") from error
                time.sleep(2 ** attempt)

    claude_text, grok_text = scorer.claude_text, scorer.grok_text
    scorer.work_dir = lambda: cwd
    scorer.grok_home_for_thread = grok_home
    scorer.run_cli = strict_command
    scorer.require_subscription = check_auth
    return call, stats


def blocks(scorer, directory):
    result = {}
    for _, source, body, _ in scorer.skill_parts(directory):
        for paragraph, _ in scorer.paragraph_blocks(body):
            if paragraph.strip():
                result[digest(source, paragraph)] = (source, paragraph)
    return result


def claim_blocks(scorer, claim, paragraphs):
    span = scorer.normalize_ws(claim["span"])
    by_path = {}
    for key, (path, paragraph) in paragraphs.items():
        by_path.setdefault(path, []).append((key, scorer.normalize_ws(paragraph)))
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
        raise RuntimeError(f"Draft claim {claim['id']} has no paragraph for its source span")
    declared, _ = claim_anchor(scorer, claim)
    keys = matches.get(declared) or [key for group in matches.values() for key in group]
    return sorted(keys)


def claim_anchor(scorer, claim):
    source = re.split(r"(?<=\.md):|(?<=\.sh):", claim["source"], maxsplit=1)[0]
    return source, scorer.normalize_ws(claim["span"])


def score(scorer, args, call, stats, seats, state):
    directory = scorer.selected_skills([args.skill])[0]
    paragraphs = blocks(scorer, directory)
    manifest = state / "claims.json"
    previous = read_json(manifest, {"blocks": [], "claims": [], "next": 0})
    unchanged = set(previous["blocks"]) & paragraphs.keys()
    claims = [claim for claim in previous["claims"] if set(claim["_blocks"]) <= unchanged]
    reused_claims = len(claims)
    changed = {key: value for key, value in paragraphs.items() if key not in unchanged}
    next_id = previous["next"]
    answerers = seats["answerers"]

    def identity(text):
        if not text.strip():
            raise ValueError("empty reply")
        return text

    if changed:
        original_bundle = scorer.skill_bundle
        if unchanged:
            scorer.skill_bundle = lambda _: "\n\n".join(
                f"<!-- {source} -->\n{paragraph}" for source, paragraph in changed.values()
            )
        scorer.claude_text = lambda system, prompt, timeout: call(
            answerers[0], system, prompt, timeout, identity,
        )
        try:
            scorer.main(["draft", "--skill", args.skill, "--timeout", str(args.timeout)])
        finally:
            scorer.skill_bundle = original_bundle
        retained_ids = {claim["id"] for claim in claims}
        old_anchors = {claim_anchor(scorer, claim): claim for claim in previous["claims"]
                       if claim["id"] not in retained_ids}
        for claim in scorer.load_claims(args.skill):
            paragraph_keys = claim_blocks(scorer, claim, paragraphs)
            prior = old_anchors.pop(claim_anchor(scorer, claim), None)
            if prior and prior["kind"] == claim["kind"]:
                claim.update(id=prior["id"], question=prior["question"], expected=prior["expected"])
            else:
                claim["id"] = str(next_id)
                next_id += 1
            claims.append(dict(claim, _blocks=paragraph_keys))
    if not claims:
        raise RuntimeError("No claims were drafted")
    save_json(manifest, {"blocks": list(paragraphs), "claims": claims, "next": next_id})

    def write_jsonl(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    write_jsonl(scorer.claims_path(args.skill), claims)
    route_path = state / "routes" / (digest(seats["judges"]) + ".json")
    routes = read_json(route_path, {})
    route_keys = {claim["id"]: digest(claim["id"], claim["_blocks"]) for claim in claims}
    offsets = {claim_id: routes.get(key, 0) for claim_id, key in route_keys.items()}

    def pair(claim):
        claim_id = claim["id"]
        index = (int(claim_id) + offsets[claim_id]) % len(answerers)
        return answerers[index], seats["judges"][DRIVERS[answerers[index]["driverKind"]]]

    def memo(stage, key, compute):
        path = (state.parent if stage == "without" else state) / stage / (key + ".json")
        with scorer.lock_for(path):
            cached = read_json(path)
            if cached is not None:
                return cached
            value = compute()
            save_json(path, value)
            return value

    validation_attempts = Counter()

    def answer(claim, arm, full_bundle, timeout):
        seat, _ = pair(claim)
        context = claim["_blocks"] if arm == "with" else None
        if checking_rewrite:
            validation_attempts[claim["id"]] += 1
            context = [full_bundle, validation_attempts[claim["id"]]]
        key = digest(seat, claim["question"], context)
        system = scorer.answer_system(full_bundle if arm == "with" else "") + ANSWER_FOOTER
        text, usage = memo(arm, key, lambda: call(seat, system, claim["question"], timeout, identity))
        return {"id": claim["id"], "arm": arm, "answer": text, "answerer_model": seat["model"],
                "usage": usage, "ok": True}

    def grade(claim, reply, timeout):
        _, seat = pair(claim)
        prompt = scorer.judge_prompt(claim, reply)
        parsed, usage = memo("grades", digest(seat, prompt),
                             lambda: call(seat, scorer.JUDGE_SYSTEM, prompt, timeout, scorer.parse_grade))
        return dict(parsed, judge_model=seat["model"], usage=usage)

    checking_rewrite = False
    scorer.answer_claim, scorer.grade_answer = answer, grade
    run = ["--skill", args.skill, "--timeout", str(args.timeout), "--concurrency", str(args.concurrency)]
    result = scorer.run_path(args.skill, "baseline")
    for attempt in range(len(answerers)):
        scorer.main(["score", *run])
        rows = scorer.load_jsonl(result / "decisions.jsonl")
        if {row["id"] for row in rows} != set(route_keys):
            raise RuntimeError("The scorer did not return every claim")
        unscored = {row["id"] for row in rows if row["decision"] == "unscored"}
        routes.update({route_keys[claim_id]: offset for claim_id, offset in offsets.items()
                       if offset and claim_id not in unscored})
        save_json(route_path, routes)
        if not unscored:
            break
        if attempt + 1 < len(answerers):
            for claim_id in unscored:
                offsets[claim_id] += 1
            for name in ("answers.jsonl", "grades.jsonl"):
                path = result / name
                write_jsonl(result / f"attempt-{attempt + 1}-{name}", scorer.load_jsonl(path))
                write_jsonl(path, [row for row in scorer.load_jsonl(path) if row["id"] not in unscored])
    if unscored:
        raise RuntimeError(f"Incomplete score for {args.skill}. Retry with the same state. Missing grades: {sorted(unscored)}")
    manifest_path = result / "manifest.json"
    metadata = read_json(manifest_path)
    metadata.update(answerer="mixed", judge="mixed",
                    answerers=[seat["model"] for seat in answerers],
                    judges={family: seat["model"] for family, seat in seats["judges"].items()})
    save_json(manifest_path, metadata)
    counts = {scale: dict(Counter(row[f"bucket_{scale}"] for row in rows))
              for scale in ("lenient", "strict")}
    summary = {"skill": args.skill, "claims": len(claims), "reused_claims": reused_claims,
               "fallback_claims": sum(offset % len(answerers) != 0 for offset in offsets.values()),
               "buckets": counts, "artifacts": str(scorer.novelty_root())}
    if not args.score_only:
        original_blocks = scorer.block_claims

        def safe_block_claims(block, decisions):
            matched = original_blocks(block, decisions)
            complete_cut = any(scorer.normalize_ws(row["span"]) == scorer.normalize_ws(block) for row in matched)
            if matched and not complete_cut and all(row["decision"] == "cut" for row in matched):
                return [*matched, {"decision": "keep", "span": ""}]
            return matched

        def rewrite(system, prompt, timeout, effort=None):
            seat = seats["implementer"]
            system += REWRITE_GUARD
            text, usage = memo("rewrites", digest(seat, system, prompt),
                               lambda: call(seat, system, prompt, timeout, identity))
            return ("" if text.strip() == "[[DROP_PARAGRAPH]]" else text), usage

        scorer.block_claims = safe_block_claims
        scorer.claude_text = rewrite
        before = scorer.disk_chars(directory)
        if scorer.main(["apply", *run]):
            raise RuntimeError("Proposed rewrite failed repository checks")
        after = scorer.disk_chars(directory)
        summary.update(before_chars=before, proposed_chars=after)
        if after < before:
            checking_rewrite = True
            retained = scorer.rescore_skill(directory, args.timeout, args.concurrency)
            lost = [row["id"] for row in retained if row["status"] == "lost"]
            summary.update(checked_taught=len(retained), lost_taught=lost)
            if not lost:
                summary["proposal"] = str(directory)
    summary["calls"] = dict(stats)
    return summary


def load_seats(path, score_only=False):
    seats = read_json(path)
    answerers, judges = seats["answerers"], seats["judges"]
    families = [DRIVERS[seat["driverKind"]] for seat in answerers]
    if len(families) < 2 or len(families) != len(set(families)):
        raise ValueError("Configure at least two answerers, with one model per family")
    for family, seat in judges.items():
        if DRIVERS[seat["driverKind"]] == family:
            raise ValueError(f"{family} needs a judge from a different family")
    if set(judges) != set(families):
        raise ValueError("Configure a judge for each answerer family")
    active = [*answerers, *judges.values()]
    if not score_only:
        active.append(seats["implementer"])
    for seat in active:
        family = DRIVERS[seat["driverKind"]]
        if not seat["model"].startswith(family + "-") or not re.fullmatch(r"[a-z]+", seat["effort"]):
            raise ValueError(f"Invalid {family} seat")
    return seats, {DRIVERS[seat["driverKind"]] for seat in active}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--skill", required=True)
    parser.add_argument("--seats", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--score-only", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.skill):
        parser.error("Pass a skill directory name")
    if args.timeout < 1 or args.concurrency < 1:
        parser.error("Timeout and concurrency must be positive")
    sys.dont_write_bytecode = True
    import novelty as scorer

    seats, families = load_seats(args.seats, args.score_only)
    start = time.monotonic()
    scorer_hash = hashlib.sha256(Path(scorer.__file__).read_bytes()).hexdigest()
    version = digest(PROTOCOL, scorer_hash)
    root = args.state.resolve() / version
    state = root / digest(seats["answerers"]) / args.skill
    artifacts_root = args.state.resolve() / "artifacts" / args.skill
    artifacts_root.mkdir(parents=True, exist_ok=True)
    artifacts = Path(tempfile.mkdtemp(prefix="run-", dir=artifacts_root))
    scratch = artifacts / "repo"
    skill_path = Path("skills") / args.skill
    original = Path("before") / skill_path
    edited = Path("repo") / skill_path
    shutil.copytree(args.root / skill_path, artifacts / edited)
    if not args.score_only:
        shutil.copytree(artifacts / edited, artifacts / original)
    shutil.copytree(args.root / "scripts", scratch / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    scorer.repo_root = lambda: scratch
    scorer.eprint(f"Artifacts: {artifacts}")
    with tempfile.TemporaryDirectory(prefix="shrink-cli-") as temporary:
        call, stats = install_transport(scorer, Path(temporary), families)
        summary = score(scorer, args, call, stats, seats, state)
    if "proposal" in summary:
        diff = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", original.as_posix(), edited.as_posix()],
            cwd=artifacts, capture_output=True, check=False,
        )
        if diff.returncode != 1 or not diff.stdout:
            raise RuntimeError("Could not produce the shrink patch")
        patch = artifacts / "shrink.patch"
        patch.write_bytes(diff.stdout)
        summary["patch"] = str(patch)
    summary["seconds"] = round(time.monotonic() - start, 1)
    summary["scorer_sha256"] = scorer_hash
    save_json(artifacts / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
