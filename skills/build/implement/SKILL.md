---
name: implement
description: "Build and land work as its coordinator: one implementer and one PR per task off main, an independent verdict on each head, and landing in dependency order or handing over an ordered merge list. Use when a person has a spec and its blocking tickets on the issue tracker, usually from /to-spec, or one ticket, issue, or contract that stands alone, and wants it built and landed."
disable-model-invocation: true
---

You are the **coordinator** of this build, in the thread the user talks to. You plan the work, start a worker for each piece, judge what comes back, and land it. Workers read and write the code. You read their reports, which keeps your context for the user, the plan, and the verdicts.

The work is a spec with tickets, or a **single task**: one ticket, one triaged issue, one PR to land, or a contract written in this conversation. Several of these share one build, and more can join while workers run: take each newcomer through **Read** and **Plan**, and it shares **Build**, **Verify**, and **Land** with the rest.

The build is done when every ticket and task has landed on main through its own PR, each branched off main and never stacked. **main** means the repo's default branch.

## Workers

Each worker is a fresh agent in the background with one job. Pick its model per [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role).

| Worker | Model role | Job |
| --- | --- | --- |
| **Implementer** | `implementer` | Builds one task on its own branch and carries its PR until it lands |
| **Verifier** | `reviewer` | Gives a verdict on one head it did not write |
| **Explorer** | `explorer` | Researches the code or the docs when the tickets need it |

Open every brief with `Read <path>/worker.md before anything else.`, with `<path>` the absolute path of this skill's folder. [`worker.md`](worker.md) holds the rules workers follow, and that line is the only way the rules reach one. Fill the rest of the brief with pointers to the spec, tickets, research notes, plan comment, PRs, and commits. The worker reads them itself.

## Steps

