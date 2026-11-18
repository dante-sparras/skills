import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
BACKTICK_RUN = re.compile(r"`+")
FIX = "Rewrite the sentence, or use a comma, a period or a new sentence instead."


def prose_mask(line):
    mask = [True] * len(line)
    runs = list(BACKTICK_RUN.finditer(line))
    i = 0
    while i < len(runs):
        opener = runs[i]
        closer = next(
            (j for j in range(i + 1, len(runs)) if len(runs[j].group()) == len(opener.group())),
            None,
        )
        if closer is None:
            i += 1
            continue
        for k in range(opener.start(), runs[closer].end()):
            mask[k] = False
        i = closer + 1
    return mask


def prose_semicolons(text):
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence is None and match:
            fence = match.group(1)
            continue
        if fence is not None:
            closes = match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
            if closes and not line[match.end():].strip():
                fence = None
            continue
        prose = prose_mask(line)
        for column, char in enumerate(line, start=1):
            if char == ";" and prose[column - 1]:
                yield number, column


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
    found = 0
    for path in sorted(p for p in root.rglob("*.md") if p.is_file()):
        for line, column in prose_semicolons(path.read_text(encoding="utf-8")):
            found += 1
            print(f'{path.as_posix()}:{line}:{column}: found ";" (semicolon outside code). {FIX}')
    if found:
        print(f"\n{found} prose semicolon(s) in Markdown under {root.as_posix()}/.")
        return 1
    print(f"No prose semicolons in Markdown under {root.as_posix()}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
