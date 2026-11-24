"""Tests for skills/coordinate/factory.ts, the T3 Code workflow. Needs Node 18 or newer."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACTORY = REPO / "skills" / "coordinate" / "factory.ts"
HARNESS = Path(__file__).resolve().parent / "factory_harness.mjs"

BLOCKERS = [
    ("Blocked by: #12, #14\n\nThe rest of the body.", ["12", "14"]),
    ("**Blocked by:** #3", ["3"]),
    ("## What\nx\n\n## Blocked by\n\n- #7\n- #9\n\n## Next\n#99", ["7", "9"]),
    ("## Blocked by\n- #7\n## Next\n#99", ["7"]),
    ("## Blocked by\n\nNone", []),
    ("Fixes #5. Nothing blocks it.", []),
    (None, []),
]


@unittest.skipUnless(shutil.which("node"), "Node is not installed")
class Factory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = {"blockers": [body for body, _ in BLOCKERS], "numbers": ["#526", "526"]}
        done = subprocess.run(
            ["node", str(HARNESS), str(FACTORY), json.dumps(cases)], capture_output=True, text=True, cwd=REPO
        )
        if done.returncode:
            raise AssertionError(f"factory.ts did not load under the harness:\n{done.stderr}")
        cls.out = json.loads(done.stdout.strip().splitlines()[-1])

    def test_registers_both_workflows(self):
        # setup-skills, factory.md and the dispatcher's own `start` name these. Rename them together.
        self.assertEqual(self.out["registered"], ["skills-factory-ship", "skills-factory-dispatch"])

    def test_finds_blockers_in_an_issue_body(self):
        for (body, want), got in zip(BLOCKERS, self.out["blockers"]):
            with self.subTest(body=body):
                self.assertEqual(got, want)

    def test_issue_number_drops_the_hash(self):
        self.assertEqual(self.out["numbers"], ["526", "526"])


if __name__ == "__main__":
    unittest.main()
