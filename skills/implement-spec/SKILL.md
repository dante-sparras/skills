---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-skills`.

If the user passes a spec or ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

The goal is every ticket landed on main through one PR per task, each off main and never stacked, with the coordinator owning the landing order.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Start every subagent with a fresh context window. Communicate primarily through **context pointers**: to the spec, tickets, research notes, the ledger, PRs, and commits. Don't duplicate information already available via pointers.

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) before delegating. Start one `coordinator` to run the steps below. Give it the spec, ticket references, and this skill. Before starting a backup coordinator, have it recover from the first run's ledger and open PRs.

## Roles

- The `coordinator` owns the verdicts and the landing order. It plans, starts owners, sends each code-ready head to a verifier, and is the only agent that merges.
- Each `implementer` **owner** carries one task's PR from build to landing. Its own branch is the only branch it writes: it never merges, rebases another branch, or pushes main.
- Each `reviewer` verifier checks one head it did not write.
- An `explorer` researches the codebase or documentation when the tickets need it.

## Ledger

The coordinator keeps a **ledger** file outside the repo, beside the research notes, so a backup coordinator or a replacement owner can pick up where the last one stopped. It holds the landing mode, the file plan, each task's owner task ID, branch, worktree, and PR, and each verdict with its head SHA and patch-id. Update it on every change.

## File plan

Before launching any owner, list the files each ticket may touch. Group tickets that share a file into one **task**, unless one already blocks the other, since the task graph keeps those apart. If a group would then wait on itself through a ticket outside it, pull that ticket into the group too. A task blocks on every blocker of its tickets.

Launch a task only when every task it blocks on has landed on main and its files are disjoint from every open task's files. An owner that needs a file outside its plan stops and names the file. Add the file to its plan when no open task holds it. Otherwise the owner waits until the holding task lands.

## Verdicts

A verifier works in a checkout of the head. It re-runs the repo's checks, proves the tickets' behavior on the real surface, and checks the diff against the file plan. Then it calls the Skill tool with `code-review`, giving `origin/main` as the fixed point, the PR's tickets as the spec, and the PR's purpose as the intent. It returns `PASS` or `FAIL`, and fails a head only for a problem it can show: a failing run at the head, a finding the panel proved, or a wrong line in the diff. A problem main already has fails the head only when the PR copies it or newly reaches it. It reports anything else as a follow-up. Green CI and the owner's own report are not verdicts.

A verdict covers a patch, not a commit. Record the patch-id of the PR's diff from its base with `git diff $(git merge-base origin/main <head>) <head> | git patch-id --stable`. After a rebase, compute it again. The verdict carries over when the patch-id is unchanged. Otherwise verify the new head again.

## Landing mode

Read the repo's `AGENTS.md`, `CLAUDE.md`, and contributing guide, and the branch protection on main. The mode is **land** unless one of them reserves merging for a human, such as a rule that the owner reviews and merges every PR, or a required approval the coordinator cannot give. Then the mode is **hand off**. Never give or bypass an approval the forge enforces.

## Steps

The coordinator starts here.

1. Read the spec and tickets to understand the task graph.

2. If the tickets need codebase or documentation research, start an `explorer`. Have it save notes outside the repo where the owners can read them.

3. Settle the landing mode, write the file plan, and start the ledger.

4. From here on, act on events. An owner or verifier finishing, failing, hitting a usage limit, or asking a question wakes you. Answer a question. Replace an agent that failed or hit a limit with a fresh one of the same role per [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role), given the original brief and what the first one pushed.

5. Start a fresh `implementer` owner in the background for each launchable task on the frontier, each in its own worktree on its own branch off current main. Each owner:
   - calls the Skill tool with `tdd` to build its tickets, editing only the files in its plan
   - runs the typechecker and the single test files it touches often while it works, and the full test suite before it reports a head
   - pushes soon after starting and after each finished unit, and opens its PR off main early so CI runs alongside the work, writing the body with the `pr` skill and marking the PR as closing its tickets
   - rebases onto current main, proves the change on the real artifact, and reports the code-ready head
   - keeps CI green, reports every later head, and makes every write to its branch, including a rebase the coordinator calls for, with `git push --force-with-lease` pinned to the SHA it last pushed

6. When an owner reports a code-ready head, start a `reviewer` on it per Verdicts. On `FAIL`, send the verdict to the owner and verify the head it reports next. If two owners made the same mistake, call the Skill tool with `correct` before you land more work.

7. Act on each PR that passed at its current head with green CI, one at a time, in dependency order: a PR goes only after every PR it blocks on has landed. In **land** mode:
   - Fetch main. If main changed a file the PR touches, something the patch calls or depends on, or which checks run, have the owner rebase onto main. Compute the patch-id again, verify the new head if it changed, and wait for green CI.
   - Merge with `gh pr merge <pr> --squash`, then read back `gh pr view <pr> --json state,mergedAt,baseRefName`. A PR has landed only when it reads merged into main.
   - Resolve the PR's tickets the way the issue tracker closes work if merging did not, and clean up the owner's worktree.

   In **hand off** mode, stop at verified. Once every PR on the frontier passes at its current head with green CI, hand the user an ordered merge list: each PR with its verdict and head SHA, in the order you would land them, and the tasks still blocked behind them. Once the list is handed over, nobody pushes to a listed PR without the user's go. Report per step 10. Tell the user to rerun this skill after merging. The rerun recovers from the ledger and starts the next frontier off the new main.

8. If a landing changes the frontier, add the new tasks to the file plan and start them per step 5.

9. Once every ticket has landed, resolve the spec the way the issue tracker closes work and clean up all worktrees.

10. Report each PR with its verdict, whether it landed or waits on the merge list, and the follow-ups the verifiers reported.
