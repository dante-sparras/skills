---
name: factory
description: "Set up and run the factory, the T3 Code workflow that ships issues labelled ready-for-agent: a repo's labels, the model roles, the workflow's install, and its runs. Use when a person starts using these skills in a repo, asks what waits on them or what the factory is doing, or a skill reports that the factory is missing or stale."
disable-model-invocation: true
---

# Factory

The factory ships the work: it starts a worker for each issue labelled `ready-for-agent`, and asks the user before a merge. [factory.md](factory.md) says how it works. This skill sets it up and runs it. It takes in no work: the user types `/debug`, `/ticket`, `/spec`, or `/triage` for that.

`t3 workflow store list skills-factory/projects/<owner>/<repo>` prints the repo's settings when the factory is installed for it. Go by that, and by what the user asked. In PowerShell, `t3` is a `.cmd` file, so write each `"` inside a JSON argument as `\"`.

| The user | Do |
| --- | --- |
| Wants the model roles set or changed | [Configure model roles](model-roles.md#configure-model-roles), and nothing else |
| Asked nothing more, in a repo with settings | [Show what waits](#show-what-waits) |
| Asks about a run, or to retry, stop, pause, or change a setting | [Run it](#run-it) |
| Is in a repo with no settings | [Set the repo up](#set-the-repo-up) |

## Set the repo up

Nothing is written into the repo itself.

1. **Check the repo.** The skills keep issues on GitHub, through the `gh` CLI. `git remote -v` shows whether this repo is there. With no GitHub remote, get the repo URL from the user and wire it up: `git init` if needed, then `git remote add origin <url>`. Done when `gh repo view` prints the project from inside this directory. If it cannot, stop and say what is missing.

   The repo's folder is also a T3 project, since workers start in it: `t3_project_list` shows whether it is, and `t3 project add <folder>` adds it.

   A repo that an earlier version of these skills set up holds `docs/agents/` and an `## Agent skills` block in `AGENTS.md`. Nothing reads them now, so offer to remove them.

2. **Create the labels.** Create each label that [tracker.md](tracker.md#labels) names and the repo lacks, with `gh label create`. `gh label list` shows what exists.

3. **Set model roles.** Follow [Configure model roles](model-roles.md#configure-model-roles), unless the roles file already holds all three.

4. **Install the workflow.** If `t3 workflow list` fails, workflows are off: say that **Settings → Labs → Workflows** turns them on and that `/factory` picks up from here, and skip to the report.
   - **Copy** `factory.ts`, beside this file, to `skills-factory.ts` in the `workflows` folder of T3 home: `~/.t3/workflows/` by default. T3 reloads the folder on its own.
   - **Register the repo** with the [settings](#settings). Show them to the user before you write them.
   - **Check** that the dispatcher runs: `t3 workflow start skills-factory-dispatch --input '{"scheduledAt":"<now, as ISO 8601>"}' --key check/<now>`, then `t3 workflow show <run>`. With no ready issue it ends as `skipped`.

5. **Preflight.** Check what would stall a first run, and tell the user each check that fails. None of them stops the setup.

   | Check | How | When it fails |
   | --- | --- | --- |
   | `gh` can push | `gh api repos/<owner>/<repo> --jq .permissions.push` prints `true` | No worker can open a PR |
   | The merge method is allowed | `gh api repos/<owner>/<repo> --jq '{allow_squash_merge, allow_merge_commit, allow_rebase_merge}'` allows the `mergeMethod` you set | Every merge fails. Set a method the repo allows |
   | Nothing forces a person's review | `gh api repos/<owner>/<repo>/rules/branches/<default branch> --jq '[.[] \| select(.type == "pull_request")] \| length'` prints `0`, and `gh api repos/<owner>/<repo>/branches/<default branch>/protection --jq .required_pull_request_reviews` prints nothing or fails with 404 | The factory cannot approve its own PR, so every merge is the user's to make, with "I will merge it" |
   | PRs get checks | A workflow under `.github/workflows/` runs on `pull_request` | Nothing stalls: the factory waits a short while for checks, then goes on with the reviewer's proof alone. Say so |
   | The roles' models run | Each model in the roles file is in the catalog, per step 2 of [Resolve a role](model-roles.md#resolve-a-role) | A run falls back to the backup. With no roles file, every agent runs on the project's default model |
   | The app can be driven | The repo has a `verify-<app>` skill, or none of its changes shows in a running app | The first ticket that needs the app waits behind a ticket that creates the skill. Offer to read [create-verify-skill](../create-verify-skill/SKILL.md) and follow it now |

6. **Report** which labels you created, which roles are set, whether the factory is installed, and what the preflight found.

## Settings

One repo's settings are one key in the workflow store:

```sh
t3 workflow store set skills-factory/projects/<owner>/<repo> '<settings as JSON>'
```

| Field | Value |
| --- | --- |
| `project` | The repo's folder, as an absolute path |
| `repository` | `<owner>/<repo>` |
| `skillsFolder` | The absolute path of the folder that holds this skill's folder, with every other skill beside it |
| `defaultBranch` | The name after `origin/` in `git symbolic-ref --short refs/remotes/origin/HEAD` |
| `verifySkill` | The verify skill's path from the repo root, or `null` to use the first `.claude/skills/verify-*` folder on main |
| `maxActive` | How many runs may hold an agent at once, spec checks included. `4` is a good start |
| `mergeMethod` | `squash`, `merge`, or `rebase`, by the repo's settings |
| `enabled` | `true`. Set `false` to pause the repo |
| `autoMerge` | `never`, the default, asks the user before every merge. `two-way` merges without asking when the reviewer passed the PR and judged it cheap to roll back. Set `two-way` only when the user asks for it |

The model roles are not settings. The factory reads them from the roles files as each run starts, as [model-roles.md](model-roles.md) says.

## Show what waits

Gather everything that waits on the user, and show it as one list, oldest first in each group. Leave out a group with nothing in it.

1. **Questions and merges**: `t3 workflow questions --json`. Each is a run of this repo waiting on an answer: a merge, a ruling, a worker's question, a collaborator's hold.
2. **`needs-triage`**: the open issues with that label. Follow-ups, and issues the factory stopped on, each with a comment that says why.
3. **Waiting on a blocker**: the open `ready-for-agent` issues with an open blocker, per [tracker.md](tracker.md)'s count of open blockers, each with what blocks it.
4. **In progress**: `t3 workflow list --status running --json`, as one line per run.
5. **A stale install**: the second check in [handoff.md](handoff.md).
6. **Landed lately**: `t3 workflow list --status completed --json`, for the `skills-factory-ship` runs of this repo that ended in the last seven days. Each run's result names its PR. Mark the ones whose result has `asked` as `false`: the factory merged those without asking.

Then offer the next step for the first group that has something: answer a question here, with `t3 workflow signal`, or run `triage` on the `needs-triage` issues, by reading [triage](../triage/SKILL.md) and following it.

## Run it

- **Start a pass now**, without waiting for the timer, with the command in step 5 of [handoff.md](handoff.md). The factory starts one itself when a PR merges.
- **Answer a question** in T3 Code's Workflows page, or with `t3 workflow signal --run <run> --wait <question> '{"choice": "<one of its choices>"}'`. `t3 workflow questions` lists them.
- **Retry** an issue by putting `ready-for-agent` back. Every run ends by removing the label, unless it parked the issue behind another one. A run that stopped or was cancelled also moves the issue to `needs-triage`, and a run that stopped says why in a comment on the issue.
- **Stop** one run with `t3 workflow cancel <run>`. `t3 workflow show <run>` shows its steps.
- **Pause** a repo by setting `enabled` to `false` in its settings.
- **Update** the workflow by copying `factory.ts` again, when it differs from the installed file. T3 does not see changes to the original. A run keeps the workflow version it started with, so copy an update when no run is open.
- **Change a setting** by writing the whole settings object again, with the one field changed.
