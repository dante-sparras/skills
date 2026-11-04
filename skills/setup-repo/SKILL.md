---
name: setup-repo
description: "Set up a repo with Dante's baseline: AGENTS.md, CONTRIBUTING.md, .github templates and workflows, docs, license, and GitHub settings. Run inside an existing project, or anywhere else to scaffold a new one first."
disable-model-invocation: true
---

# Setup Repo

Give any project, in any stack, a good baseline.

## What it creates

[templates/](templates/) mirrors this tree. Only the skill folders, `skills-lock.json`, `docs/agents/`, `LICENSE`, and the toolchain file are made another way.

```text
.
├── .agents/skills/                   # default skills, for Codex
├── .claude/skills/                   # the same skills, for Claude Code
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   ├── config.yml
│   │   └── feature_request.yml
│   ├── workflows/
│   │   ├── branch-name.yml
│   │   ├── ci.yml
│   │   ├── pr-title.yml
│   │   ├── release-please.yml        # optional: releases
│   │   ├── stale-needs-info.yml
│   │   └── zizmor.yml                # zizmor and actionlint audit the workflows themselves
│   ├── SECURITY.md                   # public repos only
│   ├── dependabot.yml
│   └── pull_request_template.md
├── docs/
│   ├── agents/                       # written by setup-matt-pocock-skills
│   └── development.md
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .node-version                     # or the stack's toolchain file, when none exists
├── .release-please-manifest.json     # optional: releases
├── AGENTS.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── release-please-config.json        # optional: releases
└── skills-lock.json                  # where each default skill came from
```

Files marked `optional:` are written only when that feature is chosen. `docs/development.md` also gets a Releasing section with it.

| Optional feature | Files | Chosen in |
| --- | --- | --- |
| `releases` | `.github/workflows/release-please.yml`, `release-please-config.json`, `.release-please-manifest.json`. release-please adds `CHANGELOG.md` with the first release. | Q8 |

It also applies the GitHub settings in step 6.

## How it works

| Step | What happens | Stops for the user |
| --- | --- | --- |
| 1. Start | Move to the repo root, or create a new project | New project: one message with every question |
| 2. Explore | Read the repo | Only for uncommitted changes, or the wrong branch |
| 3. Ask | Ask Q5 to Q10 | Existing projects: one message with every question |
| 4. Write | Create the GitHub repo, write the templates, install the default skills, run `setup-matt-pocock-skills` | One message for files that already exist; whatever `setup-matt-pocock-skills` asks |
| 5. Commit and push | Commit the baseline, push it or open a PR | No |
| 6. Apply GitHub settings | Apply the settings approved in Q10 | Only when a setting can't be applied as approved |
| 7. Report | Say what was done and what's left | No |

Every question follows [references/asking.md](references/asking.md); read it before the first message to the user. Don't stop anywhere else.

In this file, each question has the same shape: a heading with its number and title (Q1 to Q10), an **Ask:** line with the question worded for its usual recommendation, its choices as a list when it has them, a **Recommend:** line when there is a recommendation, and then its rules. These numbers are for this file; in a message, number the questions you send from Q1, as [references/asking.md](references/asking.md) says.

`OWNER/REPO` means the GitHub repository throughout, such as `dante-sparras/skills`. `main` means the repo's default branch; in commands, `<default>` is its real name.

## Conditions

These conditions change what the skill does. Look them up here instead of re-deriving them.

### Visibility

Known in step 2, or from Q5 for a new GitHub repo. Until then, assume public.

| | Public | Private |
| --- | --- | --- |
| Stance (Q6) | Asked: `strict` or `open` | `team`, not asked |
| License recommendation (Q7) | MIT | None (proprietary) |
| `SECURITY.md` and private vulnerability reporting | Yes | No |
| Ruleset on `main` | Yes | Only on a paid plan |

### Guarded `main`

Known in step 2: whether `main` already has branch protection or a ruleset. A user without admin rights also counts as guarded.

| | Unguarded | Guarded |
| --- | --- | --- |
| Push | Straight to `main` | To branch `chore/repository-baseline`, then a PR |
| Ruleset, workflow permissions, and SHA-pinned actions in step 6 | Applied | Deferred: the user applies them after the baseline PR merges, since `main`'s workflows don't have the baseline's pins and permissions until then |
| Other step 6 settings | Applied | Applied with admin rights. Without them, Q10 and step 6 are skipped, except Labels, which only need write access and are created without asking; the Report lists every other setting for an admin to apply. |

### Paid plan

Decides whether a private repo gets the ruleset and auto-merge. `gh api user -q .plan.name` (or `gh api orgs/<org> -q .plan.name`) usually comes back empty, because gh's default token can't see the plan. Then probe: `gh api repos/OWNER/REPO/rulesets` on a private repo returns 403 with an upgrade message on a free plan. With no GitHub repo yet, mark the plan-dependent lines "**If you're on a paid plan:**", and probe right after step 4 creates the repo.

### Ruleset

The ruleset on `main` applies when all of these hold:

