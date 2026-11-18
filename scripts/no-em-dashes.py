import sys
from pathlib import Path

EM_DASH = "\N{EM DASH}"
FIX = "Rewrite the sentence, or use a comma, a period or a new sentence instead."


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
    found = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for column, char in enumerate(text, start=1):
                if char == EM_DASH:
                    found += 1
                    print(f'{path.as_posix()}:{line}:{column}: found "{EM_DASH}" (em dash, U+2014). {FIX}')
    if found:
        print(f"\n{found} em dash(es) under {root.as_posix()}/.")
        return 1
    print(f"No em dashes under {root.as_posix()}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
