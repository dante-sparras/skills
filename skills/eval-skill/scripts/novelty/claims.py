import json
import re
import threading
from collections import defaultdict

from . import skillfiles
from .clis import CallError
from .isolation import name_hits
from .prompts import DRAFT_SYSTEM, PROTOCOL, REVIEW_SYSTEM, parse_review, review_prompt
from .textutil import digest, json_between, normalize_ws, read_json, save_json, tokens

FIELDS = ("id", "kind", "question", "expected", "span", "source")
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


def grams(text):
    words = tokens(text)
    return {" ".join(words[index:index + 4]) for index in range(len(words) - 3)
            if sum(1 for word in words[index:index + 4] if word not in STOP) >= 2}


def leak_grams(question, span, kind):
    span_grams = grams(span)
    shared = sorted(grams(question) & span_grams)
    if kind == "fact" and len(shared) * 2 <= len(span_grams):
        return []
    return shared


def claim_errors(claim, text, name):
    if not isinstance(claim, dict):
        return ["is not an object"]
    errors = [f"missing {key}" for key in FIELDS if not str(claim.get(key) or "").strip()]
    kind = claim.get("kind")
    question, expected, span = (str(claim.get(key) or "") for key in ("question", "expected", "span"))
    if kind not in ("process", "fact"):
        errors.append("kind must be process or fact")
    if span and span not in text and normalize_ws(span) not in normalize_ws(text):
        errors.append("span is not in the skill text")
    leaks = leak_grams(question, span, kind)
    if leaks:
        errors.append(f"question leaks the instruction: {leaks[0]}")
    if kind == "process" and META_QUESTION.search(question):
        errors.append("process question asks for an explanation")
    expected_words = " ".join(tokens(expected))
    if kind == "fact" and expected_words and f" {expected_words} " in f" {' '.join(tokens(question))} ":
        errors.append("fact question contains the expected answer")
    if re.search(r"\bskill\b", question, re.I) or name_hits(question, name, bare=True):
        errors.append("question names the skill")
    if "—" in json.dumps(claim, ensure_ascii=False) or ";" in question + expected:
        errors.append("uses a semicolon or an em dash")
    return errors


def validate_claims(claims, text, limit, name, allow_empty=False):
    if not isinstance(claims, list):
        return ["draft is not a JSON array"]
    errors = [f"more than {limit} claims"] if len(claims) > limit else []
    if not claims and not allow_empty:
        errors.append("no claims")
    ids = [claim.get("id") for claim in claims if isinstance(claim, dict)]
    errors += [f"{identifier} duplicate id" for identifier in sorted({i for i in ids if ids.count(i) > 1}, key=str)]
    for index, claim in enumerate(claims):
        label = str(claim.get("id") or index) if isinstance(claim, dict) else str(index)
        errors += [f"{label} {error}" for error in claim_errors(claim, text, name)]
    return errors


def anchor(claim):
    source = re.split(r"(?<=\.md):|(?<=\.sh):", claim["source"], maxsplit=1)[0]
    return source, normalize_ws(claim["span"])


def with_blocks(claim, paragraphs):
    return dict(claim, _blocks=skillfiles.span_paragraphs(claim["span"], anchor(claim)[0], paragraphs))


class ClaimBook:
    def __init__(self, path, paragraphs, max_claims):
        self.path = path
        self.paragraphs = paragraphs
        previous = read_json(path, {"blocks": [], "claims": [], "next": 0})
        unchanged = set(previous["blocks"]) & paragraphs.keys()
        self.claims = [claim for claim in previous["claims"] if set(claim["_blocks"]) <= unchanged]
        self.reused = len(self.claims)
        kept = {claim["id"] for claim in self.claims}
        self.prior = {anchor(claim): claim for claim in previous["claims"] if claim["id"] not in kept}
        self.next_id = previous["next"]
        self.dropped = 0
        self.lock = threading.Lock()
        changed = defaultdict(list)
        for key, (source, paragraph) in paragraphs.items():
            if key not in unchanged:
                changed[source].append(paragraph)
        self.changed = {source: f"<!-- {source} -->\n" + "\n\n".join(items) for source, items in changed.items()}
        self.budget = max(1, max_claims - len(self.claims))

    def limit(self, source):
        if len(self.changed) == 1:
            return self.budget
        total = sum(len(text) for text in self.changed.values()) or 1
        return max(1, int(self.budget * len(self.changed[source]) / total))

    def admit(self, drafted):
        admitted = []
        with self.lock:
            for claim in drafted:
                old = self.prior.pop(anchor(claim), None)
                if old and old["kind"] == claim["kind"]:
                    claim.update(id=old["id"], question=old["question"], expected=old["expected"])
                else:
                    claim["id"] = str(self.next_id)
                    self.next_id += 1
                self.claims.append(claim)
                admitted.append(claim)
        return admitted

    def save(self):
        save_json(self.path, {"blocks": list(self.paragraphs), "claims": self.claims, "next": self.next_id})


