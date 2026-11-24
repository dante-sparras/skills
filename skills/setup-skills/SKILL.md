---
name: setup-skills
description: "Configure the settings the engineering skills read. Per repo, in `docs/agents/` and an `AGENTS.md` block: the issue tracker, triage labels, domain docs, and who merges. Globally, in `~/.config/skills/roles.json`: the model roles, which a repo can override in `.skills/roles.json`. Use when a person sets these skills up in a new repo, a skill reports that the tracker or roles are not configured, or a person wants to change the model roles."
disable-model-invocation: true
---

# Setup skills

For model setup alone, go straight to [Configure model roles](MODEL-ROLES.md#configure-model-roles).

Otherwise write the per-repo settings the engineering skills read: the issue tracker, the labels, the domain docs, and who merges. Explore, show what you found, confirm, then write.

## 1. Explore

Read what exists:

- `git remote -v`: is this a GitHub repo, and which one?
- `AGENTS.md` at the root: is there an `## Agent skills` section already?
- `GLOSSARY.md` and `GLOSSARY-MAP.md` at the root.
- `docs/agents/`: output from an earlier run of this skill.
- Monorepo signals: a `pnpm-workspace.yaml`, a `workspaces` field in `package.json`, or a populated `packages/*` where each package has its own `src/`. Without them the repo has a single context, as almost every repo does.

## 2. Ask

Summarise what is present and what is missing. Then take the sections in order, one answer each. Lead with the recommended answer so the user can accept it in a word, and skip a section that exploration already settled.

**Section A: Issue tracker.** Where issues live, so the skills know whether to call `gh issue create` or follow another workflow.

- **GitHub**: propose it when a `git remote` points there. It uses the `gh` CLI. With no such remote, get the repo URL from the user and wire it up (`git init` if needed, then `git remote add origin <url>`). Done when `gh repo view` prints the project from inside this directory. If it cannot, stop and say what is missing.
- **Other**, such as Jira or Linear: ask the user to describe the workflow in one paragraph, and record that.

The GitHub template has a "PRs as a request surface" flag, off by default. Leave it off without asking. The user can flip it in the file later.

**Section B: Labels.** Ask one question:

> Do you want to keep the default labels? (recommended: **yes**)

The defaults are the canonical roles, each label named after its role: the states `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`, the categories `bug` and `enhancement`, and `spec`. On a no, usually because the tracker already has other names such as `bug:triage`, collect the overrides, so the skills apply the existing labels.

**Section C: Domain docs.** Write **single-context**, one `GLOSSARY.md` at the root, without asking. Offer **multi-context**, a root `GLOSSARY-MAP.md` pointing to per-context glossaries, only when exploration found monorepo signals.

**Section D: Landing.** Ask one question:

> Once a PR has passed review and its checks, should the coordinator merge it, or leave the merge to you? (recommended: **the coordinator**)

The coordinator reads the answer. It still hands the merge to a person wherever branch protection requires an approval it cannot give.

**Section E: Required checks.** Runs on GitHub when the repo has CI and no ruleset or branch protection on the default branch requires a check. Read the exact check names with `gh api repos/<owner>/<repo>/commits/<default branch>/check-runs --jq '[.check_runs[].name] | unique'`. A workflow's file name or title is not a check name, and a wrong name blocks every merge. Leave out a check that runs only for some paths. Ask one question:

> Make `<checks>` required on `<default branch>`? (recommended: **yes**)

T3 wakes the coordinator when a required check passes and stays silent for any other, so without this a green PR waits until something else wakes the coordinator. Tell the user that pushes straight to the default branch stop working once the ruleset is active.

## 3. Confirm

Show the user a draft of the `## Agent skills` block and of each `docs/agents/` file. Let them edit before you write.

## 4. Write

**`AGENTS.md`** at the repo root, created if missing. Update an existing `## Agent skills` block in place, and leave the sections around it as the user wrote them. Claude reads `CLAUDE.md`, so make sure that file holds the line `@AGENTS.md`, creating it when the repo has none.

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

Read `GLOSSARY.md` at the repo root before exploring, or each glossary that `GLOSSARY-MAP.md` lists for the topic. Use its terms, and stay off the synonyms it lists under `_Avoid_`.

### Landing

[who merges a reviewed PR: "the coordinator" or "a person"].
```

**`docs/agents/`**, starting from the seed templates in this folder:

| File | Seed | Write when |
| --- | --- | --- |
| `issue-tracker.md` | [issue-tracker-github.md](./issue-tracker-github.md), or the user's description for another tracker | Always |
| `triage-labels.md` | [triage-labels.md](./triage-labels.md) | Always |

**Labels**, on GitHub: create each one the tracker lacks with `gh label create`. That is the configured labels, and `map`, `map:research`, `map:prototype`, `map:interview`, and `map:task`.

**Land the files** before anything else changes the repo's rules: commit them on a `chore/setup-skills` branch, open a PR, and merge it or hand it to the user. Workers start from the default branch, so until this lands they see none of it.

**Required checks**, on a yes to Section E, once the files have landed: `gh api --method POST repos/<owner>/<repo>/rulesets --input <file>`, with the body below. A `403` means GitHub does not offer rulesets for this repo on its plan: say so and move on.

```json
{
  "name": "main: required checks",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{ "context": "<check>" }, { "context": "<another check>" }]
      }
    }
  ]
}
```

## 5. Set model roles

Follow [Configure model roles](MODEL-ROLES.md#configure-model-roles).

## 6. Report

Tell the user which files you wrote. They can edit `docs/agents/*.md` directly, and rerun model setup alone to change the roles.
