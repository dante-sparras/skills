# The factory

The **factory** is a T3 Code workflow, [factory.ts](../skills/factory/factory.ts), that ships each issue labelled `ready-for-agent`, one PR per issue, with nobody to start it.

A **pass** starts every issue it can. One runs every ten minutes, when a skill files an issue, and when a PR merges.

## One issue, start to finish

| Step | What happens |
| --- | --- |
| 1. Worker | Builds the issue in one PR |
| 2. Checks | A red check or a conflict wakes the worker |
| 3. Comments | A collaborator's comment wakes the worker. Anyone else's is listed in the factory's note on the PR |
| 4. Reviewer | Argues each finding with the worker, for at most three rounds |
| 5. Your review | The run ends, and the PR waits for you, for as long as you like |
| 6. Merge | A short run of its own merges the PR once you say go |

The factory never asks whether to open a PR or to merge one.

## Your review

| You | The factory |
| --- | --- |
| Add the `approved` label | Merges the PR |
| Comment, or ask for changes | Wakes the worker. The PR comes back once a reviewer has passed it |
| Merge it yourself | Finishes up after you |
| Close it | Puts the issue in `needs-triage` |

- **The label is your approval**, since GitHub does not let you approve a PR your own account opened. With `approver` set, only that account's label counts.
- **It covers the commits you saw.** A later commit takes the label off, and the factory tells you when the PR is ready again.
- **You hear of it** on the PR, and in the worker's thread, which stays in your list until the PR merges.
- **It merges** within a minute for the first quarter of an hour, and at the next pass after that.
- **A question** is asked in the worker's thread. A `NO AGREEMENT` verdict is one: accept the PR as it is, send your rulings to the worker, or stop.

Two settings change this:

| Setting | Effect |
| --- | --- |
| `autoMerge: two-way` | Merges without your review a PR that the reviewer passed and judged cheap to roll back, and says so on the PR |
| `enabled: false` | Pauses the repo: its agents get no more work, and nothing merges |

## When the merge needs more

| Case | What happens |
| --- | --- |
| The head moved, a collaborator commented, a check went red, or the branch conflicts with main or fell behind it | The next pass wakes the worker in its own thread. The PR comes back once a reviewer has passed it |
| A branch rule asks for a review the label cannot give | The factory says so on the PR. You merge by hand, and it finishes up |
| A merge queue takes the PR | Nothing that follows a merge happens until the PR is in |

## After a run

| Case | What the factory does |
| --- | --- |
| A spec's last ticket lands | A reviewer proves the spec's user stories on main. `PASS` closes the spec. Each gap becomes a `bug` ticket |
| Two runs report the same friction | Files a guardrail issue, and builds the fix with `correct`. A `broken` script or check needs one report |
| The repo has no verify skill, and a proof needs the running app | Files an issue that creates the skill. The task waits behind it |
| A worker finds nothing to change | Opens no PR, and moves the issue to `needs-triage` with the worker's reasons |
| An agent returns a follow-up | Files it in `needs-triage` |

## A red main

Each pass reads the checks on main's newest commit. When one has failed:

- The factory files one `bug` issue that names each failing check, and starts it at once.
- Nothing else starts in that repo until the issue closes. Runs already open go on.
- If the fix's own run stopped, the repo waits on you, and `/factory` says so first.

## The files

No agent reads this file. The rest live in the `factory` skill's folder.

| File | Read by | Holds |
| --- | --- | --- |
| [factory.ts](../skills/factory/factory.ts) | T3 Code | The workflows: `ship`, `land`, `spec`, and `dispatch`, which is the pass |
| [SKILL.md](../skills/factory/SKILL.md) | The agent you type `/factory` to | Setup, settings, what waits on you, and how to run it |
| [model-roles.md](../skills/factory/model-roles.md) | Any skill that starts an agent | Which model each role runs on |
| [handoff.md](../skills/factory/handoff.md) | Any agent that files an issue | The checks before an issue goes to `ready-for-agent` |
| [agent-brief.md](../skills/factory/agent-brief.md) | The same agents, and workers | The shape of an issue the factory builds |
| [tracker.md](../skills/factory/tracker.md) | Every agent | The labels, and the `gh` commands |
| [worker.md](../skills/factory/worker.md) | Workers | How to build an issue in one PR |
| [reviewer.md](../skills/factory/reviewer.md) | Reviewers | How to review a PR, and check a spec |
| [rules.md](../skills/factory/rules.md) | Workers and reviewers | The rules both share |
