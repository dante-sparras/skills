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
- Which of `triage`, `to-spec`, and `wayfinder` are installed, as a folder beside this one or a name among your skills. The first two decide whether Section B runs. `wayfinder` decides whether its labels are created.
- Monorepo signals: a `pnpm-workspace.yaml`, a `workspaces` field in `package.json`, or a populated `packages/*` where each package has its own `src/`. Without them the repo has a single context, as almost every repo does.

## 2. Ask

Summarise what is present and what is missing. Then take the sections in order, one answer each. Lead with the recommended answer so the user can accept it in a word, and skip a section that exploration already settled.

**Section A: Issue tracker.** Where issues live, so the skills know whether to call `gh issue create` or follow another workflow.

- **GitHub**: propose it when a `git remote` points there. It uses the `gh` CLI. With no such remote, get the repo URL from the user and wire it up (`git init` if needed, then `git remote add origin <url>`). Done when `gh repo view` prints the project from inside this directory. If it cannot, stop and say what is missing.
- **Other**, such as Jira or Linear: ask the user to describe the workflow in one paragraph, and record that.

The GitHub template has a "PRs as a request surface" flag, off by default. Leave it off without asking. The user can flip it in the file later.

**Section B: Labels.** Runs only when `triage` or `to-spec` is installed. Ask one question:

> Do you want to keep the default labels? (recommended: **yes**)

The defaults are the canonical roles, each label named after its role: the states `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`, the categories `bug` and `enhancement`, and `spec`. On a no, usually because the tracker already has other names such as `bug:triage`, collect the overrides, so the skills apply the existing labels.

**Section C: Domain docs.** Write **single-context**, one `GLOSSARY.md` at the root, without asking. Offer **multi-context**, a root `GLOSSARY-MAP.md` pointing to per-context glossaries, only when exploration found monorepo signals.

**Section D: Landing.** Ask one question:

> Once a build has verified a PR, should the coordinator merge it, or leave the merge to you? (recommended: **the coordinator**)

The `implement` skill reads the answer. It still hands the merge to a person wherever branch protection requires an approval it cannot give.

## 3. Confirm

Show the user a draft of the `## Agent skills` block and of each `docs/agents/` file. Let them edit before you write.

## 4. Write

**`AGENTS.md`** at the repo root, created if missing. Update an existing `## Agent skills` block in place, and leave the sections around it as the user wrote them.

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

[one-line summary of layout: "single-context" or "multi-context"]. See `docs/agents/domain.md`.

### Landing

[who merges a verified PR: "the coordinator" or "a person"].
```

**`docs/agents/`**, starting from the seed templates in this folder:

| File | Seed | Write when |
| --- | --- | --- |
| `issue-tracker.md` | [issue-tracker-github.md](./issue-tracker-github.md), or the user's description for another tracker | Always |
| `domain.md` | [domain.md](./domain.md) | Always |
| `triage-labels.md` | [triage-labels.md](./triage-labels.md) | Section B ran. Otherwise leave out the file and the `### Triage labels` sub-block |

**Labels**, on GitHub: create each one the tracker lacks with `gh label create`. That is the configured labels when Section B ran, and `wayfinder:map`, `wayfinder:research`, `wayfinder:prototype`, `wayfinder:interview`, and `wayfinder:task` when `wayfinder` is installed.

## 5. Set model roles

Follow [Configure model roles](MODEL-ROLES.md#configure-model-roles).

## 6. Report

Tell the user which files you wrote. They can edit `docs/agents/*.md` directly, and rerun model setup alone to change the roles.
