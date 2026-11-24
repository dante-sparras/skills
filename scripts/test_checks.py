import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load(filename):
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_").removesuffix(".py"), SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


semicolons = load("no-semicolons.py")
wiring = load("check-skills.py")
use_when = load("use-when-descriptions.py")


class Semicolons(unittest.TestCase):
    def test_prose_semicolon_is_found(self):
        self.assertEqual(list(semicolons.prose_semicolons("one; two\n")), [(1, 4, None)])

    def test_semicolon_in_code_is_skipped(self):
        text = "a `x; y` b\n\n```ts\nlet a = 1;\n```\n"
        self.assertEqual(list(semicolons.prose_semicolons(text)), [])

    def test_inner_fence_does_not_close_a_longer_outer_fence(self):
        text = "````markdown\n```ts\nlet a = 1;\n```\nstill code; here\n````\nprose\n"
        self.assertEqual(list(semicolons.prose_semicolons(text)), [])

    def test_fence_open_at_end_of_file_is_reported(self):
        text = "```markdown\n```ts\ncode\n```\nprose\n```\nhidden; prose\n"
        problems = list(semicolons.prose_semicolons(text))
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][0], 6)
        self.assertIs(problems[0][2], semicolons.UNCLOSED)


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_slug_matches_github_headings(self):
        self.assertEqual(wiring.slug("Resolve a role"), "resolve-a-role")
        self.assertEqual(wiring.slug("Test first, or prove another way"), "test-first-or-prove-another-way")
        self.assertEqual(wiring.slug("Bugs no task owns"), "bugs-no-task-owns")

    def test_good_link_and_anchor_pass(self):
        self.write("b.md", "# Title\n\n## Resolve a role\n")
        a = self.write("a.md", "See [roles](b.md#resolve-a-role) and [here](#top).\n\n# Top\n")
        self.assertEqual(list(wiring.link_problems(a)), [])

    def test_missing_file_and_missing_anchor_fail(self):
        self.write("b.md", "# Title\n")
        a = self.write("a.md", "[x](gone.md)\n[y](b.md#nope)\n")
        self.assertEqual([line for line, _ in wiring.link_problems(a)], [1, 2])

    def test_links_inside_code_are_skipped(self):
        a = self.write("a.md", "`[x](gone.md)`\n\n```md\n[y](gone.md)\n```\n")
        self.assertEqual(list(wiring.link_problems(a)), [])

    def skill(self, name):
        self.write(f"skills/{name}/SKILL.md", f'---\nname: {name}\ndescription: "X. Use when y."\n---\n')
        return self.root / "skills" / name

    def manifest(self, plugins):
        import json

        self.write(".claude-plugin/marketplace.json", json.dumps({"plugins": plugins}))

    def test_link_to_another_skill_resolves(self):
        roles = self.skill("setup-skills")
        self.write("skills/setup-skills/ROLES.md", "## Resolve a role\n")
        build = self.skill("implement")
        page = self.write("skills/implement/notes.md", "[r](../setup-skills/ROLES.md#resolve-a-role)\n")
        skills = {"setup-skills": roles, "implement": build}
        self.assertEqual(list(wiring.link_problems(page, skills)), [])

    def test_link_to_a_missing_skill_fails(self):
        build = self.skill("implement")
        page = self.write("skills/implement/notes.md", "[r](../gone/ROLES.md)\n")
        self.assertEqual([line for line, _ in wiring.link_problems(page, {"implement": build})], [1])

    def test_skills_sit_directly_under_skills(self):
        self.skill("coordinate")
        self.skill("alpha")
        self.assertEqual(list(wiring.layout_problems(self.root / "skills")), [])
        names = [p.name for p in wiring.find_skill_dirs(self.root / "skills")]
        self.assertEqual(names, ["alpha", "coordinate"])

    def test_skill_in_a_subfolder_fails(self):
        self.write("skills/plan/alpha/SKILL.md", '---\nname: alpha\ndescription: "X. Use when y."\n---\n')
        problems = list(wiring.layout_problems(self.root / "skills"))
        self.assertEqual(len(problems), 1)
        self.assertIn("skills/<name>/SKILL.md", problems[0][1])

    def test_manifest_matching_the_folders_passes(self):
        entry = self.skill("coordinate")
        alpha = self.skill("alpha")
        self.manifest([{"name": "all", "skills": ["./skills/alpha", "./skills/coordinate"]}])
        self.assertEqual(list(wiring.manifest_problems(self.root, [entry, alpha])), [])

    def test_manifest_must_list_every_skill(self):
        alpha = self.skill("alpha")
        beta = self.skill("beta")
        self.manifest([{"name": "plan", "skills": ["./skills/alpha"]}])
        problems = list(wiring.manifest_problems(self.root, [alpha, beta]))
        self.assertEqual(len(problems), 1)
        self.assertIn("./skills/beta", problems[0])

    def test_manifest_lists_a_skill_once(self):
        alpha = self.skill("alpha")
        self.manifest([{"name": "plan", "skills": ["./skills/alpha"]}, {"name": "build", "skills": ["./skills/alpha"]}])
        self.assertEqual(len(list(wiring.manifest_problems(self.root, [alpha]))), 1)

    def test_manifest_entry_must_exist(self):
        alpha = self.skill("alpha")
        self.manifest([{"name": "plan", "skills": ["./skills/alpha", "./skills/gone"]}])
        self.assertEqual(len(list(wiring.manifest_problems(self.root, [alpha]))), 1)

    def test_name_must_match_folder(self):
        skill = self.root / "skills" / "alpha"
        self.write("skills/alpha/SKILL.md", '---\nname: beta\ndescription: "X. Use when y."\n---\n')
        self.write("skills/alpha/agents/openai.yaml", "interface:\n  display_name: A\n")
        problems = list(wiring.skill_problems(skill, set()))
        self.assertEqual(len(problems), 1)
        self.assertIn("folder", problems[0][2])

    def test_invocation_flags_must_agree(self):
        skill = self.root / "skills" / "alpha"
        self.write("skills/alpha/SKILL.md", '---\nname: alpha\ndescription: "X. Use when y."\ndisable-model-invocation: true\n---\n')
        self.write("skills/alpha/agents/openai.yaml", "interface:\n  display_name: A\n")
        self.assertEqual(len(list(wiring.skill_problems(skill, {"alpha"}))), 1)
        self.write("skills/alpha/agents/openai.yaml", "policy:\n  allow_implicit_invocation: false\n")
        self.assertEqual(list(wiring.skill_problems(skill, {"alpha"})), [])

    def shaped(self, body, display="Alpha"):
        self.write("skills/alpha/SKILL.md", f'---\nname: alpha\ndescription: "X. Use when y."\n---\n\n{body}')
        self.write("skills/alpha/agents/openai.yaml", f'interface:\n  display_name: "{display}"\n')
        return self.root / "skills" / "alpha"

    def test_skill_in_the_shared_shape_passes(self):
        skill = self.shaped("# Alpha\n\n## Steps\n\n## Report\n")
        self.write("skills/alpha/model-roles.md", "# Roles\n")
        self.write("skills/alpha/example/README.md", "# An example folder\n")
        self.assertEqual(list(wiring.shape_problems(skill)), [])

    def test_body_must_open_with_the_display_name(self):
        for body in ("Does things.\n", "# Something else\n", ""):
            problems = list(wiring.shape_problems(self.shaped(body)))
            self.assertEqual(len(problems), 1, body)
            self.assertIn("'# Alpha'", problems[0][2])

    def test_closing_section_is_named_report(self):
        for heading in ("## Reply", "## 5. Report", "### Report"):
            problems = list(wiring.shape_problems(self.shaped(f"# Alpha\n\n{heading}\n")))
            self.assertEqual([line for _, line, _ in problems], [8], heading)
        fenced = self.shaped("# Alpha\n\n```md\n## Reply\n```\n")
        self.assertEqual(list(wiring.shape_problems(fenced)), [])

    def test_reference_files_are_kebab_case_beside_the_skill(self):
        skill = self.shaped("# Alpha\n")
        self.write("skills/alpha/MODEL-ROLES.md", "# Roles\n")
        self.write("skills/alpha/references/notes.md", "# Notes\n")
        names = [path.name for path, _, _ in wiring.shape_problems(skill)]
        self.assertEqual(names, ["MODEL-ROLES.md", "references"])

    def test_skill_tool_cannot_call_a_user_invoked_skill(self):
        a = self.write("a.md", "Call the Skill tool with `tdd`.\nCall the Skill tool with `implement`.\n")
        problems = list(wiring.skill_call_problems(a, {"tdd", "implement"}, {"implement"}))
        self.assertEqual([line for line, _ in problems], [2])

    def test_skill_tool_call_must_name_a_real_skill(self):
        a = self.write("a.md", 'Call the Skill tool twice, for "grilling" and "gone".\n')
        problems = list(wiring.skill_call_problems(a, {"grilling"}, set()))
        self.assertEqual(len(problems), 1)
        self.assertIn("gone", problems[0][1])

    def test_other_names_on_a_skill_tool_line_are_ignored(self):
        a = self.write("a.md", "Call the Skill tool with `tdd`. Inside the `implement` skill, ask the coordinator.\n")
        self.assertEqual(list(wiring.skill_call_problems(a, {"tdd", "implement"}, {"implement"})), [])


class UseWhen(unittest.TestCase):
    def test_description_needs_a_use_when_sentence(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            bad = Path(tmp) / "bad.md"
            good.write_text('---\nname: a\ndescription: "Does x. Use when y."\n---\n', encoding="utf-8")
            bad.write_text('---\nname: a\ndescription: "Does x."\n---\n', encoding="utf-8")
            self.assertEqual(list(use_when.problems(good)), [])
            self.assertEqual(len(list(use_when.problems(bad))), 1)

    def test_description_stays_within_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.md"
            fits = "Does x. Use when y." + "z" * (use_when.LIMIT - 19)
            path.write_text(f'---\nname: a\ndescription: "{fits}"\n---\n', encoding="utf-8")
            self.assertEqual(list(use_when.problems(path)), [])
            path.write_text(f'---\nname: a\ndescription: "{fits}z"\n---\n', encoding="utf-8")
            problems = list(use_when.problems(path))
            self.assertEqual(len(problems), 1)
            self.assertIn(str(use_when.LIMIT), problems[0][1])


if __name__ == "__main__":
    unittest.main()
