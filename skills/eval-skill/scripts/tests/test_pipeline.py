import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import run
from novelty import seats
from novelty.clis import Adapter, CallError, Reply
from novelty.pipeline import run_skills
from novelty.prompts import CANARY_QUESTION, DRAFT_SYSTEM, JUDGE_SYSTEM

SKILL = """---
name: demo
description: "Demo skill. Use when testing."
---

Before you rename a column, write down the callers.

A 404 status code means the resource was not found.
"""
CLAIMS = [
    {"id": "a", "kind": "process", "source": "skills/demo/SKILL.md",
     "question": "The orders table column cust_id should be called customer_id. Change the schema.",
     "expected": "TAUGHT The agent writes down the callers first.",
     "span": "Before you rename a column, write down the callers."},
    {"id": "b", "kind": "fact", "source": "skills/demo/SKILL.md",
     "question": "What does an HTTP 404 response tell the client?",
     "expected": "KNOWN The resource was not found.",
     "span": "A 404 status code means the resource was not found."},
]


class Script:
    def __init__(self):
        self.calls = Counter()
        self.leak = False
        self.broken = set()


def fake_cli(name, script):
    class Fake(Adapter):
        def check_signin(self, chosen):
            return f"{name}: fake"

        def catalog(self):
            return "fake", []

        def ask(self, seat, system, prompt, cancel):
            with_skill = "<skill>" in prompt
            marker = re.search(r"isomark[0-9a-f]{8}", prompt)
            if system == DRAFT_SYSTEM:
                kind = "draft"
                text = json.dumps(CLAIMS)
            elif system == JUDGE_SYSTEM:
                kind = "judge"
                expected = prompt.split("Expected behavior:\n", 1)[1]
                reply = prompt.split("Agent reply:\n", 1)[1]
                passed = "KNOWN" in expected or reply.startswith("WITH ")
                verdict = "pass" if passed else "fail"
                text = json.dumps({"lenient": verdict, "strict": verdict, "lenient_reason": "r", "strict_reason": "r"})
            elif CANARY_QUESTION in prompt:
                kind = "canary"
                text = marker.group(0) if with_skill else "NONE"
            elif system.startswith("You edit one paragraph"):
                kind = "rewrite"
                text = "[[DROP_PARAGRAPH]]"
            else:
                kind = "answer-with" if with_skill else "answer-without"
                if name in script.broken:
                    script.calls[f"{name}-failed"] += 1
                    raise CallError("broken on purpose")
                leak = f" {script.leak}" if script.leak and not with_skill else ""
                text = ("WITH " if with_skill else "WITHOUT ") + "plan" + leak
            script.calls[kind] += 1
            return Reply(text, (seat.model,))

    Fake.name = name
    return Fake


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "skills" / "demo" / "SKILL.md").write_text(SKILL, encoding="utf-8")
        patcher = mock.patch.object(seats, "USER_PANEL", self.root / "missing.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.script = Script()
        self.adapters = {name: fake_cli(name, self.script) for name in seats.CLIS}

    def run_demo(self, *flags):
        args = run.parse_args(["run", "--skill", "demo", "--root", str(self.root),
                               "--state", str(self.root / "state"), *flags])
        with mock.patch("novelty.pipeline.log"):
            result, _, passed = run_skills(args, ["demo"], self.adapters)
        return result["skills"][0] if result["skills"] else result, passed

    def test_scores_isolates_and_proposes_a_shorter_skill(self):
        summary, passed = self.run_demo()
        self.assertTrue(passed)
        self.assertEqual(summary["buckets"]["lenient"], {"already_known": 1, "hurts": 0, "teaches": 1, "fails_both": 0})
        self.assertTrue(summary["isolation"]["passed"])
        self.assertEqual(summary["proposal"]["status"], "proposed")
        self.assertEqual(summary["lost_taught"], [])
        patch = Path(summary["proposal"]["patch"]).read_text(encoding="utf-8")
        self.assertIn("-A 404 status code means the resource was not found.", patch)

    def assert_leak_fails(self, leak):
        markers = self.root / "state" / "v5" / "skills" / "demo" / "markers.json"
        markers.parent.mkdir(parents=True)
        markers.write_text(json.dumps(["isomarkdeadbeef"]))
        self.script.leak = leak
        summary, passed = self.run_demo("--score-only")
        self.assertFalse(passed)
        self.assertFalse(summary["isolation"]["passed"])
        self.assertTrue(any(leak in problem for problem in summary["isolation"]["problems"]))

    def test_an_earlier_marker_in_a_without_answer_fails_the_run(self):
        self.assert_leak_fails("isomarkdeadbeef")

    def test_a_skill_reference_in_a_without_answer_fails_the_run(self):
        self.assert_leak_fails("skills/demo")

    def test_a_failing_answerer_moves_claims_to_the_next_one(self):
        self.script.broken = {"claude"}
        summary, passed = self.run_demo("--score-only")
        self.assertTrue(passed)
        self.assertEqual(summary["unscored"], [])
        self.assertTrue(summary["moved_answerer"])
        self.assertGreater(self.script.calls["claude-failed"], 0)

    def test_a_rerun_reuses_every_answer_and_grade(self):
        self.run_demo("--score-only")
        before = Counter(self.script.calls)
        summary, passed = self.run_demo("--score-only")
        new = self.script.calls - before
        self.assertTrue(passed)
        self.assertEqual(summary["reused_claims"], 2)
        self.assertEqual(set(new), {"canary"})


if __name__ == "__main__":
    unittest.main()
