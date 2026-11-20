import tempfile
import unittest
from pathlib import Path
from unittest import mock

from novelty import skillfiles
from novelty.clis.claude import Claude
from novelty.claims import leak_grams, validate_claims
from novelty.isolation import name_hits
from novelty.report import skill_section
from novelty.rewrite import accept_edit, kept_spans
from novelty.scoring import Scorer, bucket, combine, decide, majority, tally
from novelty.seats import Seat, model_family

SKILL = "Before you rename a column, write down the callers.\n\nA 404 status code means the resource was not found.\n"


def claim(**fields):
    base = {"id": "0", "kind": "process", "source": "skills/demo/SKILL.md",
            "question": "The orders table column cust_id should be called customer_id. Change the schema.",
            "expected": "The agent writes down the callers first.",
            "span": "Before you rename a column, write down the callers."}
    return {**base, **fields}


class ClaimValidation(unittest.TestCase):
    def test_accepts_a_usable_claim(self):
        self.assertEqual(validate_claims([claim()], SKILL, 30, "demo"), [])

    def test_rejects_a_question_that_repeats_the_instruction(self):
        errors = validate_claims([claim(question="Before you rename a column, write down the callers please.")], SKILL, 30, "demo")
        self.assertTrue(any("leaks" in error for error in errors))

    def test_rejects_a_question_that_names_the_skill(self):
        errors = validate_claims([claim(question="Use the demo skill to rename cust_id.")], SKILL, 30, "demo")
        self.assertTrue(any("names the skill" in error for error in errors))

    def test_rejects_a_span_missing_from_the_text(self):
        errors = validate_claims([claim(span="Never drop a table.")], SKILL, 30, "demo")
        self.assertTrue(any("not in the skill text" in error for error in errors))

    def test_rejects_semicolons_and_too_many_claims(self):
        errors = validate_claims([claim(expected="One; two"), claim(id="1")], SKILL, 1, "demo")
        self.assertTrue(any("semicolon" in error for error in errors))
        self.assertTrue(any("more than 1" in error for error in errors))

    def test_fact_questions_may_name_their_subject(self):
        span = "a 404 status code means the requested resource was not found"
        self.assertEqual(leak_grams("What does a 404 status code mean for a request?", span, "fact"), [])
        self.assertTrue(leak_grams("Remember the 404 status code means the requested resource was not found?", span, "fact"))


class NameCheck(unittest.TestCase):
    def test_single_word_names_count_only_as_references(self):
        self.assertEqual(name_hits("I will research the topic and save research notes", "research"), [])
        self.assertEqual(len(name_hits("Use the research skill from skills/research or /research", "research")), 3)

    def test_hyphenated_names_count_as_bare_words_only_in_questions(self):
        self.assertEqual(name_hits("then eval-skill runs", "eval-skill", bare=True), ["eval-skill"])
        self.assertEqual(name_hits("Run a code-review pass before merging.", "code-review"), [])
        self.assertEqual(name_hits("Load skills/code-review first.", "code-review"), ["skills/code-review"])


class Buckets(unittest.TestCase):
    def test_bucket_table(self):
        self.assertEqual([bucket(True, True), bucket(True, False), bucket(False, True), bucket(False, False)],
                         ["already_known", "hurts", "teaches", "fails_both"])

    def test_process_claims_are_never_cut(self):
        self.assertEqual(decide("fact", "already_known", "already_known"), "cut")
        self.assertEqual(decide("process", "already_known", "already_known"), "keep")

    def test_a_claim_missing_an_answerer_is_never_cut(self):
        self.assertEqual(decide("fact", "already_known", "already_known", partial=True), "keep")
        self.assertEqual(decide("fact", "hurts", "hurts", partial=True), "fix")

    def test_overall_bucket_takes_the_most_severe_answerer(self):
        self.assertEqual(combine(["already_known", "teaches", "hurts"]), "hurts")
        self.assertEqual(combine(["already_known", "fails_both"]), "fails_both")
        self.assertEqual(combine(["already_known", "already_known"]), "already_known")

    def test_majority_decides_and_flags_disagreement(self):
        results = [{"lenient": verdict, "strict": "pass", "lenient_reason": verdict, "strict_reason": "s",
                    "answer": "a", "judge": "j", "cached": False} for verdict in ("pass", "fail", "pass")]
        self.assertIsNone(majority(results[:2], "lenient", 2))
        summary = tally("without", results, 2)
        self.assertEqual((summary["lenient"], summary["lenient_votes"], summary["unstable"]), ("pass", "PFP", ["lenient"]))


