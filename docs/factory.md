# The factory

The **factory** is a T3 Code workflow, [factory.ts](../skills/factory/factory.ts), that ships the issues you label `ready-for-agent`, with no person to start it. On each pass it checks main, looks for open issues with that label, and starts a run for each one it can. A pass runs every ten minutes, when a skill files an issue, and when a PR merges, so a ticket starts as soon as its blocker lands. Each run takes one issue down the same path:

1. **A worker** builds the issue in one PR, briefed with `rules.md` and `worker.md`.
2. **Checks.** The run waits for the PR's checks. A red check or a conflict wakes the worker on its own thread.
3. **Comments.** A comment or review from a collaborator wakes the worker with it, as a request to weigh. A collaborator's request for changes holds the merge until they approve, or until you add the `approved` label. A comment from anyone else never reaches the worker and never holds the PR: the factory lists it in its note on the PR, and you pass on what matters by commenting yourself. Bots are left out.
4. **A reviewer** reviews the head, briefed with `rules.md` and `reviewer.md`, and argues each finding with the worker until they agree, for at most three rounds.
5. **Your review.** A PR the reviewer passed waits for you, and the factory asks nothing: not whether to open it, and not whether to merge it. The run ends here. No run is open while the PR waits, so it can wait as long as you like, and it holds none of the repo's slots.
   - **How you say go.** Add the `approved` label to the PR. GitHub does not let you approve a PR your own account opened, and the factory opens every PR as you, so the label is your approval. With `approver` set, only a label that account put on counts. On a PR from another account, an approving review of the head counts too.
   - **How you say no.** Comment or ask for changes, and the worker picks it up. Close the PR, and the issue comes back to you in `needs-triage`. Merge it yourself, and the factory finishes up after you.
   - **What your go covers.** The commits that were there when you gave it. The factory notes the moment each new commit appears, and only a label put on after that merges it. It takes an older label off, and tells you again that the PR is ready. A comment of yours that changes no code leaves your go in place.
   - **How you hear of it.** The factory comments on the PR, and the worker's thread says so and stays in your list until the PR merges. Every other thread settles itself when its turn ends, so the threads you still see are the ones that need you.
   - **How soon it merges.** For a quarter of an hour after a PR becomes ready the factory looks every minute. After that each pass looks, which is every ten minutes.
   - **Without your review.** A repo whose settings set `autoMerge` to `two-way` merges a PR that the reviewer passed and judged a two-way door: cheap to roll back. The factory says so in a comment on the PR. A PR the two disagreed on, and one a collaborator holds, still wait for you.
   - **A pause.** The factory reads the repo's settings again at each step of a run, and before each merge. A repo you paused gets no more work from its agents and merges nothing, and a PR that was ready before you turned `autoMerge` off waits for your review like any other.
   - **A question.** A `NO AGREEMENT` verdict waits on your ruling: accept the PR as it is, send your rulings to the worker, or stop. Accepting it settles the findings, and the PR then waits for your review like any other. After your rulings a reviewer always looks again, whether or not the worker pushed. A worker may need a decision too. Those are asked in the worker's thread, with the agent's question tool, so T3 shows that thread as waiting on you. A thread that cannot ask leaves its question in T3 Code's Workflows page.
6. **The merge** is the work of a short run of its own, `skills-factory-land`. It goes through `gh pr merge --match-head-commit`, so GitHub refuses it if the head moved after the review.
   - **The worker is needed again** when a commit appeared, a collaborator commented, a check went red, or the branch conflicts with main or fell behind it. The next pass starts a run that goes on in the worker's own thread, and the PR comes back to you once a reviewer has passed it.
   - **GitHub lets only you merge it** when a rule on the branch asks for a review the label cannot give. The factory says so on the PR, and finishes up after you merged it by hand.
   - **A merge queue** takes a PR without merging it yet. Nothing that follows a merge happens until GitHub says the PR is in.

Workers and reviewers return their results as data, which T3 checks against a schema, so a result with a field missing is sent back to the agent to fix. A worker that needs you to decide something returns its question as data too: the factory has the worker ask you in its own thread, and wakes it with your answer. A run survives a restart of T3 Code. It picks up at the step it was on.

## What happens after a run

