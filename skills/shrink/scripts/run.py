import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4


DRIVERS = {"claudeAgent": "claude", "grok": "grok", "codex": "gpt"}
PROTOCOL = 4
ANSWER_FOOTER = (
    "\n\nThe task is a simulation. When you would use a tool, name the tool and "
    "its arguments in your final answer. Return a final answer without making tool calls."
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


def reveals_fact(question, expected):
    question_words = " ".join(tokens(question))
    expected_words = " ".join(tokens(expected))
    return bool(expected_words and f" {expected_words} " in f" {question_words} ")


def normalize_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def validate_claims(claims, bundle, allow_empty=False):
    errors = []
    if not isinstance(claims, list):
        return ["draft is not a JSON array"]
    if len(claims) > 30:
        errors.append("more than 30 claims")
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
        span = str(claim.get("span") or "")
        if span and span not in bundle and normalize_ws(span) not in folded:
            errors.append(f"{label} span is not in the skill text")
        leaks = leak_grams(str(claim.get("question") or ""), str(claim.get("span") or ""))
        if leaks:
            errors.append(f"{label} question leaks the instruction: {leaks[0]}")
        if claim.get("kind") == "process" and meta_question(claim.get("question")):
            errors.append(f"{label} process question asks for an explanation")
        if claim.get("kind") == "fact" and reveals_fact(str(claim.get("question") or ""), str(claim.get("expected") or "")):
            errors.append(f"{label} fact question contains the expected answer")
        if "\u2014" in json.dumps(claim, ensure_ascii=False) or ";" in str(claim.get("question") or "") + str(claim.get("expected") or ""):
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
        if claim["kind"] == "process" and row["decision"] == "cut":
            row["decision"] = "keep"
        row["without_lenient_reason"] = without.get("lenient_reason", "")
        row["without_strict_reason"] = without.get("strict_reason", "")
        row["with_lenient_reason"] = with_skill.get("lenient_reason", "")
        row["with_strict_reason"] = with_skill.get("strict_reason", "")
        rows.append(row)
    return rows


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
        relative = path.relative_to(skill_dir.parent.parent).as_posix()
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
        f"User task:\n{claim['question']}\n\n"
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


def rewrite_paragraph(block, rows, request):
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
    result = request("You edit one paragraph of an agent skill." + REWRITE_GUARD, "\n".join(lines))
    edited = "" if result == "[[DROP_PARAGRAPH]]" else result
    if forbidden_punctuation(edited):
        raise RuntimeError("rewrite added an em dash or a prose semicolon")
    for span in keep:
        if span not in edited and normalize_ws(span) not in normalize_ws(edited):
            raise RuntimeError("rewrite dropped a kept span")
    return edited


def blocks(directory):
    result = {}
    for _, source, body, _ in skill_parts(directory):
        for paragraph, _ in paragraph_blocks(body):
            if paragraph.strip():
                result[digest(source, paragraph)] = (source, paragraph)
    return result


def claim_blocks(claim, paragraphs):
    span = normalize_ws(claim["span"])
    by_path = {}
    for key, (path, paragraph) in paragraphs.items():
        by_path.setdefault(path, []).append((key, normalize_ws(paragraph)))
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
    declared, _ = claim_anchor(claim)
    keys = matches.get(declared) or [key for group in matches.values() for key in group]
    return sorted(keys)


def claim_anchor(claim):
    source = re.split(r"(?<=\.md):|(?<=\.sh):", claim["source"], maxsplit=1)[0]
    return source, normalize_ws(claim["span"])


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def reply_path(queue, request_id):
    return queue / "responses" / f"{request_id}.json"


def pending(queue):
    now = time.time()
    for path in sorted((queue / "requests").glob("*.json")):
        if not reply_path(queue, path.stem).exists():
            request = read_json(path)
            if request["expires_at"] > now:
                print(json.dumps(request))


def submit_reply(args):
    request_path = args.queue / "requests" / f"{args.id}.json"
    request = read_json(request_path)
    if not request or request["expires_at"] <= time.time():
        raise ValueError("Request is missing or expired")
    destination = reply_path(args.queue, args.id)
    if destination.exists():
        raise ValueError("Request already has a reply")
    response = {"error": args.error} if args.error else {"text": args.file.read_text(encoding="utf-8-sig")}
    save_json(destination, response)


class RequestQueue:
    def __init__(self, directory, timeout):
        self.directory = directory
        self.timeout = timeout
        self.stats = Counter()
        self.lock = threading.Lock()

    def call(self, seat, kind, instructions, prompt, parse):
        for attempt in range(3):
            try:
                return parse(self.request(seat, kind, instructions, prompt))
            except (ValueError, RuntimeError) as error:
                with self.lock:
                    self.stats["failed_calls"] += 1
                if attempt == 2:
                    raise RuntimeError(f"{kind} failed on {seat['model']}: {error}") from error

    def request(self, seat, kind, instructions, prompt):
        request_id = uuid4().hex
        deadline = time.time() + self.timeout
        request = {
            "id": request_id, "seat": seat, "kind": kind, "instructions": instructions,
            "prompt": prompt, "expires_at": deadline,
        }
        with self.lock:
            self.stats[DRIVERS[seat["driverKind"]] + "_calls"] += 1
        save_json(self.directory / "requests" / f"{request_id}.json", request)
        path = reply_path(self.directory, request_id)
        while time.time() < deadline:
            response = read_json(path)
            if response is not None:
                if "error" in response:
                    raise RuntimeError(response["error"])
                text = response.get("text", "").strip()
                if not text:
                    raise ValueError("Empty reply")
                return text
            time.sleep(0.15)
        raise RuntimeError("T3 reply timed out")


class Cache:
    def __init__(self, directory):
        self.directory = directory
        self.locks = {}
        self.guard = threading.Lock()

    def get(self, stage, key, compute):
        parent = self.directory.parent if stage == "without" else self.directory
        path = parent / stage / (key + ".json")
        with self.guard:
            lock = self.locks.setdefault(path, threading.Lock())
        with lock:
            existing = read_json(path)
            if existing is not None:
                return existing
            value = compute()
            save_json(path, value)
            return value


def draft_claims(directory, manifest, request, seat):
    paragraphs = blocks(directory)
    previous = read_json(manifest, {"blocks": [], "claims": [], "next": 0})
    unchanged = set(previous["blocks"]) & paragraphs.keys()
    claims = [claim for claim in previous["claims"] if set(claim["_blocks"]) <= unchanged]
    reused = len(claims)
    changed = {key: pair for key, pair in paragraphs.items() if key not in unchanged}
    next_id = previous["next"]
    if changed:
        bundle = "\n\n".join(f"<!-- {source} -->\n{block}" for source, block in changed.values())

        def parse(text):
            result = extract_json_array(text)
            errors = validate_claims(result, bundle, allow_empty=bool(claims))
            if errors:
                raise ValueError("; ".join(errors))
            return result

        drafted = request.call(seat, "draft", DRAFT_SYSTEM, bundle, parse)
        retained = {row["id"] for row in claims}
        old = {claim_anchor(row): row for row in previous["claims"] if row["id"] not in retained}
        for claim in drafted:
            prior = old.pop(claim_anchor(claim), None)
            if prior and prior["kind"] == claim["kind"]:
                claim.update(id=prior["id"], question=prior["question"], expected=prior["expected"])
            else:
                claim["id"] = str(next_id)
                next_id += 1
            claims.append(dict(claim, _blocks=claim_blocks(claim, paragraphs)))
    if not claims:
        raise ValueError("No claims were drafted")
    save_json(manifest, {"blocks": list(paragraphs), "claims": claims, "next": next_id})
    return claims, reused


def score_arm(claim, arm, bundle, answerer, judge, cache, queue, candidate_attempt=0):
    if candidate_attempt:
        context = [bundle, candidate_attempt]
    else:
        context = None if arm == "without" else claim["_blocks"]
    question = claim["question"]
    system = answer_system(bundle if arm == "with" else "") + ANSWER_FOOTER
    reply = cache.get(arm, digest(answerer, question, context), lambda: queue.call(
        answerer, "answer", system, question, str,
    ))
    prompt = judge_prompt(claim, reply)
    grade = cache.get("grades", digest(judge, prompt), lambda: queue.call(
        judge, "judge", JUDGE_SYSTEM, prompt, parse_grade,
    ))
    fields = {"id": claim["id"], "arm": arm, "ok": True}
    return (dict(fields, answer=reply, answerer_model=answerer["model"]),
            dict(fields, **grade, judge_model=judge["model"], attempt=candidate_attempt or 1))


def evaluate_claim(claim, bundle, seats, cache, queue):
    answerers = seats["answerers"]
    key = digest(claim["id"], claim["_blocks"], seats["judges"])
    route_path = cache.directory / "routes" / (key + ".json")
    starting = read_json(route_path, 0)
    for attempt in range(len(answerers)):
        offset = (starting + attempt) % len(answerers)
        answerer = answerers[(int(claim["id"]) + offset) % len(answerers)]
        judge = seats["judges"][DRIVERS[answerer["driverKind"]]]
        try:
            paired = [score_arm(claim, arm, bundle, answerer, judge, cache, queue) for arm in ("without", "with")]
        except RuntimeError as error:
            if attempt + 1 == len(answerers):
                raise RuntimeError(f"Claim {claim['id']} is incomplete: {error}") from error
        else:
            save_json(route_path, offset)
            return paired, answerer, judge, offset != 0


def rewrite_skill(directory, rows, seat, cache, queue):
    def request(instructions, prompt):
        key = digest(seat, instructions, prompt)
        return cache.get("rewrites", key, lambda: queue.call(seat, "rewrite", instructions, prompt, str))

    for path, source, body, full in skill_parts(directory):
        front = full[:-len(body)] if body and body != full else ""
        decisions = [row for row in rows if row["source"].split(":", 1)[0] == source]
        result = []
        for block, separator in paragraph_blocks(body):
            matched = block_claims(block, decisions)
            edited = block
            if any(row["decision"] != "keep" for row in matched):
                if all(row["decision"] == "cut" for row in matched) and any(
                    normalize_ws(row["span"]) == normalize_ws(block) for row in matched
                ):
                    edited = ""
                else:
                    edited = rewrite_paragraph(block, matched, request)
            result.append(edited + separator if edited or not block else "")
        edited_file = front + "".join(result)
        if edited_file.strip() and edited_file != full:
            _, newline = read_keep_newlines(path)
            write_keep_newlines(path, edited_file, newline)


def validate_candidate(directory, original, routes, cache, queue, concurrency):
    bundle = skill_bundle(directory)

    def check(row):
        answerer, judge = routes[row["id"]]
        answers, grades = [], []
        for index in (1, 2):
            answer, grade = score_arm(row, "with", bundle, answerer, judge, cache, queue, index)
            answers.append(answer)
            grades.append(grade)
            if held_status(row, grades) != "lost":
                break
        return {"id": row["id"], "status": held_status(row, grades), "scales": taught_scales(row)}, answers, grades

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(pool.map(check, (row for row in original if taught_scales(row))))


def bucket_counts(rows):
    return {scale: dict(Counter(row[f"bucket_{scale}"] for row in rows)) for scale in ("lenient", "strict")}


def evaluate_skill(args, directory, artifacts, seats, cache, queue):
    claims, reused = draft_claims(directory, cache.directory / "claims.json", queue, seats["answerers"][0])
    base = artifacts / "novelty" / args.skill
    write_jsonl(base / "claims.jsonl", claims)
    bundle = skill_bundle(directory)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        scored = list(pool.map(lambda claim: evaluate_claim(claim, bundle, seats, cache, queue), claims))
    answers = [answer for pairs, _, _, _ in scored for answer, _ in pairs]
    grades = [grade for pairs, _, _, _ in scored for _, grade in pairs]
    routes = {pairs[0][0]["id"]: (answerer, judge) for pairs, answerer, judge, _ in scored}
    rows = classify(claims, grades)
    for name, data in (("answers", answers), ("grades", grades), ("decisions", rows)):
        write_jsonl(base / "baseline" / f"{name}.jsonl", data)
    save_json(base / "baseline" / "manifest.json", {
        "prompt_version": PROTOCOL, "answerers": seats["answerers"], "judges": seats["judges"],
    })
    by_model = {}
    for row in rows:
        by_model.setdefault(routes[row["id"]][0]["model"], []).append(row)
    summary = {
        "skill": args.skill, "claims": len(claims), "reused_claims": reused,
        "fallback_claims": sum(fallback for _, _, _, fallback in scored),
        "buckets": bucket_counts(rows),
        "buckets_by_answerer": {model: bucket_counts(items) for model, items in by_model.items()},
        "artifacts": str(base),
    }
    if not args.score_only:
        before = disk_chars(directory)
        rewrite_skill(directory, rows, seats["implementer"], cache, queue)
        after = disk_chars(directory)
        summary.update(before_chars=before, proposed_chars=after)
        if after < before:
            for check in ("no-em-dashes.py", "no-semicolons.py", "use-when-descriptions.py"):
                subprocess.run([sys.executable, str(args.root / "scripts" / check), str(directory)],
                               stdout=sys.stderr, check=True)
            validations = validate_candidate(directory, rows, routes, cache, queue, args.concurrency)
            kept = [row for row, _, _ in validations]
            write_jsonl(base / "after" / "kept.jsonl", kept)
            write_jsonl(base / "after" / "answers.jsonl", (a for _, arms, _ in validations for a in arms))
            write_jsonl(base / "after" / "grades.jsonl", (g for _, _, grades in validations for g in grades))
            lost = [row["id"] for row in kept if row["status"] == "lost"]
            summary.update(checked_taught=len(kept), lost_taught=lost)
            if not lost:
                summary["requires_task_evals"] = True
    return summary


def load_seats(path, score_only):
    seats = read_json(path)
    answerers, judges = seats["answerers"], seats["judges"]
    families = [DRIVERS[seat["driverKind"]] for seat in answerers]
    if len(families) < 2 or len(families) != len(set(families)):
        raise ValueError("Configure at least two answerers, with one model per family")
    if set(judges) != set(families):
        raise ValueError("Configure a judge for each answerer family")
    for family, seat in judges.items():
        if DRIVERS[seat["driverKind"]] == family:
            raise ValueError(f"{family} needs a judge from a different family")
    active = [*answerers, *judges.values()]
    if not score_only:
        active.append(seats["implementer"])
    for seat in active:
        family = DRIVERS[seat["driverKind"]]
        if not seat["model"].startswith(family + "-") or not seat["effort"] or not seat["providerInstanceId"]:
            raise ValueError(f"Invalid {family} seat")
    return seats


def run(args):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.skill):
        raise ValueError("Pass a skill directory name")
    if args.timeout < 1 or args.concurrency < 1:
        raise ValueError("Timeout and concurrency must be positive")
    seats = load_seats(args.seats, args.score_only)
    start = time.monotonic()
    args.root = args.root.resolve()
    queue = RequestQueue(args.queue.resolve(), args.timeout)
    queue.directory.mkdir(parents=True)
    print(f"T3 requests: {queue.directory}", file=sys.stderr, flush=True)
    version = digest(PROTOCOL)
    cache = Cache(args.state.resolve() / version / digest(seats["answerers"]) / args.skill)
    target = args.state.resolve() / "artifacts" / args.skill
    target.mkdir(parents=True, exist_ok=True)
    artifacts = Path(tempfile.mkdtemp(prefix="run-", dir=target))
    print(f"Artifacts: {artifacts}", file=sys.stderr, flush=True)
    skill_path = Path("skills") / args.skill
    before, candidate = Path("before") / skill_path, Path("repo") / skill_path
    directory = artifacts / candidate
    shutil.copytree(args.root / skill_path, directory)
    if not args.score_only:
        shutil.copytree(directory, artifacts / before)
    summary = evaluate_skill(args, directory, artifacts, seats, cache, queue)
    if summary.get("requires_task_evals"):
        diff = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", before.as_posix(), candidate.as_posix()],
            cwd=artifacts, capture_output=True, check=False,
        )
        if diff.returncode != 1 or not diff.stdout:
            raise RuntimeError("Could not produce the shrink patch")
        patch = artifacts / "shrink.patch"
        patch.write_bytes(diff.stdout)
        summary["patch"] = str(patch)
    summary.update(seconds=round(time.monotonic() - start, 1), calls=dict(queue.stats))
    save_json(artifacts / "summary.json", summary)
    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("run")
    worker.add_argument("--root", type=Path, default=Path.cwd())
    worker.add_argument("--skill", required=True)
    worker.add_argument("--seats", type=Path, required=True)
    worker.add_argument("--state", type=Path, required=True)
    worker.add_argument("--queue", type=Path, required=True)
    worker.add_argument("--timeout", type=int, default=180)
    worker.add_argument("--concurrency", type=int, default=4)
    worker.add_argument("--score-only", action="store_true")
    requests = commands.add_parser("pending")
    requests.add_argument("--queue", type=Path, required=True)
    reply = commands.add_parser("reply")
    reply.add_argument("--queue", type=Path, required=True)
    reply.add_argument("--id", required=True)
    source = reply.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--error")
    args = parser.parse_args()
    if args.command == "run":
        run(args)
    elif args.command == "pending":
        pending(args.queue)
    elif re.fullmatch(r"[0-9a-f]{32}", args.id):
        submit_reply(args)
    else:
        parser.error("Invalid request ID")


if __name__ == "__main__":
    main()