- the repo is public, or private on a paid plan;
- the checks pass in step 2 (with no stack, they count as passing);
- `main` has no existing ruleset or protection that already requires a PR and passing checks;
- the user approves it in Q10. Without admin rights Q10 isn't asked: count it as approved, so it's listed for an admin and the `CONTRIBUTING.md` bullet stays.

**Precheck.** In `.github/workflows/`, each required check (`ci`, `pr-title`) must be:

- the `name:` of a job,
- in a workflow triggered by `pull_request` (or `pull_request_target`, for `pr-title`),
- with no `paths:`, `paths-ignore:`, or `branches:` filter on that trigger.

And in step 6, `ci` must have passed in step 5.

With a guarded `main`, it's deferred: the Report lists it for after the baseline PR merges. When the checks fail, leave it out of Q10. It also stops applying when CI fails in step 5 and can't be fixed, or the step 6 precheck fails. Whenever it doesn't apply for one of these reasons, list it under "Left for them" with the reason; a required `ci` that fails blocks every PR.

---

## 1. Start

If the current directory is inside a git repo, move to its root: `git rev-parse --show-toplevel`. Then:

- **It's inside a git repo** (`git rev-parse --is-inside-work-tree`) **or has a project manifest** ([references/stacks.md](references/stacks.md)): it's an existing project. Go to step 2.
- **It has neither:** create a new project, as below, then go to step 2 inside it.

### Create a new project

**1. Ask.** First check the plan, as "Paid plan" in Conditions describes. Then send one message that opens with "You ran this skill outside a project, so let's create one." and holds:

- Q1 to Q4 below. They're open questions, with no recommendation.
- Then Q5 to Q10 from step 3, where their "New project" column applies.

#### Q1. Project name

**Ask:** What should the project be called?

Use it as written for `{{PROJECT_NAME}}`. Its kebab-case form is the folder and repo name.

#### Q2. Location

**Ask:** Which folder should the project folder go in?

It's the parent folder. Check that `<parent>/<kebab-name>` doesn't exist yet.

#### Q3. Kind of project

**Ask:** What kind of project is it?

Free text, such as "Next.js app" or "Python CLI". When it covers materially different projects, ask one follow-up, such as for "React app":

**Ask:** Use Next.js? Or Vite.

#### Q4. Description

**Ask:** Describe the project in one sentence.

Use it as written for `{{DESCRIPTION}}`.

**2. Choose the scaffold command.**

- Use the stack's official scaffolder at its latest version: `create-next-app@latest`, `bun create vite`, `uv init`, `cargo new`, and so on.
- Read its `--help` or current docs, and pass every choice as a flag so it never stops at a prompt.
- Take its recommended defaults, but prefer TypeScript over JavaScript, the package manager the user names, and the stack's mainstream linter and formatter.
- With no scaffolder for the stack, write the minimal manifest by hand (`go mod init <module>`, a bare `pyproject.toml`).

**3. Run it, without asking.**

