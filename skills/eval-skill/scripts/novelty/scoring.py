from collections import Counter

from .clis import CallError
from .prompts import JUDGE_SYSTEM, PROTOCOL, TASK_SYSTEM, arm_prompt, judge_prompt, nonempty, parse_grade
from .textutil import digest, read_json, save_json

BUCKETS = ("already_known", "hurts", "teaches", "fails_both")
SCALES = ("lenient", "strict")
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
ROW_FIELDS = ("id", "kind", "source", "span", "question", "expected")


def bucket(without_pass, with_pass):
    if without_pass and with_pass:
        return "already_known"
    if without_pass:
        return "hurts"
    if with_pass:
        return "teaches"
    return "fails_both"


def decide(kind, lenient, strict):
    decision = DECISIONS[(lenient, strict)]
    return "keep" if kind == "process" and decision == "cut" else decision


def taught_scales(row):
    return [scale for scale in SCALES if row.get(f"bucket_{scale}") == "teaches"]


def held_status(row, grades):
    scales = taught_scales(row)
    if not scales:
        return "not-taught"
    for index, grade in enumerate(grades, start=1):
        if all(grade.get(scale) == "pass" for scale in scales):
            return "held" if index == 1 else "held-on-retry"
    return "lost"


def bucket_counts(rows):
    return {scale: {name: sum(1 for row in rows if row[f"bucket_{scale}"] == name) for name in BUCKETS}
            for scale in SCALES}


def classify(claim, without, with_skill, answerer, moved):
    row = {key: claim.get(key, "") for key in ROW_FIELDS}
    row.update(_blocks=claim["_blocks"], answerer=answerer.key, moved_answerer=moved,
               judges=sorted({without["judge"], with_skill["judge"]}))
    for scale in SCALES:
        row[f"bucket_{scale}"] = bucket(without[scale] == "pass", with_skill[scale] == "pass")
    row["decision"] = decide(claim["kind"], row["bucket_lenient"], row["bucket_strict"])
    for arm, result in (("without", without), ("with", with_skill)):
        row[f"{arm}_answer"] = result["answer"]
        row[f"{arm}_cached"] = result["cached"]
        for scale in SCALES:
            row[f"{arm}_{scale}"] = result[scale]
            row[f"{arm}_{scale}_reason"] = result[f"{scale}_reason"]
    return row


class Scorer:
    def __init__(self, caller, cache, panel, skill, arms, routes):
        self.caller = caller
        self.cache = cache
        self.panel = panel
        self.skill = skill
        self.arms = arms
        self.routes = routes

    def answer(self, question, arm, answerer, bundle, context):
        key = digest("answer", PROTOCOL, answerer.key, TASK_SYSTEM, arm_prompt(question, None),
                     None if bundle is None else context)
        return self.cache.get("without" if bundle is None else "with", key, lambda: self.caller.call(
            answerer, TASK_SYSTEM, arm_prompt(question, bundle), nonempty, f"answer-{arm}", self.skill))

    def grade(self, claim, answer, answerer):
        prompt = judge_prompt(claim, answer)
        errors = []
        for judge in self.panel.judges_for(answerer):
            key = digest("grade", PROTOCOL, judge.key, JUDGE_SYSTEM, prompt)
            try:
                grade, _ = self.cache.get("grades", key, lambda: self.caller.call(
                    judge, JUDGE_SYSTEM, prompt, parse_grade, "judge", self.skill))
                return dict(grade, judge=judge.key)
            except CallError as error:
                errors.append(str(error))
        raise CallError(f"no judge could grade claim {claim['id']}: {errors[-1]}")

    def arm(self, claim, arm, answerer, bundle, context):
        answer, cached = self.answer(claim["question"], arm, answerer, bundle, context)
        return dict(self.grade(claim, answer, answerer), arm=arm, answer=answer, cached=cached, answerer=answerer.key)

    def route_path(self, claim):
        return self.routes / f"{digest(claim['id'], claim['_blocks'])}.json"

    def claim(self, claim, bundle):
        answerers = self.panel.answerers
        start = read_json(self.route_path(claim), 0)
        errors = []
        for step in range(len(answerers)):
            offset = (start + step) % len(answerers)
            answerer = answerers[(int(claim["id"]) + offset) % len(answerers)]
            futures = [self.arms.submit(self.arm, claim, arm, answerer, bundle if arm == "with" else None,
                                        claim["_blocks"]) for arm in ("without", "with")]
            try:
                without, with_skill = [future.result() for future in futures]
            except CallError as error:
                errors.append(f"{answerer.key}: {error}")
                continue
            save_json(self.route_path(claim), offset)
            return classify(claim, without, with_skill, answerer, offset != start)
        return {"id": claim["id"], "kind": claim["kind"], "decision": "unscored", "errors": errors}

    def recheck(self, row, bundle, version):
        answerer = next(seat for seat in self.panel.answerers if seat.key == row["answerer"])
        grades = []
        for attempt in (1, 2):
            grades.append(self.arm(row, "with", answerer, bundle, [version, attempt]))
            if held_status(row, grades) != "lost":
                break
        return {"id": row["id"], "scales": taught_scales(row), "status": held_status(row, grades)}


def by_answerer(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["answerer"], []).append(row)
    return {seat: {scale: dict(Counter(row[f"bucket_{scale}"] for row in items)) for scale in SCALES}
            for seat, items in groups.items()}
