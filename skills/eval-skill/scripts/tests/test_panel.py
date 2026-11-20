import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run
from novelty import seats
from novelty.seats import Panel


class PanelLayers(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        patcher = mock.patch.object(seats, "USER_PANEL", self.root / "missing.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.folder.cleanup)

    def resolve(self, *flags):
        return Panel.resolve(run.parse_args(["panel", "--root", str(self.root), *flags]))

    def test_built_in_default(self):
        panel = self.resolve()
        self.assertEqual(panel.judges["gpt"].key, "claude:sonnet:low")
        self.assertEqual(panel.sources["answerers"], "built-in default")

    def test_project_file_then_flags_win(self):
        project = self.root / ".skills" / "eval-skill.json"
        project.parent.mkdir()
        project.write_text(json.dumps({"drafter": "codex:gpt-6.2-sol:high", "limits": {"grok": {"parallel": 2}}}))
        panel = self.resolve("--implementer", "grok:grok-4.7:high")
        self.assertEqual(panel.drafter.key, "codex:gpt-6.2-sol:high")
        self.assertEqual(panel.sources["drafter"], str(project))
        self.assertEqual(panel.implementer.key, "grok:grok-4.7:high")
        self.assertEqual(panel.sources["implementer"], "command line")
        self.assertEqual(panel.parallel("grok"), 2)
        self.assertEqual(panel.parallel("claude"), 8)

    def test_refuses_a_judge_from_the_answerers_family(self):
        with self.assertRaises(SystemExit):
            self.resolve("--judge", "claude=claude:opus:high")

    def test_a_drafter_needs_a_judge_for_its_family_to_review_claims(self):
        with self.assertRaises(SystemExit):
            self.resolve("--answerer", "opencode:anthropic/claude-sonnet-5-5:default",
                         "--drafter", "opencode:google/gemini-3-pro:default")
        panel = self.resolve("--answerer", "claude:sonnet:low", "--drafter", "codex:gpt-6.2-sol:low")
        self.assertEqual(panel.judges_for(panel.drafter)[0].key, "claude:sonnet:low")

    def test_one_model_for_every_role_is_allowed_and_noted(self):
        panel = self.resolve("--model", "grok:grok-4.7:low")
        self.assertTrue(panel.single)
        self.assertIn("Single-model panel", panel.note)
        self.assertEqual(panel.judges_for(panel.answerers[0]), panel.answerers)

    def test_opencode_seat_is_judged_by_model_family(self):
        panel = self.resolve("--answerer", "opencode:anthropic/claude-sonnet-5-5:default",
                             "--answerer", "codex:gpt-6.2-sol:low")
        self.assertEqual(set(panel.judges), {"claude", "gpt"})
        self.assertEqual(panel.clis, ["claude", "codex", "opencode"])
        self.assertEqual(panel.judges["claude"].key, "codex:gpt-6.2-sol:low")

    def test_saved_file_round_trips(self):
        panel = self.resolve("--drafter", "codex:gpt-6.2-sol:medium")
        saved = self.root / "saved.json"
        saved.write_text(json.dumps(panel.as_file()))
        again = self.resolve("--panel", str(saved))
        self.assertEqual(again.as_file(), panel.as_file())


if __name__ == "__main__":
    unittest.main()
