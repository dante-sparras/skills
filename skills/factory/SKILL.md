---
name: factory
description: "Set up and run the factory, the T3 Code workflow that ships issues labelled ready-for-agent: a repo's labels, the model roles, the workflow's install, and its runs. Use when a person starts using these skills in a repo, asks what waits on them or what the factory is doing, or a skill reports that the factory is missing or stale."
disable-model-invocation: true
---

# Factory

The factory ships the work: it starts a worker for each issue labelled `ready-for-agent`, and merges a PR once the user has approved it. [factory.md](factory.md) says how it works. This skill sets it up and runs it. It takes in no work: the user types `/debug`, `/ticket`, `/spec`, or `/triage` for that.

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
   | Nothing forces a person's review | `gh api repos/<owner>/<repo>/rules/branches/<default branch> --jq '[.[] \| select(.type == "pull_request")] \| length'` prints `0`, and `gh api repos/<owner>/<repo>/branches/<default branch>/protection --jq .required_pull_request_reviews` prints nothing or fails with 404 | GitHub blocks the factory's merge, since the `approved` label is not a review. Every merge is then the user's to make by hand, and the run finishes up after it |
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
| `maxActive` | How many runs may hold an agent at once, spec checks included. A PR that waits for the user's review holds none, since no run is open for it. `4` is a good start |
| `mergeMethod` | `squash`, `merge`, or `rebase`, by the repo's settings |
| `enabled` | `true`. Set `false` to pause the repo: nothing starts, open runs give their agents no more work, and no waiting PR is merged |
| `approver` | The user's GitHub login, which `gh api user --jq .login` prints. Only an `approved` label that this account put on is a go. It is also the account the agents post from, which is how the factory tells an agent's comment from another person's |
| `autoMerge` | `never`, the default, merges a PR only once the user has approved it. `two-way` also merges, without the user's review, a PR that the reviewer passed and judged cheap to roll back. Set `two-way` only when the user asks for it |

The model roles are not settings. The factory reads them from the roles files as each run starts, as [model-roles.md](model-roles.md) says.

## Show what waits

Gather everything that waits on the user, and show it as one list, oldest first in each group. Leave out a group with nothing in it.

Say first when the repo is held up. `t3 workflow store list skills-factory/main-red/<owner>/<repo>` names the issue that fixes a red main: while that issue is open, the factory starts nothing else in the repo. `t3 workflow list --status skipped` shows the newest passes, and a pass that could not read an issue says which.

1. **PRs that wait for the user's review**: `t3 workflow store list skills-factory/ready/<owner>/<repo>/`. Each entry is one PR: give its link, and say that the `approved` label merges it. One with `byHand` set is the user's to merge on GitHub. One with `rework` set goes back to its worker at the next pass.
2. **Questions**: the project's threads that are not settled, from `t3_thread_list` with `settled: false`. A worker's thread with a pending question, which `t3_pending_request` lists, waits on an answer: a ruling, or a worker's question. `t3 workflow questions --json` lists a question that no thread could ask.
3. **`needs-triage`**: the open issues with that label. Follow-ups, and issues the factory stopped on, each with a comment that says why.
4. **Waiting on a blocker**: the open `ready-for-agent` issues with an open blocker, per [tracker.md](tracker.md)'s count of open blockers, each with what blocks it.
5. **In progress**: `t3 workflow list --status running --json` and `--status waiting`, as one line per run. A run under `--status paused` stopped on an error: `t3 workflow show <run>` says which step, `t3 workflow resume <run>` tries it again, and it holds a slot until it is resumed or cancelled.
6. **A stale install**: the second check in [handoff.md](handoff.md).
7. **Landed lately**: `t3 workflow list --status completed --json`, for the `skills-factory-land` runs of this repo that ended in the last seven days. Each run's result names its PR. Mark the ones whose result has `asked` as `false`: the factory merged those without asking.

Then offer the next step for the first group that has something: open the PR that waits, answer a question in its thread, or run `triage` on the `needs-triage` issues, by reading [triage](../triage/SKILL.md) and following it. Never add the `approved` label yourself: it is the user's review.

## Run it

- **Start a pass now**, without waiting for the timer, with the command in step 5 of [handoff.md](handoff.md). The factory starts one itself when a PR merges.
- **Answer a question** in the thread that asks it. A question that no thread could ask waits in T3 Code's Workflows page: answer it there, or with `t3 workflow signal --run <run> --wait <question> '{"choice": "<one of its choices>"}'`. `t3 workflow questions` lists those.
- **Retry** an issue by putting `ready-for-agent` back. Every run ends by removing the label, unless it parked the issue behind another one. A run that stopped or was cancelled also moves the issue to `needs-triage`, and a run that stopped says why in a comment on the issue.
- **Stop** one run with `t3 workflow cancel <run>`. `t3 workflow show <run>` shows its steps. A cancelled run cannot settle its worker's thread, so settle it with `t3_thread_organize`.
- **Pause** a repo by setting `enabled` to `false` in its settings.
- **Update** the workflow by copying `factory.ts` again, when it differs from the installed file. T3 does not see changes to the original. A run keeps the workflow version it started with, so copy an update when no run is open: `t3 workflow list --status running` and `--status waiting` show them. Runs are short, since none stays open while a PR waits for review. For one that is open, wait, or cancel it and put `ready-for-agent` back afterwards: the next run goes on with the same PR.
- **Change a setting** by writing the whole settings object again, with the one field changed.
