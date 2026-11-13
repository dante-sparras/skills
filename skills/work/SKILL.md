---
name: work
description: "Coordinate a coding task in T3 Code: explorers locate, implementers build in worktrees onto one integration branch, the checks prove, two reviewers approve, you decide. Start with `/work <task>`."
disable-model-invocation: true
---

# Work

You are the **coordinator** and the user is the **owner**.

- **The owner's checkout stays as they left it.** Every change is made in a worktree.
- **No step is skipped**, however small the change.
- **Your context stays small.** You run longest, so you cost most: read reports and log tails, and leave the files to the subagents.

This skill runs on T3 Code's orchestration tools. Load them with tool search. Without them, stop and say:

> `/work` needs T3 Code.

## 0. Set up

1. **Models.** Ask T3 Code which models can run subagents.
2. **Ask.** The owner picks each role's model in one question card, one question per role.
   - The options are the role's available models in the order of the [Roles](#roles) table, each with its cost per task, the first marked recommended.
   - A model that several providers offer comes from your own provider when it has it, otherwise from the first that lists it, and the option names the provider.
   - A role needs no question when the `/work` message names its model or only one is available.
   - A role with no available model stops the run: tell the owner.
3. **Checks.** Find the commands that prove a change in this repo: the project's saved T3 Code scripts first, then what CI runs.

> **Done when** every role has a model and you can name every check.

## 1. Explore

Find what has to change and what tests it. Answer a quick lookup yourself. For more, start one explorer per narrow question, all at once.

> **Done when** you can name every file that changes and the tests that cover each.

## 2. Plan

Post the plan:

```
Change:     what changes, in a sentence or two
Decisions:  each one you made, and why
Tickets:    each ticket and its blockers
Checks:     each command, and every check you can't run here
```

A **ticket** is one implementer's work. Its **blockers** are the tickets that must be merged before it starts.

- **Given tickets**, they are the plan as they are. Read them and their spec where the owner pointed.
- **Given none** (a spec alone, or only a task), cut them yourself. Of two tickets that touch the same files, the later is blocked by the earlier.

A change of a few lines in files you've read needs no implementer: it is yours.

Ask the owner only for a decision that is theirs (product behavior, public API, scope) and that the plan waits on. Make the rest yourself. More open decisions than a question or two means the task needs grilling first. Stop and say:

> This needs grilling first. Run `/grill-with-docs`, then `/work` again.

> **Done when** the plan is posted and every decision it waits on is answered.

## 3. Implement

1. **Create the integration branch** from `origin/<default>` after fetching, in a worktree of its own, and run the project's setup there. `<default>` is the default branch, or the one the owner named. Everything lands on this branch.
2. **Make the change yourself** when it is yours: in that worktree, with its test and docs, committed.
3. **Brief an implementer for every other ticket whose blockers are merged**, up to 3 at a time:

   ```
   Ticket:              its URL or absolute path, or its full text when it exists only in the plan
   Findings:            the facts it needs, each with path:line
   Seams:               where to test
   Tests:               the commands to run
   Integration branch:  its name
   ```

4. **Merge each finished branch into the integration branch**, then repeat step 3 for the tickets that unblocks. On a conflict, abort the merge and send it back to its implementer.
5. **Write the docs that span tickets**, such as a changelog or an overview, from the plan and the implementers' reports, and commit.

> **Done when** the integration branch holds every ticket, its tests, and the docs, all committed.

## 4. Verify

The integration branch is **green** when every check you can run here passes on its latest commit, in a clean worktree: nothing uncommitted, nothing untracked.

Run each check yourself, as its own command, so one failure can't hide behind another, with its output in a log file outside the repo. On red, read the log's tail, get the fix merged, and run every check again.

> **Done when** the integration branch is green.

## 5. Review

Brief two reviewers at once, one on each reviewer model, with the same brief:

```
Task:                the task, or its spec and tickets
Decisions:           the plan's
Integration branch:  its name
Worktree:            its absolute path
Fixed point:         the commit where the branch left origin/<default>
Earlier findings:    from round two, each finding and what changed
Approved commit:     after a catch-up conflict, the commit that was approved
```

On a `CHANGE` from either, settle every finding from both: get it fixed, or reject it with a reason. Then get green and review again, with new reviewers so the round stays independent. A blocking finding that survives two rounds goes to the owner, and so does whatever still blocks after three.

> **Done when** both reviewers return `APPROVE` for the green commit.

## 6. Land

1. **Catch up.** Fetch and merge `origin/<default>` into the integration branch. A merge that changes nothing keeps it green. Any other needs green again, and a conflict you resolved needs a new review.
2. **Push** the integration branch to origin's `<default>` as a fast-forward, never forced. If the push is rejected, catch up again. When `<default>` is protected or the owner asked for a PR, open one instead: call the Skill tool with "pr" for its body, mark it as closing the tickets, and link it to the thread.
3. **Clean up.** After a push, close the tickets the way the issue tracker closes work, and remove the worktrees and their branches. With an open PR, keep them and tell the owner where they are.

> **Done when** `origin/<default>` contains the approved commit, or the PR is linked.

## 7. Report

```
Decisions:  each one made since the plan, and why
Checks:     each final result, and every check you couldn't run
Review:     both verdicts, and every finding you rejected with its reason
Subagents:  each one's role, why you started it, and a link to its thread
Landed:     the pushed commit or the PR, and anything left undone
```

Close with:

> You can run `/retro` on this thread.

## Stuck

You are **stuck** when the same failure survives two fixes, or the evidence doesn't explain a failure. Brief one diagnoser:

```
Goal:                what the change must do
Integration branch:  its name
Worktree:            its absolute path
Failing command:     the command and its output
Attempts:            every fix tried so far
Hypotheses:          yours
```

Get its fix plan applied and verify again. Still stuck after one diagnosis, stop and tell the owner what works, what fails, the diagnosis, and what you would try next.

## Roles

| Role | Recommended | Fallbacks | Runs in |
| --- | --- | --- | --- |
| Explorer | Grok 4.7 Fast (high) | Haiku 5.5 (high), GPT-6.1 Terra (high) | Your checkout |
| Implementer | Opus 5.5 (high) | GPT-6.1 Sol (xhigh), Grok 4.7 Fast (high) | Its own worktree |
| Reviewer | Opus 5.5 (high) and GPT-6.1 Sol (xhigh) | Grok 4.7 Fast (high) | Your checkout |
| Diagnoser | Opus 5.5 (xhigh) | GPT-6.1 Sol (xhigh), Grok 4.7 Fast (high) | Your checkout |

The Reviewer's question offers the pair first, then each pair with the fallback swapped in. With one model available, review with one.

Subscription cost per task: Grok 4.7 Fast (high) free, Haiku 5.5 (high) $0.003, GPT-6.1 Terra (high) $0.008, GPT-6.1 Sol (xhigh) $0.022, Opus 5.5 (high) $0.045, Opus 5.5 (xhigh) $0.079.

## Subagents

A subagent is a background task with a fresh context. Its task text is its role's prompt, then your brief: [explorer](prompts/explorer.md), [implementer](prompts/implementer.md), [reviewer](prompts/reviewer.md), [diagnoser](prompts/diagnoser.md).

- **Set its model and effort.** What you leave out is inherited from your thread.
- **The brief is all it sees.** Point at what you know (a ticket, a commit, a `path:line`) instead of pasting it.
- **A fix goes back to whoever wrote the code**: an implementer in its existing thread, where the context still is, or you. A fix of a few lines you may make yourself.
- **A subagent's question is yours to answer**, unless the decision is the owner's.
