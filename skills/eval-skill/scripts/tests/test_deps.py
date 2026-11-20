import tempfile
import unittest
from pathlib import Path

from novelty import skillfiles
from novelty.deps import dependencies
from novelty.isolation import Markers, verdict
from novelty.prompts import arm_prompt


def write(root, path, text):
    target = root / "skills" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def skill(name, body, description="Does a thing. Use when testing."):
    return f'---\nname: {name}\ndescription: "{description}"\n---\n\n{body}\n'


class Dependencies(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        write(self.root, "setup/SKILL.md", skill("setup", "Setup body."))
        write(self.root, "setup/ROLES.md", "Roles: pick the explorer seat.\n")
        write(self.root, "setup/OTHER.md", "Unrelated setup notes.\n")
        write(self.root, "asker/SKILL.md", skill("asker", "Ask in rounds. Read [roles](../setup/ROLES.md#pick)."))
        write(self.root, "glossary/SKILL.md", skill("glossary", "Write terms to GLOSSARY.md."))
        write(self.root, "combo/SKILL.md", skill(
            "combo", 'Call the Skill tool twice, for "asker" and "glossary".\n\nMention `setup` without loading it.'))

    def test_a_link_loads_only_the_linked_file(self):
        deps = dependencies(self.root / "skills", "asker")
        self.assertEqual(deps.sources, ["skills/setup/ROLES.md"])
        self.assertIn("Roles: pick the explorer seat.", deps.text)
        self.assertNotIn("Unrelated setup notes.", deps.text)
        self.assertNotIn("Setup body.", deps.text)

    def test_a_skill_tool_call_loads_the_whole_skill_and_its_links(self):
        deps = dependencies(self.root / "skills", "combo")
        self.assertEqual(deps.sources, ["skills/asker", "skills/glossary", "skills/setup/ROLES.md"])
        self.assertIn("Ask in rounds.", deps.text)
        self.assertIn("Write terms to GLOSSARY.md.", deps.text)
        self.assertIn("Does a thing. Use when testing.", deps.text)
        self.assertIn("Roles: pick the explorer seat.", deps.text)

    def test_a_name_outside_a_skill_tool_line_is_not_a_dependency(self):
        self.assertNotIn("Setup body.", dependencies(self.root / "skills", "combo").text)

    def test_only_the_sentence_that_calls_the_skill_tool_counts(self):
        write(self.root, "builder/SKILL.md", skill(
            "builder", "Call the Skill tool with `glossary` first. Inside the `asker` skill, follow its lead."))
        self.assertEqual(dependencies(self.root / "skills", "builder").sources, ["skills/glossary"])

    def test_skills_a_dependency_loads_are_left_out(self):
        write(self.root, "outer/SKILL.md", skill("outer", 'Call the Skill tool with "combo".'))
        sources = dependencies(self.root / "skills", "outer").sources
        self.assertEqual(sources, ["skills/combo"])

    def test_a_skill_without_dependencies_gets_no_text(self):
        deps = dependencies(self.root / "skills", "glossary")
        self.assertEqual((deps.text, deps.sources), ("", []))

    def test_the_bundle_carries_the_description(self):
        self.assertIn("Does a thing. Use when testing.", skillfiles.bundle(self.root / "skills" / "glossary"))


class Prompts(unittest.TestCase):
    def test_both_arms_get_the_dependencies_and_only_one_gets_the_skill(self):
        without = arm_prompt("Plan it.", None, "DEPENDENCY TEXT")
        with_skill = arm_prompt("Plan it.", "SKILL TEXT", "DEPENDENCY TEXT")
        self.assertIn("DEPENDENCY TEXT", without)
        self.assertNotIn("SKILL TEXT", without)
        self.assertIn("DEPENDENCY TEXT", with_skill)
        self.assertIn("SKILL TEXT", with_skill)

    def test_prompts_without_dependencies_are_unchanged(self):
        self.assertEqual(arm_prompt("Plan it.", None, ""), arm_prompt("Plan it.", None))
        self.assertEqual(arm_prompt("Plan it.", "SKILL", ""), arm_prompt("Plan it.", "SKILL"))


class Isolation(unittest.TestCase):
    def test_a_skill_reference_the_dependencies_contain_is_not_a_leak(self):
        with tempfile.TemporaryDirectory() as folder:
            markers = Markers(Path(folder) / "markers.json")
            row = {"id": "0", "cells": {"a": {"without": {"answers": ["Then run /combo as the setup says."]}}}}
            leaked = verdict("combo", markers, [row], [], "Run /combo after setup.")
            clean = verdict("combo", markers, [row], [], "")
        self.assertTrue(leaked["passed"])
        self.assertFalse(clean["passed"])
