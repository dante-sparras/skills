import re
import secrets

from .prompts import CANARY_QUESTION, TASK_SYSTEM, arm_prompt
from .clis import CallError
from .scoring import without_answers
from .textutil import read_json, save_json


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


class Markers:
    def __init__(self, path):
        self.path = path
        self.current = "isomark" + secrets.token_hex(4)
        self.all = [*read_json(path, []), self.current]
        save_json(path, self.all)

    def found_in(self, text):
        lowered = (text or "").lower()
        return [marker for marker in self.all if marker.lower() in lowered]


def canary(caller, seat, arm, bundle, marker, skill):
    def parse(text):
        if arm == "with" and marker.lower() not in text.lower():
            raise CallError("the with-skill arm did not echo the marker")
        return text

    prompt = arm_prompt(CANARY_QUESTION, bundle if arm == "with" else None)
    try:
        text = caller.call(seat, TASK_SYSTEM, prompt, parse, "canary", skill, repair=False)
        return {"seat": seat.key, "arm": arm, "answer": text[:300], "ok": True}
    except CallError as error:
        return {"seat": seat.key, "arm": arm, "error": str(error), "ok": False}


def verdict(name, markers, rows, canaries):
    problems = []
    checked = 0
    for row in rows:
        for answer in without_answers(row):
            checked += 1
            for found in dict.fromkeys([*markers.found_in(answer), *name_hits(answer, name)]):
                problems.append(f"claim {row['id']} without-skill answer contains {found!r}")
    for result in canaries:
        if not result["ok"]:
            problems.append(f"{result['seat']} {result['arm']} canary failed: {result['error']}")
        elif result["arm"] == "without" and markers.found_in(result["answer"]):
            problems.append(f"{result['seat']} without-skill canary returned the marker")
    by_seat = {}
    for result in canaries:
        by_seat.setdefault(result["seat"], {})[result["arm"]] = result.get("answer", result.get("error", ""))[:120]
    return {
        "marker": markers.current,
        "markers_checked": len(markers.all),
        "without_answers_checked": checked,
        "canary": by_seat,
        "passed": not problems,
        "problems": problems,
    }
