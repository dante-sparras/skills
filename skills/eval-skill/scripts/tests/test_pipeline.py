import json
import re
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import run
from novelty import seats
from novelty.clis import Adapter, CallError, Reply
from novelty.pipeline import run_skills
from novelty.prompts import CANARY_QUESTION, DRAFT_SYSTEM, JUDGE_SYSTEM, PROBE_PROMPT, REVIEW_SYSTEM

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
        self.lock = threading.Lock()
        self.leak = ""
        self.broken = set()
        self.model = "fake-1"
        self.flaky = False
        self.flag_question = None
        self.repaired_question = None

    def count(self, kind):
        with self.lock:
            self.calls[kind] += 1
            return self.calls[kind]


def judge_reply(script, prompt):
    expected = prompt.split("Expected behavior:\n", 1)[1]
    reply = prompt.split("Agent reply:\n", 1)[1]
    passed = "KNOWN" in expected or reply.startswith("WITH ")
    if script.flaky and "KNOWN" in expected and reply.startswith("WITHOUT"):
        passed = script.count("flaky-judge") % 2 == 1
    verdict = "pass" if passed else "fail"
    return json.dumps({"lenient": verdict, "strict": verdict, "lenient_reason": "r", "strict_reason": "r"})


def fake_cli(name, script):
    class Fake(Adapter):
        def check_signin(self, chosen):
            return f"{name}: fake"

        def catalog(self):
            return "fake", []

        def ask(self, seat, system, prompt, cancel):
            with_skill = "<skill>" in prompt
            if prompt == PROBE_PROMPT:
                kind, text = "probe", "OK"
            elif system == DRAFT_SYSTEM and "rejected this claim" in prompt:
                kind = "repair"
                text = json.dumps([dict(CLAIMS[1], question=script.repaired_question)])
            elif system == DRAFT_SYSTEM:
                kind, text = "draft", json.dumps(CLAIMS)
            elif system == REVIEW_SYSTEM:
                kind = "review"
                leaks = script.flag_question is not None and f"Question:\n{script.flag_question}\n" in prompt
                text = json.dumps({"leaks": leaks, "faithful": True, "reason": "r"})
            elif system == JUDGE_SYSTEM:
                kind, text = "judge", judge_reply(script, prompt)
            elif CANARY_QUESTION in prompt:
                kind = "canary"
                text = re.search(r"isomark[0-9a-f]{8}", prompt).group(0) if with_skill else "NONE"
            elif system.startswith("You edit one paragraph"):
                kind, text = "rewrite", "[[DROP_PARAGRAPH]]"
            else:
                kind = "answer-with" if with_skill else "answer-without"
                if name in script.broken:
                    script.count(f"{name}-failed")
                    raise CallError("broken on purpose")
                leak = f" {script.leak}" if script.leak and not with_skill else ""
                text = ("WITH " if with_skill else "WITHOUT ") + f"plan {script.count('variant')}" + leak
            script.count(kind)
            return Reply(text, (f"{seat.model}-{script.model}",))

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
        return result["skills"][0], passed

    def test_scores_every_answerer_and_proposes_a_shorter_skill(self):
        summary, passed = self.run_demo()
        self.assertTrue(passed)
        self.assertEqual(summary["buckets"]["lenient"], {"already_known": 1, "hurts": 0, "teaches": 1, "fails_both": 0})
        self.assertEqual(len(summary["buckets_by_answerer"]), 3)
        for counts in summary["buckets_by_answerer"].values():
            self.assertEqual(counts["strict"]["teaches"], 1)
        self.assertEqual(self.script.calls["answer-without"], 2 * 3 * 2)
        self.assertTrue(summary["isolation"]["passed"])
        self.assertEqual(summary["proposal"]["status"], "proposed")
        patch = Path(summary["proposal"]["patch"]).read_text(encoding="utf-8")
        self.assertIn("-A 404 status code means the resource was not found.", patch)

    def assert_leak_fails(self, leak):
        markers = self.root / "state" / "v6" / "skills" / "demo" / "markers.json"
        markers.parent.mkdir(parents=True)
        markers.write_text(json.dumps(["isomarkdeadbeef"]))
        self.script.leak = leak
        summary, passed = self.run_demo("--score-only")
        self.assertFalse(passed)
        self.assertTrue(any(leak in problem for problem in summary["isolation"]["problems"]))

    def test_an_earlier_marker_in_a_without_answer_fails_the_run(self):
        self.assert_leak_fails("isomarkdeadbeef")

    def test_a_skill_reference_in_a_without_answer_fails_the_run(self):
        self.assert_leak_fails("skills/demo")

    def test_a_failing_answerer_leaves_missing_cells_not_unscored_claims(self):
        self.script.broken = {"claude"}
        summary, passed = self.run_demo("--score-only")
        self.assertTrue(passed)
        self.assertEqual(summary["unscored"], [])
        self.assertEqual({cell["answerer"] for cell in summary["missing_cells"]}, {"claude:sonnet:low"})

    def test_disagreeing_samples_take_a_third_sample_and_are_flagged(self):
        self.script.flaky = True
        summary, _ = self.run_demo("--score-only")
        self.assertTrue(summary["unstable"])
        self.assertGreater(self.script.calls["answer-without"], 2 * 3 * 2)

    def test_a_rerun_reuses_everything_until_the_model_changes(self):
        self.run_demo("--score-only")
        before = Counter(self.script.calls)
        summary, passed = self.run_demo("--score-only")
        self.assertTrue(passed)
        self.assertEqual(summary["reused_claims"], 2)
        self.assertEqual(set(self.script.calls - before), {"canary", "probe"})
        self.script.model = "fake-2"
        before = Counter(self.script.calls)
        self.run_demo("--score-only")
        self.assertGreater((self.script.calls - before)["answer-without"], 0)

    def test_a_leaking_question_is_repaired(self):
        self.script.flag_question = CLAIMS[1]["question"]
        self.script.repaired_question = "Which status code family covers a missing page?"
        summary, passed = self.run_demo("--score-only")
        self.assertTrue(passed)
        self.assertEqual(self.script.calls["repair"], 1)
        self.assertEqual(summary["claims"], 2)
        self.assertEqual(summary["rejected_claims"], [])

    def test_a_question_that_still_leaks_is_dropped(self):
        self.script.flag_question = CLAIMS[1]["question"]
        self.script.repaired_question = CLAIMS[1]["question"]
        summary, _ = self.run_demo("--score-only")
        self.assertEqual(summary["claims"], 1)
        self.assertEqual(len(summary["rejected_claims"]), 1)


if __name__ == "__main__":
    unittest.main()
