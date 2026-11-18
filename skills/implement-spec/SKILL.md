---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-skills`.

The goal is the entire spec implemented on a single **integration branch**, or landed through the repository's queue when it has a landing contract, with every ticket resolved the way the issue tracker closes work.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Start every subagent with a fresh context window.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

**Implementer subagents** should be run in the background where possible for maximum concurrency.

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) before delegating. Start one `coordinator` to run the steps below and own the integration branch. Give it the spec, ticket references, and this workflow. The coordinator starts workers, records their task IDs and branches, and runs one merger at a time. Before starting a backup coordinator, recover the integration branch and worker status from the first run.

## Steps

The coordinator starts here.

1. Read the spec and tickets to understand the task graph.

2. If the tickets need codebase or documentation research, start an `explorer`. Have it save notes outside the repo where the implementers can read them.

3. Run `python3 <skills>/land/scripts/land.py status` in the repository. If it prints a landing contract, other threads land on this repository through its queue, so an integration branch would go around it. Run the tickets through [coordinate](../coordinate/SKILL.md) instead of steps 3 to 6 and step 9: the frontier tickets are its tasks, and each lands as its own PR that closes its ticket. Pass it the research notes from step 2 as context pointers. Then continue at step 7: review the spec's landed commits and its open queue PRs together, and give the fixes to coordinate as one more task.

   Otherwise create the integration branch. If the issue tracker closes work through PRs, or the user asks for one, open a draft PR after the first merge in step 5 (a branch with no commits ahead of main can't open one), marked as closing the spec and tickets.

4. Use the `implementer` role for each fresh ticket worker, each in its own worktree on its own branch. Each worker:
   - confirms its worktree is based on the integration branch before starting, and resets onto it if not
   - calls the Skill tool with `tdd` to build the ticket
   - merges the integration branch tip into its own branch before reporting done

5. Once a worker completes, start a merger with the `implementer` role to merge its work to the integration branch. If two workers made the same mistake, call the Skill tool with `correct` before you merge more work.

6. If this changes the **frontier** of available tickets, kick off more **implementer subagents** to work on the new tickets. This allows for maximum concurrency.

7. Once all tickets are complete, call the Skill tool with `code-review` on the integration branch. Fix all issues raised by the code review with one fresh `implementer`.

8. If a draft PR exists, mark it ready for review. Otherwise, resolve each ticket the way the issue tracker closes work, and report the integration branch.

9. Clean up all **implementer subagent** worktrees.
