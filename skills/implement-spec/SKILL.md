---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-skills`.

The goal is one PR for the whole spec, opened from a single **spec branch** (the integration branch) that holds every ticket, with merge order settled before the user reads it.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Start every subagent with a fresh context window. Communicate primarily through **context pointers**: to the spec, tickets, research notes, the ledger, and commits. Don't duplicate information already available via pointers.

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) before delegating. Start one `coordinator` to run the steps below. Give it the spec, ticket references, and this skill. Before starting a backup coordinator, have it recover from the first run's ledger and spec branch.

## Roles

- The `coordinator` is the only writer to the spec branch. It plans, starts workers, sends each worker's head to a verifier, merges, and pushes.
- Each `implementer` worker builds one task in its own worktree on its own branch. It commits there, reports its head SHA, and stops. Its own branch is the only branch it writes: it never merges, rebases the spec branch, or pushes main.
- Each `reviewer` verifier checks one worker head it did not write.
- An `explorer` researches the codebase or documentation when the tickets need it.

## Ledger

The coordinator keeps a **ledger** file outside the repo, beside the research notes, so a backup coordinator or a replacement worker can pick up where the last one stopped. It holds the file plan, each task's worker task ID, branch, worktree, and stuck-after time, and each verdict with its head SHA and patch-id. Update it on every change.

## File plan

Before launching any worker, list the files each ticket may touch. Group tickets that share a file into one **task**, unless one already blocks the other, since the task graph keeps those apart. If a group would then wait on itself through a ticket outside it, pull that ticket into the group too. A task blocks on every blocker of its tickets.

Launch a task only when its files are disjoint from every running task's files. A worker that needs a file outside its plan stops and names the file. Add the file to its plan when no running task holds it. Otherwise the worker waits until the holding task merges.

## Verdicts

A verifier re-runs the repo's checks at the worker's head, proves the tickets' behavior on the real surface, and audits the diff against the tickets and the file plan. It returns `PASS` or `FAIL`, and fails a head only for a problem it can show with a failing run or a wrong line in the diff. It reports anything else as a follow-up, and the coordinator lists follow-ups in the PR body. Green checks and the worker's own report are not verdicts.

A verdict covers a patch, not a commit. Record the patch-id of the worker's diff from its base with `git diff $(git merge-base <spec-branch> <head>) <head> | git patch-id --stable`. After a rebase, compute it again. The verdict carries over when the patch-id is unchanged. Otherwise verify the new head again.

## Steps

The coordinator starts here.

1. Read the spec and tickets to understand the task graph.

2. If the tickets need codebase or documentation research, start an `explorer`. Have it save notes outside the repo where the workers can read them.

3. Write the file plan and start the ledger.

4. Create the spec branch from main in the coordinator's own worktree.

5. Arm an hourly check, with `/loop 1h` where the host has it, that runs until no delegated work is left. Each tick probes every worker by its side effects, such as new commits or worktree changes, not its status text. A worker is stuck when it errors, cannot start turns, or shows nothing new past its stuck-after time, which you set at launch from how long similar tasks took. A worker waiting on you is not stuck, so answer it. Replace a stuck worker at once with a fresh `implementer` on the same branch, given the original brief and what the stuck one committed.

6. Start a fresh `implementer` in the background for each task on the frontier, each in its own worktree on its own branch from the spec branch tip. Each worker:
   - confirms its worktree is based on the spec branch tip before starting, and resets onto it if not
   - calls the Skill tool with `tdd` to build its tickets, editing only the files in its plan
   - commits, reports its head SHA, and stops

7. When a worker stops, start a `reviewer` on its head per Verdicts. On `FAIL`, start a fresh `implementer` on the same branch with the original brief and the verdict, then verify its new head. If two workers made the same mistake, call the Skill tool with `correct` before you merge more work.

8. Merge passed branches into the spec branch in dependency order: a task merges only after every task it blocks on has merged. For each one:
   - Rebase the worker's branch onto the spec branch tip inside its worktree. On a conflict, abort and give the rebase to a fresh `implementer` in that worktree.
   - Compute the patch-id again and verify the new head if it changed.
   - If the spec branch gained commits since the verdict, run the repo's checks on the rebased head.
   - Fast-forward the spec branch with `git merge --ff-only <worker-branch>` and push it.
   - After the first merge, open one draft PR from the spec branch to main, marked as closing the spec and tickets. A branch with no commits ahead of main can't open one.

9. If a merge changes the frontier, add the new tasks to the file plan and start them per step 6.

10. Once every ticket has merged, call the Skill tool with `code-review` on the spec branch. Give all fixes to one fresh `implementer`, then verify and merge its branch per steps 7 and 8.

11. Mark the PR ready for review and hand it to the user, who merges it. If the issue tracker doesn't close work through PRs, also resolve each ticket the way it does.

12. Stop the hourly check and clean up all worker worktrees.
