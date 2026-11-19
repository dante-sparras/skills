import json
import statistics
from collections import defaultdict

BUCKET_COLUMNS = ("already_known", "hurts", "teaches", "fails_both")
LEGEND = ("Cells give the lenient then strict bucket per answerer: K already known, H hurts, T teaches, F fails both. "
          "~ marks a cell whose samples disagreed. Overall is the most severe bucket across answerers, in the order "
          "hurts, teaches, fails both, already known.")


def call_stats(records):
    groups = defaultdict(list)
    for record in records:
        groups[(record["kind"], record["seat"])].append(record)
    rows = []
    for (kind, seat), items in sorted(groups.items()):
        seconds = sorted(item["ended_at"] - item["started_at"] for item in items)
        rows.append({
            "kind": kind, "seat": seat, "calls": len(items),
            "failed": sum(1 for item in items if not item["ok"]),
            "hedged": sum(1 for item in items if item.get("hedged")),
            "p50": round(statistics.median(seconds), 1),
            "p90": round(seconds[min(len(seconds) - 1, int(len(seconds) * 0.9))], 1),
            "max": round(seconds[-1], 1),
            "mean_slot_wait": round(statistics.mean(item["started_at"] - item["queued_at"] for item in items), 1),
            "models": sorted({model for item in items for model in item.get("models", [])}),
        })
    return rows


def table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
            *("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)]


def panel_section(result):
    panel = result["panel"]
    judges = ", ".join(f"{family} answers by {seat}" for family, seat in panel["judges"].items())
    models = ", ".join(f"{seat} is {model}" for seat, model in result["models"].items())
    lines = [
        f"# Novelty run {result['run']}", "",
        f"Wall time {result['wall_seconds']}s. Panel: answerers {', '.join(panel['answerers'])}. Judges {judges}. "
        f"Drafter {panel['drafter']}. Implementer {panel['implementer']}. "
        f"Up to {result['samples']} samples per arm, decided by majority.",
        "", f"Models: {models}.",
    ]
    if result.get("panel_note"):
        lines += ["", result["panel_note"]]
    return lines + ["", "Billing: " + ". ".join(result["billing"]) + "."]


def isolation_lines(isolation):
    canaries = " ".join(
        f"{seat} echoed {pair.get('with', '')[:40]!r} with the skill and {pair.get('without', '')[:40]!r} without."
        for seat, pair in isolation["canary"].items())
    status = "passed" if isolation["passed"] else "FAILED"
    return [f"Isolation {status}: marker {isolation['marker']} absent from {isolation['without_answers_checked']} "
            f"without-skill answers, checked against {isolation['markers_checked']} markers and the skill name. {canaries}",
            *(f"- {problem}" for problem in isolation["problems"])]


def claim_notes(summary):
    lines = []
    for item in summary["rejected_claims"]:
        lines.append(f"- Rejected by review: {item['span'][:80]!r}. {item['reason']}")
    for item in summary["unreviewed_claims"]:
        lines.append(f"- Kept without review: {item['span'][:80]!r}. {item['reason']}")
    for item in summary["missing_cells"]:
        lines.append(f"- Claim {item['claim']} has no score from {item['answerer']}: {item['error']}")
    for claim, cells in summary["unstable"].items():
        lines.append(f"- Claim {claim} samples disagreed: " +
                     ", ".join(f"{seat} {', '.join(arms)}" for seat, arms in cells.items()))
    return lines


def skill_section(summary, answerers):
    lines = ["", f"## {summary['skill']}", "",
             f"Claims {summary['claims']} ({summary['reused_claims']} reused, {summary['dropped_claims']} invalid "
             f"drafts dropped, {len(summary['rejected_claims'])} rejected by review). Unscored {len(summary['unscored'])}.",
             *isolation_lines(summary["isolation"]), ""]
    lines += table(("Grade", "already known", "hurts", "teaches", "fails both"),
                   [(scale, *(summary["buckets"][scale][name] for name in BUCKET_COLUMNS)) for scale in ("lenient", "strict")])
    lines.append("")
    lines += table(("Answerer", "Grade", "already known", "hurts", "teaches", "fails both"),
                   [(seat, scale, *(counts[scale][name] for name in BUCKET_COLUMNS))
                    for seat, counts in summary["buckets_by_answerer"].items() for scale in ("lenient", "strict")])
    lines += ["", LEGEND, ""]
    lines += table(("Claim", "Kind", *answerers, "Overall", "Decision", "Span"), [
        (row["id"], row["kind"], *(row["cells"].get(seat, "-") for seat in answerers),
         f"{row.get('bucket_lenient') or '-'}/{row.get('bucket_strict') or '-'}", row["decision"],
         (row.get("span") or "").replace("|", "/").replace("\n", " ")[:90])
        for row in summary["rows"]])
    notes = claim_notes(summary)
    if notes:
        lines += [""] + notes
    proposal = summary.get("proposal")
    if proposal:
        lines += ["", f"Proposal: {proposal['status']}. {proposal.get('reason', '')} "
                      f"{summary.get('before_chars')} to {summary.get('proposed_chars')} characters."]
        if proposal.get("patch"):
            lines.append(f"Patch: {proposal['patch']}. Task evals: {proposal['task_evals']['status']}.")
    lines.append("")
    lines += table(("Step", "Start s", "End s", "Seconds"),
                   [(step, entry.get("start"), entry.get("end"), entry.get("seconds")) for step, entry in summary["steps"].items()])
    return lines


def render_report(result):
    lines = panel_section(result)
    for summary in result["skills"]:
        lines += skill_section(summary, result["panel"]["answerers"])
    lines.append("")
    lines += table(("Call", "Seat", "Calls", "Failed", "Hedged", "p50 s", "p90 s", "Max s", "Mean slot wait s"), [
        (row["kind"], row["seat"], row["calls"], row["failed"], row["hedged"], row["p50"], row["p90"], row["max"],
         row["mean_slot_wait"]) for row in result["calls"]])
    lines.append(f"\nCache hits: {json.dumps(result['cache_hits'])}.")
    return "\n".join(lines) + "\n"
