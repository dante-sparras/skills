# AGENTS.md

## Scripts

Run each from the repo root, with `python3` where `python` is not Python 3.

| Script | What it does |
| --- | --- |
| [`scripts/check.py`](scripts/check.py) | Runs every check and test below. CI runs it too, so run it before you push |
| [`scripts/check-skills.py`](scripts/check-skills.py) | Checks the skills' layout, names, shape, invocation flags, links, and skill calls, and that this file names every script and folder |
| [`scripts/no-comments.py`](scripts/no-comments.py) | Fails on a comment or docstring in code or config |
| [`scripts/no-em-dashes.py`](scripts/no-em-dashes.py) | Fails on an em dash in Markdown under `skills/` |
| [`scripts/no-semicolons.py`](scripts/no-semicolons.py) | Fails on a semicolon in the prose of Markdown under `skills/` |
| [`scripts/use-when-descriptions.py`](scripts/use-when-descriptions.py) | Checks that each skill's description has a "Use when" sentence and stays within 350 characters |
| `scripts/test_*.py` | The tests, which `python -m unittest discover -s scripts -p "test_*.py"` runs |
| [`scripts/factory_harness.mjs`](scripts/factory_harness.mjs) | Loads `factory.ts` for `test_factory.py`. Needs Node 18 or newer |
| [`scripts/link-skills.py`](scripts/link-skills.py) | Links every skill into `~/.claude/skills` and `~/.agents/skills` |

## Project structure

| Path | Holds |
| --- | --- |
| [`skills/`](skills) | One folder per skill, `skills/<name>/`, the layout it installs to: `SKILL.md`, its reference files beside it, and `agents/openai.yaml` with its display name |
| [`skills/factory/factory.ts`](skills/factory/factory.ts) | The factory: the T3 Code workflow that ships issues |
| [`docs/`](docs) | Docs for people. No skill links to them |
| [`scripts/`](scripts) | The scripts above |
| [`GLOSSARY.md`](GLOSSARY.md) | The terms the skills and docs use |
| [`README.md`](README.md) | What the repo is, for people. It links every skill |
| [`LICENSES/`](LICENSES) | The licenses of the upstream skills |
| [`.github/workflows/checks.yml`](.github/workflows/checks.yml) | CI |
