import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "link-skills.py"
spec = importlib.util.spec_from_file_location("link_skills", SCRIPT)
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)


class LinkSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.skills = root / "repo" / "skills"
        self.target = root / "agent" / "skills"
        self.target.mkdir(parents=True)
        for name in ("spec", "ticket"):
            self.skill(name)

    def skill(self, name):
        folder = self.skills / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
        return folder

    def test_links_every_skill(self):
        done = links.sync(self.skills, self.target)
        self.assertEqual(done, [("linked", "spec"), ("linked", "ticket")])
        self.assertTrue((self.target / "spec" / "SKILL.md").is_file())
        self.assertEqual(links.sync(self.skills, self.target), [])

    def test_removes_a_link_to_a_skill_that_is_gone(self):
        gone = self.skill("plan")
        links.sync(self.skills, self.target)
        (gone / "SKILL.md").unlink()
        gone.rmdir()
        self.assertEqual(links.sync(self.skills, self.target), [("removed", "plan")])
        self.assertIsNone(links.link_target(self.target / "plan"))
        self.assertTrue((self.target / "spec" / "SKILL.md").is_file())

    def test_leaves_what_it_did_not_link(self):
        other = Path(self.tmp.name).resolve() / "elsewhere" / "find-skills"
        other.mkdir(parents=True)
        links.make_link(self.target / "find-skills", other)
        (self.target / "spec").mkdir()
        (self.target / "spec" / "notes.md").write_text("mine", encoding="utf-8")
        done = links.sync(self.skills, self.target)
        self.assertEqual(done, [("skipped", "spec"), ("linked", "ticket")])
        self.assertIsNotNone(links.link_target(self.target / "find-skills"))
        self.assertTrue((self.target / "spec" / "notes.md").is_file())

    def test_a_dry_run_changes_nothing(self):
        done = links.sync(self.skills, self.target, dry_run=True)
        self.assertEqual(done, [("linked", "spec"), ("linked", "ticket")])
        self.assertEqual(list(self.target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