class Recheck(unittest.TestCase):
    def scorer(self, verdicts):
        scorer = Scorer.__new__(Scorer)
        scorer.panel = type("Panel", (), {"answerers": [Seat.parse("claude:sonnet:low")]})()
        scorer.vote = lambda *args: verdicts
        return scorer

    def row(self, lenient, strict):
        return {"id": "1", "cells": {"claude:sonnet:low": {"bucket_lenient": lenient, "bucket_strict": strict}}}

    def test_an_already_known_claim_that_now_fails_is_lost(self):
        result = self.scorer({"lenient": "fail", "strict": "pass"}).recheck(self.row("already_known", "teaches"), "", "v")
        self.assertEqual(result["status"], "lost")

    def test_a_hurt_claim_reports_whether_the_fix_worked(self):
        fixed = self.scorer({"lenient": "pass", "strict": "pass"}).recheck(self.row("hurts", "already_known"), "", "v")
        self.assertEqual((fixed["status"], fixed["fixes"]), ("held", {"claude:sonnet:low": "fixed"}))
        still = self.scorer({"lenient": "fail", "strict": "pass"}).recheck(self.row("hurts", "already_known"), "", "v")
        self.assertEqual((still["status"], still["fixes"]), ("held", {"claude:sonnet:low": "still hurts"}))


class ApiKeys(unittest.TestCase):
    def test_the_claude_token_refresh_gets_no_api_key(self):
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}), \
                mock.patch("subprocess.run") as run_process:
            Claude(60).refresh()
        env = run_process.call_args.kwargs["env"]
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertTrue(env["CLAUDE_CONFIG_DIR"])


class Families(unittest.TestCase):
    def test_family_comes_from_the_model(self):
        self.assertEqual(Seat.parse("codex:gpt-6.2-sol:low").family, "gpt")
        self.assertEqual(model_family("opencode", "anthropic/claude-sonnet-5-5"), "claude")
        self.assertEqual(model_family("opencode", "opencode/deepseek-v4.1-flash-free"), "deepseek")

    def test_rejects_a_malformed_seat(self):
        with self.assertRaises(SystemExit):
            Seat.parse("claude:sonnet")


class Rewrites(unittest.TestCase):
    def test_a_kept_span_across_paragraphs_is_kept_piece_by_piece(self):
        rows = [{"decision": "keep", "span": "First paragraph ends here. Second paragraph starts here."}]
        self.assertEqual(kept_spans(rows, "Intro. First paragraph ends here."), ["First paragraph ends here."])
        self.assertEqual(kept_spans(rows, "Second paragraph starts here. More."), ["Second paragraph starts here."])
        accept_edit(kept_spans(rows, "Intro. First paragraph ends here."))("First paragraph ends here.")


class Report(unittest.TestCase):
    def test_a_proposal_without_a_rewrite_omits_the_size(self):
        summary = {"skill": "demo", "claims": 0, "reused_claims": 0, "dropped_claims": 0, "rejected_claims": [],
                   "unreviewed_claims": [], "missing_cells": [], "unstable": {}, "unscored": [], "rows": [],
                   "buckets": {scale: dict.fromkeys(("already_known", "hurts", "teaches", "fails_both"), 0)
                               for scale in ("lenient", "strict")}, "buckets_by_answerer": {}, "steps": {},
                   "isolation": {"passed": True, "marker": "m", "without_answers_checked": 0, "markers_checked": 1,
                                 "canary": {}, "problems": []},
                   "proposal": {"status": "none", "reason": "the run has unscored claims"}}
        text = "\n".join(skill_section(summary, []))
        self.assertIn("Proposal: none. The run has unscored claims.", text)
        self.assertNotIn("None to None", text)


class ParagraphEdits(unittest.TestCase):
    def test_drops_a_paragraph_and_keeps_the_trailing_newline(self):
        with tempfile.TemporaryDirectory() as folder:
            skill = Path(folder) / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\n---\n\nKeep this.\n\nDrop this.\n\nEdit this.\n", encoding="utf-8")
            keys = {paragraph: key for key, (_, paragraph) in skillfiles.paragraphs(skill).items()}
            skillfiles.apply_paragraph_edits(skill, {keys["Drop this."]: "", keys["Edit this.\n"]: "Edited."})
            self.assertEqual((skill / "SKILL.md").read_text(encoding="utf-8"), "---\nname: demo\n---\n\nKeep this.\n\nEdited.\n")


if __name__ == "__main__":
    unittest.main()
