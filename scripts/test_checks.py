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
no_comments = load("no-comments.py")


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


class Comments(unittest.TestCase):
    def found(self, name, text):
        return [text[begin:end] for begin, end in no_comments.comments(Path(name), text)]

    def test_script_comments_are_found(self):
        text = "const a = 1; // one\n/* two */\nconst b = 2;\n"
        self.assertEqual(self.found("a.ts", text), ["// one", "/* two */"])

    def test_script_text_that_only_looks_like_a_comment_is_skipped(self):
        for text in [
            'const url = "https://example.com"; const b = \'a // b\';\n',
            "const t = `see // here ${a + `in // ner`} /* there */`;\n",
            r"const r = /\/\//.test(s); const q = /[/]/g; const half = a / 2 / b;",
            r"return /^\s*\/\//.test(line);",
        ]:
            self.assertEqual(self.found("a.mjs", text), [], text)

    def test_comment_inside_a_template_expression_is_found(self):
        self.assertEqual(self.found("a.js", "const t = `${a /* x */}`;\n"), ["/* x */"])

    def test_python_comments_and_docstrings_are_found(self):
        text = '"""Module."""\nA = "# no"  # yes\n\n\ndef f():\n    """Doc."""\n    return "text"\n'
        self.assertEqual(self.found("a.py", text), ['"""Module."""', "# yes", '"""Doc."""'])

    def test_shebang_and_plain_strings_are_skipped(self):
        self.assertEqual(self.found("a.py", '#!/usr/bin/env python3\nA = """not a docstring"""\n'), [])

    def test_config_comments_are_found(self):
        text = 'color: "#fff"\nurl: a#b\nname: x # why\n# whole line\n'
        self.assertEqual(self.found("a.yml", text), ["# why", "# whole line"])
        self.assertEqual(self.found(".gitignore", "# built\ndist/\n"), ["# built"])

    def test_other_files_are_skipped(self):
        self.assertEqual(self.found("a.md", "# Title\n<!-- note -->\n"), [])


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

    def test_guide_must_name_every_script_and_folder(self):
        self.write("scripts/check.py", "")
        self.write("scripts/link.py", "")
        self.write("scripts/test_check.py", "")
        self.write("docs/a.md", "")
        self.write(".github/workflows/ci.yml", "")
        self.write("AGENTS.md", "Run scripts/check.py. See docs/ and scripts/.")
        problems = list(wiring.guide_problems(self.root))
        self.assertEqual(len(problems), 1)
        self.assertIn("scripts/link.py", problems[0])

    def test_repo_without_a_guide_passes(self):
        self.write("scripts/check.py", "")
        self.assertEqual(list(wiring.guide_problems(self.root)), [])

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

    def test_skill_is_user_invoked_unless_listed(self):
        skill = self.skill("alpha")
        self.assertEqual(list(wiring.invocation_problems(skill, {"alpha"}, {})), [])
        self.assertEqual(list(wiring.invocation_problems(skill, set(), {"alpha": "why"})), [])
        problems = list(wiring.invocation_problems(skill, set(), {}))
        self.assertEqual(len(problems), 1)
        self.assertIn("MODEL_INVOKED", problems[0][2])

    def test_listed_skill_must_drop_the_flag(self):
        skill = self.skill("alpha")
        problems = list(wiring.invocation_problems(skill, {"alpha"}, {"alpha": "why"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("Remove the line", problems[0][2])

    def test_listed_skill_must_exist(self):
        skills = {"alpha": self.skill("alpha")}
        self.assertEqual(wiring.stale_model_invoked(skills, {"alpha": "why", "gone": "why"}), ["gone"])

    def test_every_listed_skill_gives_a_reason(self):
        for name, reason in wiring.MODEL_INVOKED.items():
            self.assertTrue(reason.strip(), name)

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