1. Run it from the parent folder, creating `<kebab-name>/`. Work inside that folder from then on.
2. Run `git init -b main`, unless the scaffolder already created a repo. Keep any initial commit it made, and rename its branch to `main` (`git branch -m main`) when it's called something else.
3. Run the install, then the build (or the tests, if there's no build). Never start a dev server or anything else that keeps running. Fix whatever the scaffold broke.
4. Commit everything still uncommitted as `chore: scaffold project`.

**Done when** the new folder builds, has a manifest, and is a git repo on `main` with a clean working tree.

---

## 2. Explore

Read the repo before asking anything. Never guess what you can check.

| Check | How | Decides |
| --- | --- | --- |
| **Git repo** | `git rev-parse --is-inside-work-tree` | If not: `git init -b main`, write `.gitignore` as step 4 describes, then commit the existing files as `chore: initial commit`. Check that no `.env` or other secret file is staged first. A repo with no remote and a branch other than `main`: rename it with `git branch -m main`. |
| **Working tree** | Is `git status` clean? | If not, stop and ask "Uncommitted changes" below, before anything else. |
| **Default branch** | `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`. With no GitHub repo, or an empty one (the name comes back empty): the current branch. | `{{DEFAULT_BRANCH}}`, and `<default>` in commands. |
| **Current branch** | `git branch --show-current`, then `git fetch` and `git status -sb` | It must be the default branch, and not behind `origin`. If not, stop and ask "Wrong branch" below. |
| **GitHub** | `git remote -v`, then `gh repo view --json nameWithOwner,visibility,viewerPermission` | Visibility, whether Q5 is asked, and admin rights (`ADMIN`). Without write access (`READ`, `TRIAGE`), stop: the baseline needs to push a branch. An `origin` that isn't on GitHub gets renamed to its host (`git remote rename origin gitlab`) before step 4 creates the GitHub repo; say so in Q5. |
| **Plan** | As "Paid plan" in Conditions describes | Whether a private repo gets the ruleset and auto-merge. |
| **Guarded `main`** | Rulesets: `gh api repos/OWNER/REPO/rules/branches/<default>` (a 403 means none); read each rule's `type`, and the check names from `required_status_checks` rules' `.parameters.required_status_checks[].context`. Classic protection: `gh api repos/OWNER/REPO/branches/<default> -q '.protection'`, which works without admin rights; `enabled` and `required_status_checks.contexts` are what count (`.protected` is also true for rulesets, so don't use it). | Guarded when a rule blocks a direct push (`pull_request`, `required_status_checks`, `update`, `required_signatures`) or classic protection is enabled; other rules, such as Copilot review, don't count. Note the required check names. Whether classic protection requires a PR: with admin rights, `gh api repos/OWNER/REPO/branches/<default>/protection -q .required_pull_request_reviews` (non-null means yes); without them, assume it doesn't. A new GitHub repo, or a `main` not on GitHub yet, is unguarded. |
| **Stack** | The manifests in [references/stacks.md](references/stacks.md), the lockfile, and the project's scripts or tasks | CI steps, Dependabot, `.gitignore`, release type, `AGENTS.md`. |
| **Releases and version** | `gh release list --limit 1`, `git describe --tags --abbrev=0 --match "v*"`, and the version in the manifest | Q8's recommendation, `{{CURRENT_VERSION}}`, and `{{BOOTSTRAP_SHA}}`. |
| **License** | `gh repo view --json licenseInfo`, or a `LICENSE` or `LICENSE.md` file | Whether Q7 is asked, and `{{LICENSE_LINE}}`. |
| **Existing files** | Which files from "What it creates" already exist | Which files need a decision in step 4. |
| **Existing workflows** | In each workflow not from the baseline: any `uses:` not pinned to a full SHA, and any job with no `permissions:` at either the job or the workflow level | Step 4 pins them and adds the permissions each job needs. Q10's settings line names them. |
| **Checks** | Run the locked install (as in CI), then the commands `{{CI_COMMANDS}}` will run ([references/stacks.md](references/stacks.md)), including Go's and Rust's always-on checks. Then `git status --porcelain`: anything the install and checks created (`node_modules/`, `.venv/`, `dist/`, `target/`, coverage) must end up ignored, except a lockfile. | Whether the ruleset applies (see Conditions). A failed install counts as failing checks. With no lockfile, run the normal install to create one, and commit it with the baseline. |
| **Manifests** | Every package manifest in the repo, at any depth: those in [references/stacks.md](references/stacks.md), plus `Dockerfile`, `Gemfile`, `composer.json`, and any other Dependabot ecosystem | The Dependabot entries; see [references/stacks.md](references/stacks.md) for workspaces. |
| **Name and description** | The README or a manifest, else the folder name. For a new project: Q1 and Q4. | `{{PROJECT_NAME}}` and `{{DESCRIPTION}}`. |

### Uncommitted changes

**Ask:** The working tree has uncommitted changes. Commit or stash them, then reply **yes** to continue.

### Wrong branch

**Ask:** You're on `<branch>`, but the baseline goes on `<default>`. Switch to `<default>` and pull, then continue? Or stop.

**Recommend:** Switch and pull, when the working tree is clean. Behind `origin` only: pull, then continue.

---

## 3. Ask

**New project:** every question was asked in step 1. Go to step 4.

**Existing project:** send one message. Open it with a short summary of what the repo has and what's missing, plus the private-repo limits from the Visibility table when the repo is private. Then ask every question that applies, in this order:

| Question | Existing project with a GitHub repo: ask when | New project, or no GitHub repo yet: ask when |
| --- | --- | --- |
| **Q5** GitHub repo | Never | Always; for a new project, the name is Q1's, so ask only visibility and owner |
| **Q6** Stance | Public | Always, marked "**If public:**" |
| **Q7** License | No license yet | No license yet; give both recommendations, marked "**If public:**" and "**If private:**" |
| **Q8** Versioned releases | Always | Always; for a new project, give both recommendations, marked by kind of project |
| **Q9** Release token | The ruleset would apply, or `main` already requires checks; marked "**If you answer yes to versioned releases:**", plus "**If you approve the ruleset:**" when it depends on Q10 | The ruleset would apply; marked "**If you answer yes to versioned releases:**" and "**If you approve the ruleset:**", plus "**If public:**" when a private repo wouldn't get the ruleset |
| **Q10** GitHub settings | You have admin rights | Always |

When a line in one message depends on another answer in that message, start it with that condition in bold: "**If public:**", "**If you answer yes to versioned releases:**", "**If you approve the ruleset:**". Apply only the lines whose condition holds once the answers are in.

### Q5. GitHub repo

**Ask:** There's no GitHub repo yet, and the baseline needs one. Create it as a public repo named `<folder-name>` under `<your login>`? Or give another name, make it private, or pick one of your orgs: `<orgs>`.

**Recommend:** `<folder-name>`, public, under your account.

- List the orgs from `gh api user/orgs -q '.[].login'`; leave that part out when there are none. When an org could be chosen, its plan isn't known yet: mark the plan-dependent lines "**If you're on a paid plan:**", and probe after step 4 creates the repo.
- Ask it first in step 3. For a new project, the name is Q1's kebab-case form.
- **Declined:** end the skill without writing anything, and say the baseline needs a GitHub repo.
- **Private:** the private column of the Visibility table applies, and any answer to Q6 is dropped.

### Q6. Contribution stance

**Ask:** Use the strict stance for outside contributions? Or choose open. Both keep the one-problem-per-PR and evidence rules in CONTRIBUTING.md.

- **Strict**: features and behavior changes need the maintainer's approval first; PRs that don't follow the guide may be closed.
- **Open**: small fixes go straight to a PR; bigger changes are discussed first.

**Recommend:** Strict.

The stance picks which `<!-- stance:… -->` blocks `CONTRIBUTING.md` keeps. Private repos get `team`, without asking.

### Q7. License

**Ask:** Use the MIT license? Or name another SPDX id (such as Apache-2.0), or none for proprietary code.

**Recommend:** MIT for a public repo. For a private repo, recommend none, and ask: Leave it unlicensed, as proprietary code? Or name an SPDX id.

### Q8. Versioned releases

**Ask:** Publish numbered releases with a changelog? release-please opens a release PR from the commit titles on `main`; merging it tags the release.

**Recommend:** Yes for something people install (a library, a CLI, a desktop or mobile app, or a repo with `v*` tags). No for a website, web app, or service deployed from `main`; then ask "Skip versioned releases? …". For a new project, Q3 isn't answered yet: give both, as "**If it's a library, CLI, or desktop or mobile app:** yes. **If it's a website, web app, or service:** no."

### Q9. Release token

**Ask:** Use a release token? A release PR opened with the built-in token doesn't trigger CI, so the ruleset blocks it.

- **Token**: you create a fine-grained token for this repo (Contents, Pull requests, and Issues read/write) and store it with `gh secret set RELEASE_PLEASE_TOKEN --repo OWNER/REPO`. It expires and needs renewing.
- **No token**: close and reopen each release PR right before merging it, to trigger its checks.

**Recommend:** Token.

Never ask for the token itself; the user stores it. Storing a secret needs admin rights (or owning a personal repo): without them, say an admin stores it, and list it in the Report's admin items.

### Q10. GitHub settings

**Ask:** Apply these to OWNER/REPO?

List one line per row of step 6's settings table whose "Applies when" holds, in its "In Q10" wording. Mark a line whose condition depends on another answer in this message, as above. With a guarded `main`, end each deferred line with "(you apply this after the baseline PR merges)".

**Recommend:** All of them.

---

## 4. Write

Fill everything from what the repo actually contains and what the user answered.

### Create the GitHub repo

Only when Q5 was asked. Create it as answered, without pushing:

```sh
gh repo create OWNER/REPO --<visibility> --source . --remote origin --description "<description>"   # leave out --description when it's a TODO
```

**Done when** `gh repo view` prints the repo from inside this directory. `{{OWNER}}` and `{{REPO}}` are known from here on. If the plan is still unknown, probe it now ("Paid plan" in Conditions), and settle the "**If you're on a paid plan:**" answers before writing the templates.

### Copy the templates

Copy every file in [templates/](templates/), except:

- `.github/SECURITY.md`, for a private repo, or when private vulnerability reporting was declined in Q10
- the `releases` files, when releases weren't chosen (see "What it creates")

| Rule | What to do |
| --- | --- |
| **Paths** | The path inside `templates/` is the repo path. A leading `dot-` on a segment becomes `.` (`dot-github/` → `.github/`), and a trailing `.tmpl` is dropped. |
| **Placeholders** | Replace every uppercase `{{NAME}}`, using the Placeholders table below. GitHub expressions like `${{ github.ref }}` stay as written. |
| **Blocks** | Keep a `<!-- stance:… -->` block when it names the repo's stance; a block can name several (`<!-- stance:strict,open -->`). Keep an `<!-- optional:… -->` block when that feature was chosen. Keep `<!-- optional:ruleset -->` when the ruleset applies (see Conditions; deferred counts), or `main`'s existing rules already require a PR and passing checks. Keep `<!-- optional:security -->` when `SECURITY.md` is written. Delete every other block, and every marker line. |

When the file already exists:

| Existing file | What to do |
| --- | --- |
| `.gitignore` | Never ask; only add. Append the template lines it lacks under a `# Baseline` heading, plus an entry for anything the step 2 install and checks created that isn't ignored yet, except a lockfile. |
| `CLAUDE.md` with more than `@AGENTS.md` | Move its content into the matching sections of `AGENTS.md`; whatever fits none goes into a `## Conventions` section before `## Notes`. Then make `CLAUDE.md` just `@AGENTS.md`. Show both diffs in the existing-files message, as context; with no other file to ask about, show them in the Report. When `AGENTS.md` itself is kept as the user's, move the `CLAUDE.md` content in anyway, and say so. |
| Written by the scaffolder in step 1 | Replace it without asking, keeping any stack-specific instructions. |
| Anything else | Ask "Existing file" below, one question per file, all in one message. Put in that same message the `CLAUDE.md` diffs, as context, and a question about any existing job whose `permissions:` you can't work out from what it does. |

#### Existing file

**Ask:** `<file>` already exists. Merge in the baseline's additions? Or replace it with the baseline's version, or keep yours. Show the diff below the question.

**Recommend:** Merge: keep the user's content, and add what's missing.

#### After the files are settled

- Apply [references/stacks.md](references/stacks.md): the stack's `.gitignore` section (only when there was no `.gitignore`), the toolchain version file (unless the repo already pins a version), and the install cooldown. After changing a lockfile's settings (uv's `exclude-newer`), refresh the lockfile (`uv lock`).
- If `{{CI_STEPS}}` formats or lints the whole repo, add `.agents/` and `.claude/skills/` to that tool's ignore file (`.prettierignore`, `biome.json`, `.markdownlintignore`, and so on). With releases, add `CHANGELOG.md` too, since release-please writes it in its own style.
- With releases, add `CHANGELOG.md linguist-generated` to `.gitattributes`.
- Pin every unpinned `uses:` in the repo's other workflows to the full SHA of the tag it already uses (`gh api repos/<owner>/<repo>/commits/v4` for `@v4`, with only `owner/repo` even when the action has a sub-path or is a reusable workflow), with that tag as the comment; don't move it to a newer version. Local `./` actions need no pin. Give each job with no `permissions:` at either level the ones it needs.
- Leave the `## Notes` section of `AGENTS.md` exactly as written.

### Placeholders

Never invent a value. When it's unknown, use the "If unknown" column.

| Placeholder | File | Value | If unknown |
| --- | --- | --- | --- |
| `{{PROJECT_NAME}}` | several | From step 2, or Q1 | The folder name |
| `{{DESCRIPTION}}` | `AGENTS.md`, `README.md` | One sentence from the README or a manifest, or Q4 | `TODO: one-sentence description` |
| `{{DEFAULT_BRANCH}}` | workflows, `CONTRIBUTING.md`, `SECURITY.md`, `docs/development.md`, `bug_report.yml` | From step 2 | `main` |
| `{{REQUIRED_CHECKS}}` | `CONTRIBUTING.md` | "`ci` and the PR title" for the baseline's ruleset; otherwise the check names step 2 found on `main` | Delete the `optional:ruleset` block |
| `{{OWNER}}`, `{{REPO}}` | several | `gh repo view --json nameWithOwner` | Always known after "Create the GitHub repo" |
| `{{LICENSE_LINE}}` | `README.md` | `[<SPDX id>](<license file name>)`, or `Proprietary. All rights reserved.` | `TODO: license` |
| `{{STACK_LIST}}` | `AGENTS.md` | One bullet per main technology, with the version where the repo pins one | `- TODO: add the stack` |
| `{{PROJECT_TREE}}` | `AGENTS.md` | The directories that matter, as a tree with a `# comment` beside each. See below. | The files this skill created, then `# TODO: add source directories once code exists` |
| `{{COMMANDS_TABLE}}` | `docs/development.md` | A `\| Command \| What it does \|` table of every script or task, then the skills row below | The skills row, then `\| TODO \| Add commands once the stack exists \|` |
| `{{PREREQUISITES}}` | `docs/development.md` | Tools and their versions, as bullets | `- TODO: add prerequisites` |
| `{{SETUP_COMMANDS}}` | `docs/development.md` | The install commands after the clone | `# TODO: add install commands` |
| `{{ENVIRONMENT_NOTES}}` | `docs/development.md` | Copying `.env.example`, services to start, required credentials | Delete the line and the blank line after it |
| `{{CI_COMMANDS}}` | `AGENTS.md`, `docs/development.md` | The check command from [references/stacks.md](references/stacks.md), in backticks | `` `TODO: add the check command once the stack exists` `` |
| `{{CI_STEPS}}` | `ci.yml` | Setup, install, and the check command, from [references/stacks.md](references/stacks.md), each step starting `      - ` (6 spaces) | One step: `      - run: echo "No checks configured yet; add them when the stack exists."` |
| `{{STACK_ECOSYSTEMS}}` | `dependabot.yml` | Entries from [references/stacks.md](references/stacks.md), each starting `  - ` (2 spaces) | Delete the line |
| `{{AREA_OPTIONS}}` | `bug_report.yml` | One `        - <area>` line (8 spaces) per top-level app, package, or component | Delete the line |
| `{{RELEASE_TYPE}}` | `release-please-config.json` | From [references/stacks.md](references/stacks.md) | `simple` |
| `{{CURRENT_VERSION}}` | `.release-please-manifest.json` | The manifest's version, else the latest `v*` tag without its `v` | `0.0.0` |
| `{{BOOTSTRAP_SHA}}` | `release-please-config.json` | The `HEAD` SHA from before the baseline commit, when the repo has earlier commits but no GitHub release | Delete the whole `"bootstrap-sha"` line |

`{{PROJECT_TREE}}` always includes these, with these comments. Add `docs/adr/` (`# Decision records`) and `GLOSSARY.md` once they exist.

| Path | Comment |
| --- | --- |
| `CONTRIBUTING.md` | `# Branches, commit and PR titles, PR rules` |
| `docs/development.md` | `# Setup, environment, and every command` |
| `docs/agents/` | `# How the engineering skills use this repo` |
| `.agents/skills/` | `# Agent skills; a copy in .claude/skills/` |

The skills row for `{{COMMANDS_TABLE}}`, exactly:

```markdown
| `npx -y skills@1.7.4 update -p` | Update the unpinned agent skills. Pinned ones (with a `ref` in `skills-lock.json`) change only when re-added with a newer `#<sha>`. |
```

### `LICENSE`

- **None chosen (proprietary), or a license already exists:** write nothing.
- **Otherwise:** fetch the text with `gh api licenses/<spdx-id> -q .body`. For MIT and BSD-style licenses, set `[year]` to the current year and `[fullname]` to `gh api user -q .name` (or `.login` when the name is empty). Leave every other license exactly as fetched.

### Install the default skills

Install these in every repo, without asking:

| Source | Skills | Except |
| --- | --- | --- |
| `mattpocock/skills#59db609eb1e18aaf59b63284d0e52255aff0c63c` | `'*'` | `git-guardrails-claude-code` `migrate-to-shoehorn` `scaffold-exercises` `setup-pre-commit` `chief-of-staff` `claude-handoff` `loop-me` `setup-ts-deep-modules` `writing-beats` `writing-fragments` `writing-shape` |
| `dante-sparras/skills` | `'*'` | `setup-repo` |

From the repo root, run one `add` per row, then one `remove` with every skill in the Except column:

```sh
npx -y skills@1.7.4 add <source> --skill <skills> --agent claude-code codex --copy -y
npx -y skills@1.7.4 remove <every Except skill, space-separated> -y
```

Never add `-g` or drop `--copy`: the skill folders and `skills-lock.json` are committed to the repo.

Then copy `.agents/skills/work/subagents/*.md` into `.claude/agents/`, so Claude Code loads the subagents the `work` skill spawns. They're committed with the skills.

### Run `setup-matt-pocock-skills`

Read the installed `.agents/skills/setup-matt-pocock-skills/SKILL.md` and do what it says, questions included. Afterwards, move anything it wrote into `CLAUDE.md` to `AGENTS.md`, and reset `CLAUDE.md` to `@AGENTS.md`. If it chose triage label names other than the defaults in step 6's Labels table, use them in `bug_report.yml`, `feature_request.yml`, and `stale-needs-info.yml` too.

### Check the result

**Done when** every skill is installed, every template file is written, merged, or kept as the user chose, and:

- Searching the files written from templates for `\{\{[A-Z_]+\}\}|<!-- /?(stance|optional):` finds nothing. Skip the skill folders. On Windows, use the Grep tool or Git Bash's `grep -rnE`.
- Every written `.yml` parses. When `actionlint` is installed, run it on all of `.github/workflows/`: fix findings in the baseline's files, and list findings in the repo's own workflows under "Left for them". Otherwise use any YAML parser.
- The locked install from CI still succeeds, the project's formatter has run on the files you wrote (skip the skill folders), and `{{CI_COMMANDS}}` passes, unless it already failed in step 2. With no stack, there's nothing to run, and it counts as passing.
- When the ruleset applies, the written workflows pass its precheck (Conditions). Fix them if not.
- `zizmor .github` (or `uvx zizmor .github`) reports no findings in the baseline's files, when either is available. Fix each, or add a `# zizmor: ignore[<audit>]` comment saying why it's safe. List findings in the repo's own workflows under "Left for them"; don't change their logic.

---

## 5. Commit and push

1. **Guarded `main` only:** create the branch first: `git switch -c chore/repository-baseline`.
2. **Commit the baseline:**

   ```sh
   git add -A
   git commit -m "chore: set up repository baseline"
   ```

3. **Normalize line endings:**

   ```sh
   git add --renormalize .
   git status --short
   ```

   If that staged anything, commit it separately as `chore: normalize line endings`.

4. **Push:**
   - Unguarded: `git push -u origin <default>`.
   - Guarded: `git push -u origin chore/repository-baseline`, then open a PR titled `chore: set up repository baseline`, filling in the PR template.

5. **Watch CI:**
   - Unguarded: get each run for this commit with `gh run list --workflow <file> --commit "$(git rev-parse HEAD)" --json databaseId -q '.[0].databaseId'`, for `ci.yml`; for `zizmor.yml` (the Workflows workflow) only when the push changed `.github/`, as the first push does; and for every existing workflow step 4 changed that runs on this push. Report failures in those existing workflows instead of fixing their logic. A run can take a few seconds to appear: retry until it's non-empty. Then `gh run watch <id> --exit-status`.
   - Guarded: wait until `gh pr checks` lists at least one check, then `gh pr checks --watch`.

   If `ci` fails because of the baseline, fix it, commit, and push again. If it can't pass (it already failed in step 2, or a CI-only problem you can't fix), the ruleset no longer applies (see Conditions): when the `CONTRIBUTING.md` ruleset bullet was kept for it, remove that bullet in a follow-up commit, `docs: remove the ruleset note`. Never fix the project's own failing code. When the Workflows run fails only on the repo's own workflows, report it instead of fixing it. With releases, also find the `release-please.yml` run and note whether it failed; don't fix it here.

---

## 6. Apply GitHub settings

Apply each setting approved in Q10, in the order of the table and sections below. Skip deferred ones:

1. **Read** its current value. Skip it if it already matches.
2. **Apply** it.
3. **Stop and ask** only when it can't be applied as approved: an existing ruleset with different rules, a 409 from an org policy, or a failed ruleset precheck. Ask "Setting can't be applied" below.

On Windows, run these commands in Git Bash; PowerShell breaks the quoting.

| Setting | In Q10 | Applies when |
| --- | --- | --- |
| Merge settings | Squash-only merges, PR title as the commit, branches deleted after merging, an "Update branch" button, and auto-merge; wiki, Projects, and Discussions off | Always; auto-merge only for public repos and paid plans |
| Description and topics | Repo description "<description>" and topics `<topic>`, `<topic>` | Always |
| Private vulnerability reporting | Private vulnerability reporting, which SECURITY.md points to | Public |
| Labels | Labels for bugs, ideas, and triage | Always |
| Dependabot alerts and security updates | Dependabot alerts and security updates | Always |
| Secret scanning and push protection | Secret scanning with push protection: pushes containing API keys or tokens are blocked | Public (private repos need a paid Secret Protection license) |
| CodeQL default setup | CodeQL code scanning (default setup): every PR is scanned for security bugs | Public (private repos need a paid Code Security license) |
| Workflow permissions | A read-only workflow token by default | Always; deferred with a guarded `main` |
| Actions may open pull requests | GitHub Actions may open pull requests, so release-please can open the release PR | Versioned releases without a token, even with a guarded `main` |
| SHA-pinned actions | Only SHA-pinned actions allowed. Name any existing workflows that get pinned or given permissions. | Always; deferred with a guarded `main` |
| Approval for outside contributors | Outside contributors' PRs wait for your approval before their workflows run | Public |
| Immutable releases | Immutable releases: a published release's tag and files can't be changed. A later job that uploads build files needs release-please to create drafts (`"draft": true`) first. | Versioned releases |
| Ruleset on `main` | A ruleset on `main`: every change through a PR with passing checks, run on top of the latest `main` (the branch must be up to date), and CodeQL findings block the merge; no bypass | It applies (see Conditions); deferred with a guarded `main`; always last |

### Setting can't be applied

**Ask:** `<setting>` can't be applied as approved: `<what you found>`. `<your recommended fix, as a yes/no question>`? Or skip it.

For example: "The repo already has a `main` ruleset with different rules. Replace them with the baseline's rules? Or skip it."

**Recommend:** The fix.

### Merge settings

```sh
# Read. Target: squash only, title PR_TITLE, message BLANK, wiki/projects/discussions off, and the rest true.
gh api repos/OWNER/REPO -q '{squash: .allow_squash_merge, merge: .allow_merge_commit, rebase: .allow_rebase_merge, delete: .delete_branch_on_merge, auto_merge: .allow_auto_merge, update_branch: .allow_update_branch, title: .squash_merge_commit_title, message: .squash_merge_commit_message, wiki: .has_wiki, projects: .has_projects, discussions: .has_discussions}'
# Apply
gh repo edit OWNER/REPO --enable-squash-merge --squash-merge-commit-message pr-title --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge --allow-update-branch --enable-wiki=false --enable-projects=false --enable-discussions=false
# Public repos and paid plans only
gh repo edit OWNER/REPO --enable-auto-merge
```

### Description and topics

Set the description to `{{DESCRIPTION}}` only when GitHub has none and it isn't a TODO. Add 3 to 6 topics: lowercase and hyphenated, from the stack and what the project does (`typescript`, `cli`, `home-automation`). Keep any existing topics.

```sh
# Read
gh repo view OWNER/REPO --json description,repositoryTopics
# Apply
gh repo edit OWNER/REPO --add-topic <topic>,<topic>,<topic>
gh repo edit OWNER/REPO --description "<description>"   # only when it was empty
```

### Private vulnerability reporting

```sh
# Read. Target: true.
gh api repos/OWNER/REPO/private-vulnerability-reporting -q .enabled
# Apply
gh api -X PUT repos/OWNER/REPO/private-vulnerability-reporting
```

### Labels

There's nothing to read: `--force` creates or updates. Run this once per row that applies:

```sh
gh label create <name> --color <color> --description "<description>" --force --repo OWNER/REPO
```

| Name | Color | Description | When |
| --- | --- | --- | --- |
| `bug` | `d73a4a` | Something is broken or behaving incorrectly. | Always |
| `enhancement` | `a2eeef` | A feature idea or improvement. | Always |
| `needs-triage` | `fbca04` | Maintainer needs to evaluate this issue. | Always |
| `needs-info` | `d4c5f9` | Waiting on the reporter for more information. | Always |
| `ready-for-agent` | `0e8a16` | Fully specified, ready for an agent. | Always |
| `ready-for-human` | `1d76db` | Needs a human to implement. | Always |
| `wontfix` | `ffffff` | Will not be actioned. | Always |

If `setup-matt-pocock-skills` chose different triage label names, create those instead.

### Dependabot alerts and security updates

```sh
# Read. vulnerability-alerts: success means on, 404 means off. automated-security-fixes: target true.
gh api repos/OWNER/REPO/vulnerability-alerts
gh api repos/OWNER/REPO/automated-security-fixes -q .enabled
# Apply
gh api -X PUT repos/OWNER/REPO/vulnerability-alerts
gh api -X PUT repos/OWNER/REPO/automated-security-fixes
```

### Secret scanning and push protection

```sh
# Read. Target: both "enabled".
gh api repos/OWNER/REPO -q '{scanning: .security_and_analysis.secret_scanning.status, push_protection: .security_and_analysis.secret_scanning_push_protection.status}'
# Apply
gh api -X PATCH repos/OWNER/REPO -f 'security_and_analysis[secret_scanning][status]=enabled' -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```

### CodeQL default setup

Skip it when `.github/workflows/` already has a CodeQL workflow.

```sh
# Read. Target: "configured".
gh api repos/OWNER/REPO/code-scanning/default-setup -q .state
# Apply
gh api -X PATCH repos/OWNER/REPO/code-scanning/default-setup -f state=configured
```

### Workflow permissions

Covers both "Workflow permissions" and "Actions may open pull requests", in one call. A 409 means an org policy blocks it.

```sh
# Read
gh api repos/OWNER/REPO/actions/permissions/workflow
# Apply. default_workflow_permissions: read when `main` is unguarded, else as read.
# can_approve_pull_request_reviews: true for releases without a token, else as read.
gh api -X PUT repos/OWNER/REPO/actions/permissions/workflow -f default_workflow_permissions=<read|as read> -F can_approve_pull_request_reviews=<true|as read>
```

If release-please's first run failed in step 5 and Actions may now open pull requests, re-run it now: `gh workflow run release-please.yml --repo OWNER/REPO`. With a token chosen in Q9, it can't pass until the token is stored; leave it for the Report.

### SHA-pinned actions

```sh
# Read. Target: sha_pinning_required true.
gh api repos/OWNER/REPO/actions/permissions
# Apply, passing back the allowed_actions value you read
gh api -X PUT repos/OWNER/REPO/actions/permissions -F enabled=true -f allowed_actions=<as read> -F sha_pinning_required=true
```

### Approval for outside contributors

```sh
# Read. Target: "all_external_contributors".
gh api repos/OWNER/REPO/actions/permissions/fork-pr-contributor-approval -q .approval_policy
# Apply
gh api -X PUT repos/OWNER/REPO/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors
```

### Immutable releases

```sh
# Read. Target: true.
gh api repos/OWNER/REPO/immutable-releases -q .enabled
# Apply
gh api -X PUT repos/OWNER/REPO/immutable-releases
```

### Ruleset on `main`

Apply it last, and only when the precheck in Conditions passes on `origin/<default>`.

`ruleset.json` has two rules that came from real breakage:

- **Up to date before merging** (`strict_required_status_checks_policy: true`). Without it, two PRs that each pass on their own can break `main` once both merge, because neither ran CI on top of the other. Auto-merge doesn't update a branch that falls behind: the PR's author (or agent) updates it with the "Update branch" button or `gh pr update-branch`.
- **CodeQL blocks merges** (the `code_scanning` rule: security alerts of high or above, and errors). Keep it only when CodeQL runs on PRs: CodeQL default setup reads back `configured`, or `.github/workflows/` has a CodeQL workflow. Otherwise remove that rule from the JSON before applying it, since a PR waiting for CodeQL results that never come can't merge.

```sh
# Read: find this repo's own ruleset named "main" (org rulesets can't be changed here), then compare only
# the rule types and parameters that ruleset.json sets; GitHub adds defaults. Same: skip. Different: ask, then PUT.
gh api repos/OWNER/REPO/rulesets -q '.[] | select(.name == "main" and .source_type == "Repository") | .id'
gh api repos/OWNER/REPO/rulesets/<id> -q .rules
# Apply, using this skill folder's absolute path. To replace an existing one, use PUT repos/OWNER/REPO/rulesets/<id>.
gh api -X POST repos/OWNER/REPO/rulesets --input <this skill's folder>/references/ruleset.json
```

**Done when** every approved setting reads back as its target, or was declined or skipped with a reason.

---

## 7. Report

Tell the user:

- **Scaffold:** for a new project, the exact command that ran.
- **Files:** which were written, merged, or kept.
- **Skills:** how many were installed, and from which sources.
- **Settings:** which were applied, declined, or skipped, and why.
- **TODOs:** every one left in the written files.
- **Left for them**, where it applies:
  - storing the release token, if they chose one in Q9 (an admin does it, when they lack admin rights), then re-running release-please with `gh workflow run release-please.yml --repo OWNER/REPO`
  - re-running release-please with `gh workflow run release-please.yml --repo OWNER/REPO`, if its first run failed and you couldn't re-run it in step 6
  - merging the baseline PR, if one was opened
  - for Python + uv with releases: running `uv lock` on the first release PR's branch if it fails `uv sync --locked`
  - the deferred settings, for a guarded `main` with admin rights, once the baseline PR merges: the ones marked "deferred" in step 6's table whose "Applies when" otherwise holds, each as its section describes, with the commands. With releases and no token, release PRs then need closing and reopening to run their checks.
  - every step 6 setting except Labels whose "Applies when" holds (deferred ones included), for an admin to apply, when the user has no admin rights. `SECURITY.md`'s reporting link works only once they turn on private vulnerability reporting.
  - the ruleset, if it was skipped, with the reason
