import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKS = [
    ["scripts/no-em-dashes.py", "skills"],
    ["scripts/no-semicolons.py", "skills"],
    ["scripts/use-when-descriptions.py", "skills"],
    ["scripts/check-skills.py", "."],
    ["scripts/no-comments.py", "."],
    ["-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py", "-q"],
]


def main():
    failed = []
    for args in CHECKS:
        label = " ".join(args)
        print(f"== {label}", flush=True)
        if subprocess.run([sys.executable, *args], cwd=REPO).returncode:
            failed.append(label)
    if failed:
        print(f"\n{len(failed)} of {len(CHECKS)} checks failed: " + ", ".join(failed))
        return 1
    print(f"\nAll {len(CHECKS)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
