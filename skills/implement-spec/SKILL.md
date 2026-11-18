---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-skills`.

The goal is the entire spec implemented as verified PRs off trunk, one per ticket, which the user merges, with every ticket resolved the way the issue tracker closes work.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Start every owner and subagent with a fresh context window.

Communication to and from owners and subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) before delegating. Start one `coordinator` to run the steps below. Give it the spec, ticket references, and this workflow. Before starting a backup coordinator, recover the run file the first one kept.

## Steps

The coordinator starts here.

1. Read the spec and tickets to understand the task graph.

2. If the tickets need codebase or documentation research, start an `explorer`. Have it save notes outside the repo where the owners can read them.

3. Run the tickets through [coordinate](../coordinate/SKILL.md). Each frontier ticket is a task, and its blocking relationships are the task dependencies. Merge two tickets into one task only when they would touch the same files. Add these lines to every owner's brief:
   - the ticket and the research notes from step 2 as context pointers
   - call the Skill tool with `tdd` to build the ticket
   - mark the PR as closing its ticket when the issue tracker closes work through PRs

   A ticket blocked by another ticket whose PR is still open stacks on that PR, per coordinate step 2.

4. Once every ticket's PR is verified, merge every PR head into a throwaway local branch off trunk and call the Skill tool with `code-review` on it, since trunk. Send each finding to the owner of the PR it belongs to, and verify that PR again per coordinate step 3. A finding that spans PRs becomes a new task.

5. Hand the PRs to the user per coordinate step 7, then delete the throwaway branch. When the issue tracker does not close work through PRs, resolve each ticket the way it closes work once its PR merges.