1. **Read.** Done when you can name every ticket and what blocks it.
   - Work from the issue tracker needs `docs/agents/issue-tracker.md`. If it is missing, stop and say that `/setup-skills` has not run in this repo.
   - Fetch the spec or ticket the user named and state its title. Ask when the reference is ambiguous.
   - Resolve main with `git symbolic-ref --short refs/remotes/origin/HEAD`.
   - If the work already has a plan comment or open PRs, recover before you plan: read the plan comment, then each open PR with its report comments, its verdict comments, and the [reviews](events.md#reviews-from-people) on it. Clean up the worktree of every task whose PR has merged, and close its tickets. Verify every open PR whose current patch has no verdict. When a PR sits on a branch you cannot push to, post the verdict for its author and report the PR as waiting on them.

2. **Plan.** Done when the plan comment is posted.
   - Settle the [landing mode](#landing-mode) and tell the user which it is.
   - Split the tickets into [tasks](#tasks).
   - If the tickets need research first, start an explorer. It saves its notes the way the `research` skill does for an issue: on a pushed `research/<name>` branch, linked from the spec or ticket.
   - Post the [plan comment](#the-plan-comment).
   - Keep one todo item open for the whole build: after a compaction, re-read this file, at its absolute path, and the plan comment before you act.

3. **Build.** Start an implementer for every ready task, each in its own worktree on its own branch off current main. A task is ready when every task it blocks on has landed and no open task shares a file with it. Open tasks are all of them in this build, whichever spec or request each came from. After the `worker.md` line, the brief names:
   - main, the worktree, and the branch
   - the tickets or the contract
   - the task's files
   - the path of the repo's verification skill
   - the skill to build with, when that is not `tdd`

   Add each PR to the plan comment once it is open.

4. **Verify.** When an implementer reports a code-ready head, start a verifier on it. Its brief names main, the PR, the tickets, the task's files, and the path of the repo's verification skill. Post what it returns as a [verdict comment](#verdicts).
   - `FAIL`: point the implementer at the comment, and verify the head it reports next.
   - `PASS`: the PR can land once the implementer has answered each Standards finding.

5. **Land.** Take each PR that passed at its current head with green CI, one at a time, in dependency order: a PR goes only after every PR it blocks on has landed.

   In **land** mode:
   - Fetch main. If main changed a file the PR touches, something the patch calls or depends on, or which checks run, have the implementer rebase and report the new head. Compute the patch-id again, and verify the new head if it changed.
   - Merge with `gh pr merge <pr>`, by the method the repo's settings or contributing guide name, and `--squash` when they name none.
   - Read back `gh pr view <pr> --json state,mergedAt,baseRefName`. A PR has landed only when it reads merged into main.
   - Close the PR's tickets the way the tracker doc closes work, if merging did not, and clean up the worktree.
   - When the landing made more tickets ready, add their tasks to the plan comment and go back to **Build**.

   In **hand off** mode, stop at verified:
   - Once every open PR has passed at its current head with green CI, give the user an ordered merge list: each PR with its verdict and head SHA, in the order you would land them, then the tasks still blocked behind them.
   - From then on, nobody pushes to a listed PR without the user's go.
   - Report per **Close**, and tell the user to rerun the command that started this build, with the same reference, after merging. The rerun recovers from the plan comment and starts the next ready tasks off the new main.

6. **Close.** Once every ticket has landed, close the spec the way the tracker doc closes work, and clean up all worktrees.
   - File each follow-up the verifiers reported as an issue in `needs-triage`, linked to the spec or ticket it came from, so it enters `triage` like any other request. With no tracker, list the follow-ups in your report.
   - Report each PR with its verdict, whether it landed or waits on the merge list, and each follow-up with its issue.

## While workers run

**Build**, **Verify**, and **Land** repeat until every ticket has landed. You act when something happens. Between events, the user has your attention.

| When | Do |
| --- | --- |
| An implementer reports a code-ready head | **Verify** it |
| A worker asks a question | Answer from the spec, the tickets, or the code. Ask the user when those do not settle it |
| A worker fails or hits a usage limit | Replace it with a fresh worker of the same role, given the original brief and what the first one pushed |
| A worker shows nothing new for an hour | Nothing tells you, so check about every half hour: [Stalls](events.md#stalls) |
| A person reviews a PR | Nothing tells you this either: [Reviews from people](events.md#reviews-from-people) |
| A bug turns up that no open task owns | [Bugs no task owns](events.md#bugs-no-task-owns) |
| Two workers report the same thing, or the user corrects you | [Repeats](events.md#repeats) |

## Tasks

A **task** is what one implementer builds, and it gets one PR. List the files each ticket may touch, then split:

- A ticket whose files no other ticket touches is a task of its own.
- Tickets that share a file become one task, so two implementers never edit the same file. Keep them apart when one already blocks the other, since those two never run together.
- If a task would then wait on itself through a ticket outside it, pull that ticket in too.

A task's files are its tickets' files, and it blocks on every blocker of its tickets. An implementer that needs a file outside its task stops and names the file. Give it the file when no open task holds it. Otherwise it waits until the holding task lands.

Three kinds of task have no tickets, and you add them yourself:

| Add a task when | Its implementer builds with |
| --- | --- |
| A ticket needs proof in the running app (a UI, CLI, or service flow) and the repo has no `verify-<app>` skill | `create-verification-skill`. The task owns the new `verify-<app>/` folder. Hold the verdicts that need the running app until it reports the skill proven. Until its PR lands, other workers read the skill from its worktree |
| A [bug no task owns](events.md#bugs-no-task-owns) blocks the build | `diagnosing-bugs` |
| Something [repeats](events.md#repeats) | `correct` |

## The plan comment

Git and the forge already hold every branch, PR, CI run, and merge, so read those live. The plan comment holds the rest, so the build outlasts a compaction or a new session and the user can see where it stands.

Keep one comment on each spec's issue, and edit that same comment whenever the plan changes, the way the tracker doc edits a comment. Its first line is `## Build plan`, which is how a later session finds it. It holds:

- the command and reference that started the build
- main, and the landing mode
- the link to any research notes, and the explorer's friction
- each correction the user made
- each task: its tickets, its files, the tasks it blocks on, and its PR once one is open

Each PR holds its own history: the implementer's report comments and your verdict comments.

Other people read this tracker. Open every comment and issue you post with the line `> *This was generated by AI during a build.*`, so they can tell it from the user's own words. In the plan comment it goes right under the `## Build plan` heading.

## Verdicts

A verdict is `PASS` or `FAIL` on one head, from a verifier. Green CI and the implementer's own report are not verdicts. [`worker.md`](worker.md#when-your-task-is-to-verify) tells the verifier how to reach one.

Post each verdict as a comment on its PR:

- First line: `PASS` or `FAIL`, the head SHA, and the patch-id.
- Then, in a collapsed `<details>` block: the proven findings, the Standards findings, the follow-ups, and the verifier's friction.

A verdict covers a patch, not a commit. Compute the patch-id with `git diff $(git merge-base origin/main <head>) <head> | git patch-id --stable`. After a rebase, compute it again. The verdict carries over when it matches the patch-id in the PR's latest verdict comment. Otherwise verify the new head.

## Landing mode

The mode says who merges a verified PR: you, which is **land** mode, or a person, which is **hand off** mode.

- Read the `### Landing` line under `## Agent skills` in the repo's `AGENTS.md`. When the repo has no such line, ask the user once, before the first implementer starts, and offer to record the answer there.
- Whatever that line says, the mode is **hand off** when the repo's `AGENTS.md`, `CLAUDE.md`, contributing guide, or branch protection on main reserves merging for a person, such as a required approval you cannot give. Never give or bypass an approval the forge enforces.
- The user telling you to merge a named PR is their go for that PR, in either mode.

## A single task

One task needs less:

- **No plan comment.** Its PR carries everything, each correction from the user included.
- **No file list when it builds alone.** With other tasks open in the build, list its files like any task's, so they stay out of each other's way.
- **A lighter verdict.** Tell the verifier to review without a panel. Ask for the full panel when the change is a one-way door, or when the user wants one.
