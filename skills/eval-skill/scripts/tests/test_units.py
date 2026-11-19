import tempfile
import unittest
from pathlib import Path

from novelty import skillfiles
from novelty.claims import leak_grams, validate_claims
from novelty.isolation import name_hits
from novelty.scoring import bucket, combine, decide, majority, tally
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

    def test_hyphenated_names_count_as_bare_words(self):
        self.assertEqual(name_hits("then eval-skill runs", "eval-skill"), ["eval-skill"])


class Buckets(unittest.TestCase):
    def test_bucket_table(self):
        self.assertEqual([bucket(True, True), bucket(True, False), bucket(False, True), bucket(False, False)],
                         ["already_known", "hurts", "teaches", "fails_both"])

    def test_process_claims_are_never_cut(self):
        self.assertEqual(decide("fact", "already_known", "already_known"), "cut")
        self.assertEqual(decide("process", "already_known", "already_known"), "keep")

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


class Families(unittest.TestCase):
    def test_family_comes_from_the_model(self):
        self.assertEqual(Seat.parse("codex:gpt-6.2-sol:low").family, "gpt")
        self.assertEqual(model_family("opencode", "anthropic/claude-sonnet-5-5"), "claude")
        self.assertEqual(model_family("opencode", "opencode/deepseek-v4.1-flash-free"), "deepseek")

    def test_rejects_a_malformed_seat(self):
        with self.assertRaises(SystemExit):
            Seat.parse("claude:sonnet")


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
