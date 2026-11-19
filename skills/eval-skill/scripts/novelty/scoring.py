from collections import Counter

from .clis import CallError
from .prompts import JUDGE_SYSTEM, PROTOCOL, TASK_SYSTEM, arm_prompt, judge_prompt, nonempty, parse_grade
from .textutil import digest

BUCKETS = ("already_known", "hurts", "teaches", "fails_both")
PRECEDENCE = ("hurts", "teaches", "fails_both", "already_known")
SHORT = {"already_known": "K", "hurts": "H", "teaches": "T", "fails_both": "F"}
SCALES = ("lenient", "strict")
ARMS = ("without", "with")
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


def combine(buckets):
    return next(name for name in PRECEDENCE if name in buckets)


def decide(kind, lenient, strict):
    decision = DECISIONS[(lenient, strict)]
    return "keep" if kind == "process" and decision == "cut" else decision


def taught_scales(item):
    return [scale for scale in SCALES if item.get(f"bucket_{scale}") == "teaches"]


def majority(results, scale, need):
    votes = Counter(result[scale] for result in results)
    return "pass" if votes["pass"] >= need else "fail" if votes["fail"] >= need else None


def tally(arm, results, need):
    summary = {"arm": arm, "answers": [result["answer"] for result in results],
               "judges": sorted({result["judge"] for result in results}),
               "cached": all(result["cached"] for result in results), "unstable": []}
    for scale in SCALES:
        verdict = majority(results, scale, need) or Counter(result[scale] for result in results).most_common(1)[0][0]
        summary[scale] = verdict
        summary[f"{scale}_votes"] = "".join(result[scale][0].upper() for result in results)
        summary[f"{scale}_reason"] = next(result[f"{scale}_reason"] for result in results if result[scale] == verdict)
        if len({result[scale] for result in results}) > 1:
            summary["unstable"].append(scale)
    return summary


def make_cell(without, with_skill):
    cell = {"without": without, "with": with_skill,
            "unstable": sorted({f"{arm['arm']} {scale}" for arm in (without, with_skill) for scale in arm["unstable"]})}
    for scale in SCALES:
        cell[f"bucket_{scale}"] = bucket(without[scale] == "pass", with_skill[scale] == "pass")
    return cell


def make_row(claim, cells, missing):
    row = {key: claim.get(key, "") for key in ROW_FIELDS}
    row.update(_blocks=claim["_blocks"], cells=cells, missing=missing)
    if not cells:
        row["decision"] = "unscored"
        return row
    for scale in SCALES:
        row[f"bucket_{scale}"] = combine([cell[f"bucket_{scale}"] for cell in cells.values()])
        source = next(cell for cell in cells.values() if cell[f"bucket_{scale}"] == row[f"bucket_{scale}"])
        row[f"with_{scale}_reason"] = source["with"][f"{scale}_reason"]
    row["decision"] = decide(claim["kind"], row["bucket_lenient"], row["bucket_strict"])
    row["unstable"] = {seat: cell["unstable"] for seat, cell in cells.items() if cell["unstable"]}
    return row


def without_answers(row):
    return [answer for cell in row.get("cells", {}).values() for answer in cell["without"]["answers"]]


def bucket_counts(items):
    return {scale: {name: sum(1 for item in items if item[f"bucket_{scale}"] == name) for name in BUCKETS}
            for scale in SCALES}


def by_answerer(rows, answerers):
    return {seat.key: bucket_counts([row["cells"][seat.key] for row in rows if seat.key in row.get("cells", {})])
            for seat in answerers}


class Scorer:
    def __init__(self, context, skill):
        self.caller = context.caller
        self.cache = context.cache
        self.panel = context.panel
        self.identities = context.identities
        self.arms = context.arms
        self.samples = context.samples
        self.count = context.args.samples
        self.skill = skill

    def answer(self, question, arm, answerer, bundle, context, index):
        key = digest("answer", PROTOCOL, self.identities.of(answerer), TASK_SYSTEM, arm_prompt(question, None),
                     None if bundle is None else context, index)
        return self.cache.get("without" if bundle is None else "with", key, lambda: self.caller.call(
            answerer, TASK_SYSTEM, arm_prompt(question, bundle), nonempty, f"answer-{arm}", self.skill))

    def grade(self, claim, answer, answerer):
        prompt = judge_prompt(claim, answer)
        errors = []
        for judge in self.panel.judges_for(answerer):
            try:
                key = digest("grade", PROTOCOL, self.identities.of(judge), JUDGE_SYSTEM, prompt)
                grade, _ = self.cache.get("grades", key, lambda: self.caller.call(
                    judge, JUDGE_SYSTEM, prompt, parse_grade, "judge", self.skill))
                return dict(grade, judge=judge.key)
            except CallError as error:
                errors.append(str(error))
        raise CallError(f"no judge could grade claim {claim['id']}: {errors[-1]}")

    def sample(self, claim, arm, answerer, bundle, context, index):
        answer, cached = self.answer(claim["question"], arm, answerer, bundle, context, index)
        return dict(self.grade(claim, answer, answerer), answer=answer, cached=cached)

    def vote(self, claim, arm, answerer, bundle, context):
        need = self.count // 2 + 1
        results = list(self.samples.map(lambda index: self.sample(claim, arm, answerer, bundle, context, index),
                                        range(need)))
        while len(results) < self.count and not all(majority(results, scale, need) for scale in SCALES):
            results.append(self.sample(claim, arm, answerer, bundle, context, len(results)))
        return tally(arm, results, need)

    def claim(self, claim, bundle):
        futures = {(seat.key, arm): self.arms.submit(self.vote, claim, arm, seat, bundle if arm == "with" else None,
                                                     claim["_blocks"])
                   for seat in self.panel.answerers for arm in ARMS}
        cells, missing = {}, []
        for seat in self.panel.answerers:
            try:
                cells[seat.key] = make_cell(futures[(seat.key, "without")].result(), futures[(seat.key, "with")].result())
            except CallError as error:
                missing.append({"answerer": seat.key, "error": str(error)[:300]})
        return make_row(claim, cells, missing)

    def recheck(self, row, bundle, version):
        statuses = {}
        for seat in self.panel.answerers:
            cell = row["cells"].get(seat.key)
            scales = taught_scales(cell or {})
            if not scales:
                continue
            try:
                result = self.vote(row, "with", seat, bundle, [version])
                statuses[seat.key] = "held" if all(result[scale] == "pass" for scale in scales) else "lost"
            except CallError as error:
                statuses[seat.key] = f"unchecked: {error}"[:200]
        status = "lost" if any(value != "held" for value in statuses.values()) else "held"
        return {"id": row["id"], "status": status, "answerers": statuses}
