import subprocess
import sys

from .clis import CallError
from .prompts import PROTOCOL, REWRITE_GUARD
from .textutil import digest, forbidden_punctuation, normalize_ws, strip_fence

REWRITE_SYSTEM = "You edit one paragraph of an agent skill." + REWRITE_GUARD
DROP = "[[DROP_PARAGRAPH]]"
INSTRUCTIONS = {
    "cut": "Remove that span. The model already does it without being told.",
    "fix": "Rewrite that span so it no longer pulls the model off the behavior it already had. Keep any taught detail.",
    "rewrite": "Rewrite that span so the behavior is explicit enough that an agent following the paragraph will do it.",
}
CHECKS = ("no-em-dashes.py", "no-semicolons.py", "use-when-descriptions.py")


def kept_spans(rows):
    return [row["span"] for row in rows if row["decision"] == "keep" and row.get("span")]


def rewrite_prompt(paragraph, rows):
    keep = kept_spans(rows)
    lines = [
        "Edit the paragraph. Return only the edited paragraph.",
        "Do not add a semicolon or an em dash.",
        "Do not add a step the paragraph did not already contain.",
    ]
    if keep:
        lines += ["These spans must remain verbatim:", *keep]
    for row in rows:
        if row["decision"] == "keep":
            continue
        lines.append(
            f"Decision {row['decision']} on this span: {row.get('span', '')}\n"
            f"Lenient was {row.get('bucket_lenient')} ({row.get('with_lenient_reason', '')}). "
            f"Strict was {row.get('bucket_strict')} ({row.get('with_strict_reason', '')})."
        )
        lines.append(INSTRUCTIONS[row["decision"]])
    lines += ["Paragraph:", paragraph]
    return "\n".join(lines)


def accept_edit(keep):
    def accept(result):
        edited = "" if result.strip() == DROP else strip_fence(result)
        if forbidden_punctuation(edited):
            raise ValueError("the edit added an em dash or a prose semicolon")
        for span in keep:
            if span not in edited and normalize_ws(span) not in normalize_ws(edited):
                raise ValueError(f"the edit dropped a span that must stay verbatim: {span}")
        return edited
    return accept


def needs_rewrite(rows):
    return all(row["decision"] != "unscored" for row in rows) and any(row["decision"] != "keep" for row in rows)


def rewrite_paragraph(context, skill, paragraph, rows):
    if all(row["decision"] == "cut" for row in rows) and any(
            normalize_ws(row["span"]) == normalize_ws(paragraph) for row in rows):
        return ""
    seat = context.panel.implementer
    prompt = rewrite_prompt(paragraph, rows)
    try:
        key = digest("rewrite", PROTOCOL, context.identities.of(seat), REWRITE_SYSTEM, prompt)
        edited, _ = context.cache.get("rewrites", key, lambda: context.caller.call(
            seat, REWRITE_SYSTEM, prompt, accept_edit(kept_spans(rows)), "rewrite", skill))
        return edited
    except CallError:
        return paragraph


def repo_checks(root, directory):
    failures = []
    for check in CHECKS:
        script = root / "scripts" / check
        if script.is_file():
            result = subprocess.run([sys.executable, str(script), str(directory)], capture_output=True, text=True, check=False)
            if result.returncode:
                failures.append(f"{check}: {result.stdout.strip()[-400:]}")
    return failures


def write_patch(output, skill):
    diff = subprocess.run(
        ["git", "diff", "--no-index", "--binary", "--", f"before/skills/{skill}", f"repo/skills/{skill}"],
        cwd=output, capture_output=True, check=False,
    )
    patch = output / "candidate.patch"
    patch.write_bytes(diff.stdout)
    return patch
