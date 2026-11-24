# The factory

The **factory** is a T3 Code workflow, [factory.ts](factory.ts), that ships the issues you label `ready-for-agent`, with no person to start it. Every ten minutes it checks main, looks for open issues with that label, and starts a run for each one it can. Each run takes one issue down the same path:

1. **A worker** builds the issue in one PR, briefed with `rules.md` and `worker.md`.
2. **Checks.** The run waits for the PR's checks. A red check or a conflict wakes the worker on its own thread.
3. **Comments.** A comment or review from a collaborator wakes the worker with it, as a request to weigh. A collaborator's request for changes holds the merge until they approve, or until you say to merge without them. A comment from anyone else comes to you first, and reaches the worker only if you send it. Bots are left out.
4. **A reviewer** reviews the head, briefed with `rules.md` and `reviewer.md`, and argues each finding with the worker until they agree, for at most three rounds.
5. **A person's go.** Every merge waits on your answer: merge, merge it yourself, or stop. A `NO AGREEMENT` verdict waits on your ruling.
6. **The merge** goes through `gh pr merge --match-head-commit`, so GitHub refuses it if the head moved after the review. A moved head goes back through checks and review.

Workers and reviewers return their results as data, which T3 checks against a schema, so a result with a field missing is sent back to the agent to fix. A worker that needs you to decide something returns its question as data too: the factory asks you, and wakes the worker on its own thread with your answer. A run survives a restart of T3 Code. It picks up at the step it was on.

## What happens after a run

- **A spec check.** When a merge closes the last open ticket of a spec, the factory puts the spec in `ready-for-agent`. The dispatcher starts a second workflow for it, `skills-factory-spec`, in which a reviewer proves the spec's user stories on main. `PASS` closes the spec. Each gap becomes a ticket of the spec, in `ready-for-agent` with the `bug` label, and the factory builds it like any other. A spec gets one check that finishes: when its gap tickets land, it closes. A check that could not finish says why on the spec. Put `ready-for-agent` back on the spec to check it again.
- **Repeats.** Agents return their friction as a kind and a target: the repo path or command it is about. Each run counts its friction in the store as it ends, under `skills-factory/repeats/<owner>/<repo>/<kind>/<target>`. The second sighting of a target files a guardrail issue in `ready-for-agent`, with every sighting as evidence, and the factory builds the fix with `correct`. A `broken` script or check needs one sighting. Later sightings comment on that issue. A reviewer's mechanical findings, the ones `review-pr` marks as candidates for a check, are counted the same way.
- **A missing verify skill.** A worker whose proof needs the running app, in a repo with no verify skill, returns `BLOCKED`. The factory files one issue that creates the skill, marks the task as blocked by it, and keeps the task's label. Once the skill lands, the dispatcher starts the task again, and the new worker continues the old one's PR.
- **Follow-ups** become issues in `needs-triage`. A follow-up whose title matches an open issue's adds a comment there instead.

## A red main

On each pass, the dispatcher reads the checks on main's newest commit. When one has failed, it files one issue in `ready-for-agent` with the `bug` label that names each failing check, and starts nothing else in that repo until the issue closes. Runs already open go on. A cancelled or skipped check does not count, and neither does one still running.

## What it needs

- T3 Code with **Settings → Labs → Workflows** on. `t3 workflow list` exits 0 when it is.
- A GitHub repo set up by `setup-skills`, with `gh` signed in. The factory reads blockers, comments, and sub-issues, and merges, through `gh`.
- The skills installed side by side, since workers reach them by relative paths.

## Install

`setup-skills` does this, under [Install the factory](../setup-skills/SKILL.md#6-install-the-factory).

1. **Copy** `factory.ts` to `skills-factory.ts` in the `workflows` folder of T3 home: `~/.t3/workflows/` by default. T3 reloads the folder on its own. Copy it again after the skills update, since T3 does not see changes to the original. A run keeps the workflow version it started with, so copy an update when no run is open, or keep the old file's body registered until its runs end.
2. **Register the repo** in the workflow store, under `skills-factory/projects/<owner>/<repo>`:

   ```sh
   t3 workflow store set skills-factory/projects/<owner>/<repo> '<settings as JSON>'
   ```

   | Field | Value |
   | --- | --- |
   | `project` | The repo's folder, as an absolute path, or its T3 project id |
   | `repository` | `<owner>/<repo>` |
   | `skillsFolder` | The absolute path of the folder that holds the `factory` folder |
   | `defaultBranch` | The name after `origin/` in `git symbolic-ref --short refs/remotes/origin/HEAD` |
   | `readyLabel` | The `ready-for-agent` label in `docs/agents/triage-labels.md` |
   | `needsTriageLabel` | The `needs-triage` label there, for the follow-ups it files |
   | `specLabel`, `bugLabel`, `enhancementLabel` | Optional. The `spec`, `bug`, and `enhancement` labels there, when they differ from those names |
   | `verifySkill` | The verify skill's path from the repo root, or `null` to use the first `.claude/skills/verify-*` folder on main |
   | `maxActive` | How many runs may hold an agent at once, spec checks included. `4` is a good start |
   | `mergeMethod` | `squash`, `merge`, or `rebase`, by the repo's settings |
   | `enabled` | `true`. Set `false` to pause the repo |
   | `worker`, `reviewer` | Optional. A model role as `{"default": <model>, "backup": <model>}`, each `<model>` being `{"instanceId", "model", "options": [{"id", "value"}]}` from `orchestrator_capabilities`. Leave a role out to use the project's default model |

3. **Check** that the dispatcher runs: `t3 workflow start skills-factory-dispatch --input '{"scheduledAt":"<now, as ISO 8601>"}' --key check/<now>`, then `t3 workflow show <run>`. With no ready issue it ends as `skipped`.

## Run it

- **Hand it work** by labelling an issue `ready-for-agent`. An issue waits while any of its blockers is open: GitHub's own dependencies, or a `Blocked by` line or section in its body.
- **Answer it** in T3 Code's Workflows page, or with `t3 workflow questions` and `t3 workflow signal`. Every question of a run waits there, a worker's included.
- **Retry** an issue by putting `ready-for-agent` back. Every run ends by removing the label, unless it parked the issue behind another one. A run that stopped or was cancelled also moves the issue to `needs-triage`, where `triage` shows it, and says why in a comment on the issue.
- **Stop** one run with `t3 workflow cancel <run>`. **Pause** a repo by setting `enabled` to `false` in its settings.

## Where issues come from

The factory builds only what an issue already settles, one PR per issue. Type `/factory` to hand over work in conversation: it answers questions itself, and turns the rest into issues the factory can build, through `triage`, `interview`, or `plan`.