- **A spec check.** When a merge closes the last open ticket of a spec, the factory puts the spec in `ready-for-agent`. The dispatcher starts a second workflow for it, `skills-factory-spec`, in which a reviewer proves the spec's user stories on main. `PASS` closes the spec. Each gap becomes a ticket of the spec, in `ready-for-agent` with the `bug` label, and the factory builds it like any other. A spec gets one check that finishes: when its gap tickets land, it closes. A check that could not finish says why on the spec. Put `ready-for-agent` back on the spec to check it again.
- **Repeats.** Agents return their friction as a kind and a target: the repo path or command it is about. Each run counts its friction in the store as it ends, under `skills-factory/repeats/<owner>/<repo>/<kind>/<target>`. A target that two runs saw gets a guardrail issue in `ready-for-agent`, with every sighting as evidence, and the factory builds the fix with `correct`. One run counts once, however often its agents report the same thing, and when that issue was closed and the friction comes back, the count starts over. A `broken` script or check needs one sighting. Later sightings comment on that issue. A reviewer's mechanical findings, the ones `review-pr` marks as candidates for a check, are counted the same way.
- **A missing verify skill.** A worker whose proof needs the running app, in a repo with no verify skill, returns `BLOCKED`. The factory files one issue that creates the skill, marks the task as blocked by it, and keeps the task's label. Once the skill lands, the dispatcher starts the task again, and the new worker continues the old one's PR.
- **A run with no PR.** A worker that finds nothing to change opens no PR, so nobody reviewed anything. The factory moves the issue to `needs-triage` with the worker's reasons, and you close it if you agree.
- **Follow-ups** become issues in `needs-triage`. A follow-up whose title matches an open issue's adds a comment there instead.

## A red main

On each pass, the dispatcher reads the checks on main's newest commit. When one has failed, it files one issue in `ready-for-agent` with the `bug` label that names each failing check, and starts nothing else in that repo until the issue closes. That holds when the fix's own run stopped and left the issue in `needs-triage`: the repo then waits on you, and `/factory` says so first. The fix never waits for a free slot. Runs already open go on. A cancelled or skipped check does not count, and neither does one still running.

## What it needs

- T3 Code with **Settings → Labs → Workflows** on. `t3 workflow list` exits 0 when it is.
- A GitHub repo with the labels the `factory` skill creates, and `gh` signed in. The factory reads blockers, comments, and sub-issues, and merges, through `gh`.
- The skills installed side by side, since workers reach them by relative paths.

[SKILL.md](../skills/factory/SKILL.md) installs it, holds its settings, and says how to retry, stop, or pause a run.

## Where issues come from

The factory builds only what an issue already settles, one PR per issue. The skills a person types file those issues: `debug` for a bug, `ticket` for a change that fits one PR, `spec` and then `ticket` for a feature, and `triage` for what is already on the tracker. Each follows [handoff.md](../skills/factory/handoff.md).

## The files

The factory lives in the `factory` skill's folder, so it installs with the skills. This file does not: it is for you, and no agent reads it.

| File | Who reads it | What it holds |
| --- | --- | --- |
| [factory.ts](../skills/factory/factory.ts) | T3 Code | The factory itself: `ship` builds an issue up to a reviewed PR, `land` merges it, `spec` checks a finished spec, and `dispatch` is the pass that starts them |
| [SKILL.md](../skills/factory/SKILL.md) | The agent you type `/factory` to | How to set a repo up, its settings, what waits on you, and how to retry, stop, or pause a run |
| [model-roles.md](../skills/factory/model-roles.md) | Any skill that starts an agent | Which model each role runs on, and how to set the roles |
| [handoff.md](../skills/factory/handoff.md) | Any agent that files an issue for the factory | The checks before an issue goes to `ready-for-agent` |
| [agent-brief.md](../skills/factory/agent-brief.md) | The same agents, and workers | The one shape of an issue the factory builds |
| [tracker.md](../skills/factory/tracker.md) | Every agent that touches the tracker | The labels, and the `gh` commands for issues and PRs |
| [worker.md](../skills/factory/worker.md) | Every worker | How to build an issue in one PR and settle its review |
| [reviewer.md](../skills/factory/reviewer.md) | The reviewer of a PR, or of a finished spec | How to review a PR and argue each finding with its worker, and how to check a spec |
| [rules.md](../skills/factory/rules.md) | Workers and reviewers | Trust, the AI marker, results, messages, git, PR tools, and how to run a skill |
