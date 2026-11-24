"""Check each skill's description: it has a "Use when" sentence, and it is short.

A description stays in context on every turn, and an agent follows one that summarises the
skill's steps in place of the skill. So the steps stay in the body.
"""
import re
import sys
from pathlib import Path

USE_WHEN = re.compile(r"(?:^|[.!?]\s+)Use when\s+\S")
LIMIT = 350
FIX = (
    'Add a sentence after what the skill does that names its concrete triggers, such as '
    'description: "<What it does>. Use when <trigger>, <trigger>, or <trigger>." '
    "Skills with disable-model-invocation: true need one too, for the people who invoke them."
)


def frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return None
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return lines[1:end]
    return None


def description(header):
    for index, line in enumerate(header):
        if not line.startswith("description:"):
            continue
        parts = [line[len("description:"):].strip()]
        for follow in header[index + 1:]:
            if follow[:1] not in (" ", "\t"):
                break
            parts.append(follow.strip())
        value = " ".join(part for part in parts if part not in (">", "|", ">-", "|-"))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return index + 2, value
    return None


def problems(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header = frontmatter(lines)
    if header is None:
        yield 1, f"has no YAML frontmatter with a description. {FIX}"
        return
    found = description(header)
    if found is None:
        yield 2, f"has no description in its frontmatter. {FIX}"
        return
    line, value = found
    if not USE_WHEN.search(value):
        yield line, f'description has no "Use when" sentence. {FIX}'
    if len(value) > LIMIT:
        yield line, (
            f"description is {len(value)} characters, and the limit is {LIMIT}. Cut its summary of the "
            "skill's steps, which the body carries. Keep what the skill is, and one trigger per case."
        )


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
    skills = sorted(p for p in root.rglob("SKILL.md") if p.is_file())
    found = 0
    for path in skills:
        for line, problem in problems(path):
            found += 1
            print(f"{path.as_posix()}:{line}: {problem}")
    if found:
        print(f"\n{found} description problem(s) across {len(skills)} skill(s) under {root.as_posix()}/.")
        return 1
    print(
        f"All {len(skills)} skill descriptions under {root.as_posix()}/ have a \"Use when\" sentence "
        f"and stay within {LIMIT} characters."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
