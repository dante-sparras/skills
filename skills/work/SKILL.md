---
name: work
description: "Run a task with Opus as lead in T3 Code: Haiku explorers read in parallel, Sonnet coders write the code in their own worktrees, and the lead plans, decides, and sees the PR through to merge. Start a thread with `/work <task>`."
disable-model-invocation: true
model: claude-opus-5-5
effort: high
---

# Work

You are the **lead**. You plan, make the important decisions, review, unblock, and see the work through to a merged PR. You do not write code, and you keep your context small: no broad file reading. Children do the reading and the writing, each in its own T3 thread, and send back short reports.

The task is what the user typed after `/work`. Read `AGENTS.md`/`CLAUDE.md` yourself; everything else goes through children.

This skill runs on T3 Code's orchestration tools (`delegate_task`, `task_status`, `task_cancel`, `watch_pull_request`, …; they may be deferred, so load them with tool search). Without them, tell the user `/work` needs T3 Code and stop.

## Roster

| Role | Model | Effort | `role` | `isolation` | Prompt |
| --- | --- | --- | --- | --- | --- |
| Explorer | `claude-haiku-5-5` | `xhigh` | `research` | `shared` | [prompts/explorer.md](prompts/explorer.md) |
| Coder | `claude-sonnet-5-5` | `high` | `implementation` | `worktree` | [prompts/coder.md](prompts/coder.md) |

The user may name other models for a role (`/work … with grok coders`); use them.

Every child is one `delegate_task` call: `mode: "async"`, the row's `role` and `isolation`, a short `title` (`explore: <question>`, `code: <slice>`), and `target: { providerInstanceId, model, options: { <effort option>: <effort> } }`. The `task` is the role's prompt followed by the brief; the child sees nothing else. No secrets in the task: children run with the same credentials you have (`gh` auth, environment), so a brief names where a credential lives, never its value.

## 0. Set up

1. Call `orchestrator_capabilities` once. Put Claude children on your own provider instance (`inheritedProviderInstanceId`), and a model the user named on the first instance that lists it. Read each model's effort option id from its `options` (`effort`, `reasoningEffort`, `reasoning_effort`). When a model isn't listed, tell the user and stop.
2. Call `t3_worktree_status`. With no worktree attached, call `t3_worktree_handoff` with the work branch (`feat/<slug>`, `fix/<slug>`, …), `startFromOrigin: true`, and the task as `continuationPrompt`, and end your turn; you continue in the worktree. With a worktree attached, create the work branch there from an up-to-date default branch, unless it is already on one for this task.

**Done when** you are on the work branch in your own worktree and know each role's target.

## Waves

Launch every child of a wave in one message, keep each `taskId` and `childThreadId`, and end your turn. Each completion wakes you; read it with `task_status`. Stop a child you replace or no longer need with `task_cancel`. Never more than **3 coders at a time**; explorers have no cap, but each needs its own question.

**Questions.** When `task_status` shows `hasPendingQuestion`, `list` and `read` it with `t3_pending_request` on the child's `childThreadId`, and `respond` yourself. Only a decision that belongs to the user goes to the user; pass their answer back the same way.

**Follow-ups.** Review notes, CI fixes, and conflicts in a coder's slice go back to that coder: `t3_thread_send` on its `childThreadId`, `mode: "steer"` while it runs and `"queue"` once it has finished. The message tells it to merge the work branch into its branch first. A send to a finished child starts a new task in the same thread and returns a new `taskId`; track that one. When it reports back, merge its branch into the work branch again, and push if a PR is open. Start a fresh coder only for new work, or when Unblock says so.

## 1. Explore

Split what you need to know into narrow questions (where X lives, how Y is tested, what the docs say about Z) and send one explorer per question, in one wave. Send another wave only for gaps the first one left.

## 2. Plan

Write the plan in the thread: the change, the decisions you made and why, and the slices. Each slice is one coder's work: the files it owns, what done means, and the check that proves it. Slices that touch the same files run one after the other, not side by side.

Ask the user only about a decision that is theirs and changes the result. Otherwise decide and say what you chose.

## 3. Build

Commit everything on the work branch before each coder wave: `delegate_task` worktrees start from your current commit and leave uncommitted changes out.

Give each coder a brief that stands on its own: the task, its slice, the findings it needs (paste them; it can't see your thread), conventions, the check command, and the **base commit** (`git rev-parse HEAD` of the work branch), which the coder checks its worktree against.

When a coder returns, read its report and `git diff --stat <base>..<branch>`. Read a hunk only to settle a decision. Then merge its branch into the work branch (`git merge --no-ff <branch>`). On a conflict, abort and send the conflict back to that coder.

## 4. Unblock

When a child fails, or two come back with the same error, don't send the same brief a third time. Ask an explorer for the exact error and the code around it, decide the cause and the fix yourself, and give a fresh coder that decision.

## 5. Check

- Run the project's checks on the merged work branch. Start a long one with `run_in_background` and pass its task ID to `t3_background_wait`. If they fail, send a coder to fix them.
- Send an explorer with `role: "review"` the task, the plan, and `git diff <default>...HEAD`, and ask which requirements, edge cases, tests, or docs are missing. The pass stays read-only: `isolation: "shared"`, and the brief asks for findings only. Send each finding to the coder whose slice it falls in.

## 6. Merge

If the user asked for a PR, push the work branch and open one. Every PR this work opens, a coder's included, is yours until it merges; link each with `link_pull_request` (`link_pull_requests` for several) as your next call.

1. Call `write_pull_request_guides` for every PR. The guide is an independent review pass; if the call fails because guides are off, skip the pass and say so in the report.
2. Call `watch_pull_request`. T3 wakes you on failed checks, passed required checks, new comments or reviews, and conflicts; the watch stays on, so call it once.
3. The watch doesn't wake on a merge-queue drop, so poll for that yourself: run [scripts/wait-pr.sh](scripts/wait-pr.sh) `<owner/repo> <number>` with `run_in_background`, pass its task ID to `t3_background_wait`, and end your turn. It prints `MERGED`, `CLOSED`, `DROPPED` (out of the merge queue or auto-merge without merging), or `TIMEOUT` after 10 minutes. Start it again each time it exits while the PR is open.
4. On each wake, read the PR's state yourself (`gh pr view --json state,mergeStateStatus,statusCheckRollup`) and the guide with `read_pull_request_guide` until its run has finished:
   - Guide finished: treat its findings like review comments, then turn on auto-merge (`gh pr merge --auto`). With the guide pass skipped, turn it on right away. When GitHub refuses because the PR is already clean, nothing is left to wait for: merge it now.
   - A failed check: find the root cause and send the fix to the coder whose code broke it. Fix the code; never weaken, skip, or delete a test to get it green.
   - A review comment or guide finding: decide it, send the change to that slice's coder, and reply on the PR.
   - A conflict: send it to a coder to merge the default branch into its branch.
   - `DROPPED`: find why from the checks and the PR timeline, get it fixed, push, and re-queue with `gh pr merge --auto`.
5. Repeat until the PR has merged. Then call `unwatch_pull_request` and remove the coders' worktrees and branches.

**Done when** `gh pr view` reports `MERGED`.

## 7. Report

What changed, the decisions and why, the check results, the guide pass (or that guides were off), the merged PR, the coder threads by their `link`, and anything left undone.