def manifest_path(state, drafter):
    return state / f"claims-{digest(DRAFT_SYSTEM, drafter.key)[:12]}.json"


def draft(caller, seat, skill, text, limit, paragraphs, allow_empty):
    prompt = f"Skill name: {skill}\nReturn at most {limit} claims.\n\n{text}"
    salvage = {"claims": [], "dropped": 0}

    def parse(reply):
        drafted = json_between(reply, "[", "]", "draft")
        if not isinstance(drafted, list):
            raise ValueError("draft JSON is not an array")
        errors = validate_claims(drafted, text, limit, skill, allow_empty)
        if not errors:
            return [with_blocks(claim, paragraphs) for claim in drafted], 0
        valid = []
        for claim in drafted:
            if not claim_errors(claim, text, skill):
                try:
                    valid.append(with_blocks(claim, paragraphs))
                except ValueError:
                    pass
        salvage.update(claims=valid[:limit], dropped=len(drafted) - len(valid[:limit]))
        raise ValueError("; ".join(errors[:12]))

    try:
        return caller.call(seat, DRAFT_SYSTEM, prompt, parse, "draft", skill)
    except CallError:
        if not salvage["claims"]:
            raise
        return salvage["claims"], salvage["dropped"]


class Reviewer:
    def __init__(self, context, skill, paragraphs):
        self.caller = context.caller
        self.cache = context.cache
        self.identities = context.identities
        self.drafter = context.panel.drafter
        self.seat = context.panel.judges_for(self.drafter)[0]
        self.skill = skill
        self.paragraphs = paragraphs

    def verdict(self, claim, text):
        prompt = review_prompt(claim, text)
        key = digest("review", PROTOCOL, self.identities.of(self.seat), REVIEW_SYSTEM, prompt)
        result, _ = self.cache.get("reviews", key, lambda: self.caller.call(
            self.seat, REVIEW_SYSTEM, prompt, parse_review, "review", self.skill))
        problems = [name for name, bad in (("leaks", result["leaks"]), ("unfaithful", not result["faithful"])) if bad]
        return problems, result["reason"]

    def repair(self, claim, problems, reason, text):
        prompt = (f"Skill name: {self.skill}\nA reviewer rejected this claim as {' and '.join(problems)}: {reason}\n"
                  "Return a JSON array with exactly one corrected claim for the same span.\n\n"
                  f"Claim:\n{json.dumps({key: claim[key] for key in FIELDS}, ensure_ascii=False)}\n\n{text}")

        def parse(reply):
            fixed = json_between(reply, "[", "]", "repair")
            errors = validate_claims(fixed, text, 1, self.skill)
            if errors:
                raise ValueError("; ".join(errors))
            return with_blocks(fixed[0], self.paragraphs)

        return self.caller.call(self.drafter, DRAFT_SYSTEM, prompt, parse, "repair", self.skill)

    def review(self, claim, text):
        try:
            problems, reason = self.verdict(claim, text)
        except CallError as error:
            return claim, f"kept unreviewed: {error}"[:300]
        if not problems:
            return claim, None
        first = f"{' and '.join(problems)}: {reason}"
        try:
            fixed = self.repair(claim, problems, reason, text)
            problems, reason = self.verdict(fixed, text)
        except CallError as error:
            return None, f"{first} Repair failed: {error}"[:400]
        if not problems:
            return fixed, None
        return None, f"{first} Still {' and '.join(problems)} after repair: {reason}"[:400]
