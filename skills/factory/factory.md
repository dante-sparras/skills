# The factory

The **factory** is a T3 Code workflow, [factory.ts](factory.ts), that ships the issues you label `ready-for-agent`, with no person to start it. On each pass it checks main, looks for open issues with that label, and starts a run for each one it can. A pass runs every ten minutes, when a skill files an issue, and when a PR merges, so a ticket starts as soon as its blocker lands. Each run takes one issue down the same path:

1. **A worker** builds the issue in one PR, briefed with `rules.md` and `worker.md`.
2. **Checks.** The run waits for the PR's checks. A red check or a conflict wakes the worker on its own thread.
3. **Comments.** A comment or review from a collaborator wakes the worker with it, as a request to weigh. A collaborator's request for changes holds the merge until they approve, or until you say to merge without them. A comment from anyone else comes to you first, and reaches the worker only if you send it. Bots are left out.
4. **A reviewer** reviews the head, briefed with `rules.md` and `reviewer.md`, and argues each finding with the worker until they agree, for at most three rounds.
5. **A person's go.** Every merge waits on your answer: merge, merge it yourself, or stop. A `NO AGREEMENT` verdict waits on your ruling.
   - **Where it asks.** Each question waits in the worker's thread, asked with the agent's question tool, so T3 shows that thread as waiting on you. Every agent settles its thread when its turn ends, so the threads you still see are the ones that need you. A thread that cannot ask leaves its question in T3 Code's Workflows page.
   - **Without asking.** A repo whose settings set `autoMerge` to `two-way` skips the merge question when the reviewer passed the PR and judged it a two-way door: cheap to roll back. The factory says so in a comment on the PR. A PR the two disagreed on, and one a collaborator holds, still wait on you.
6. **The merge** goes through `gh pr merge --match-head-commit`, so GitHub refuses it if the head moved after the review. A moved head goes back through checks and review.

Workers and reviewers return their results as data, which T3 checks against a schema, so a result with a field missing is sent back to the agent to fix. A worker that needs you to decide something returns its question as data too: the factory has the worker ask you in its own thread, and wakes it with your answer. A run survives a restart of T3 Code. It picks up at the step it was on.

## What happens after a run

- **A spec check.** When a merge closes the last open ticket of a spec, the factory puts the spec in `ready-for-agent`. The dispatcher starts a second workflow for it, `skills-factory-spec`, in which a reviewer proves the spec's user stories on main. `PASS` closes the spec. Each gap becomes a ticket of the spec, in `ready-for-agent` with the `bug` label, and the factory builds it like any other. A spec gets one check that finishes: when its gap tickets land, it closes. A check that could not finish says why on the spec. Put `ready-for-agent` back on the spec to check it again.
- **Repeats.** Agents return their friction as a kind and a target: the repo path or command it is about. Each run counts its friction in the store as it ends, under `skills-factory/repeats/<owner>/<repo>/<kind>/<target>`. The second sighting of a target files a guardrail issue in `ready-for-agent`, with every sighting as evidence, and the factory builds the fix with `correct`. A `broken` script or check needs one sighting. Later sightings comment on that issue. A reviewer's mechanical findings, the ones `review-pr` marks as candidates for a check, are counted the same way.
- **A missing verify skill.** A worker whose proof needs the running app, in a repo with no verify skill, returns `BLOCKED`. The factory files one issue that creates the skill, marks the task as blocked by it, and keeps the task's label. Once the skill lands, the dispatcher starts the task again, and the new worker continues the old one's PR.
- **Follow-ups** become issues in `needs-triage`. A follow-up whose title matches an open issue's adds a comment there instead.

## A red main

On each pass, the dispatcher reads the checks on main's newest commit. When one has failed, it files one issue in `ready-for-agent` with the `bug` label that names each failing check, and starts nothing else in that repo until the issue closes. Runs already open go on. A cancelled or skipped check does not count, and neither does one still running.

## What it needs

- T3 Code with **Settings → Labs → Workflows** on. `t3 workflow list` exits 0 when it is.
- A GitHub repo with the labels the `factory` skill creates, and `gh` signed in. The factory reads blockers, comments, and sub-issues, and merges, through `gh`.
- The skills installed side by side, since workers reach them by relative paths.

[SKILL.md](SKILL.md) installs it, holds its settings, and says how to retry, stop, or pause a run.

## Where issues come from

The factory builds only what an issue already settles, one PR per issue. The skills a person types file those issues: `debug` for a bug, `ticket` for a change that fits one PR, `spec` and then `ticket` for a feature, and `triage` for what is already on the tracker. Each follows [handoff.md](handoff.md).

## The files

The factory lives in the `factory` skill's folder, so it installs with the skills.

| File | Who reads it | What it holds |
| --- | --- | --- |
| [factory.ts](factory.ts) | T3 Code | The factory itself |
| [SKILL.md](SKILL.md) | The agent you type `/factory` to | How to set a repo up, its settings, what waits on you, and how to retry, stop, or pause a run |
| This file | You | What the factory runs, and what happens after a run |
| [model-roles.md](model-roles.md) | Any skill that starts an agent | Which model each role runs on, and how to set the roles |
| [handoff.md](handoff.md) | Any agent that files an issue for the factory | The checks before an issue goes to `ready-for-agent` |
| [agent-brief.md](agent-brief.md) | The same agents, and workers | The one shape of an issue the factory builds |
| [tracker.md](tracker.md) | Every agent that touches the tracker | The labels, and the `gh` commands for issues and PRs |
| [worker.md](worker.md) | Every worker | How to build an issue in one PR and settle its review |
| [reviewer.md](reviewer.md) | The reviewer of a PR, or of a finished spec | How to review a PR and argue each finding with its worker, and how to check a spec |
| [rules.md](rules.md) | Workers and reviewers | Trust, the AI marker, results, messages, git, PR tools, and how to run a skill |
