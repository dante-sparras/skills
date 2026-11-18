---
name: coordinate
description: "Run many T3 owner threads on one repository at once, one PR each, parallel off trunk, verified on the exact head and handed to the user to merge. Use for 'coordinate', 'run these tasks in parallel threads', 'one PR per task', or when implement-spec runs a spec's tickets."
---

# Coordinate

You own the verdicts, never the PRs. Each task gets one owner thread that carries its PR from build to verified. Nothing is handed to the user until a verifier that never wrote the code has proven the head that would merge. The user merges every PR.

| Term | Meaning |
| --- | --- |
| Run | One coordinator's set of tasks on one repository, named by a short slug. |
| Task | One change with its own evidence and its own PR. |
| Owner | The worker thread that builds one task's PR, reports its heads, and never merges. |

For a spec with tickets, start from [implement-spec](../implement-spec/SKILL.md). Its coordinator runs this skill with the frontier tickets as tasks.

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) before launching anything. Owners use the `implementer` role and verifiers the `reviewer` role, each default first and backup once on failure. When the user asks for the coordinator in its own thread, launch that thread with the `coordinator` role's model.

## The run file

Keep `${XDG_STATE_HOME:-~/.local/state}/skills/coordinate/<run>/run.md`, outside the repository. It holds the plan and one row per task: id, files it may touch, what it depends on, owner thread, branch, PR, last reported head, verdict and the head it covers, and a stuck-after time. Whoever launches a thread records it there before doing anything else. After a compaction, or when another thread takes over the run, read this file before acting.

## Steps

1. **Plan.** Write the tasks into the run file before launching any. For each task, list the files it may touch, the one change it builds, how it will be verified, and the tasks it waits for. Merge tasks whose files overlap into one task, because two owners never share a file. A task whose files no running task touches is independent.

2. **Launch owners in parallel off trunk, never stacked,** so each PR merges on its own. Stack a PR only when it builds on another PR: base it on that PR's branch, and it rebases onto its parent's branch while the stack root rebases onto trunk. Start each owner with `t3_thread_launch`: title `<run> <task>: <summary>`, a new worktree branched from `<remote>/<trunk>` (or the parent's branch) with `startFromOrigin` true, a Conventional Branch name, and the `implementer` role's provider, model, and effort as its model selection. The message is the brief:

   ```text
   You own task <run>/<task>: <summary>.
   Done when: <verification>
   Context: <pointers to the issue, spec, notes, or commits>
   Touch only these files: <files>. If the task needs another file, stop and say which.
   Open the PR early so CI runs alongside the work, with a body per the `pr` skill. Base: <trunk or parent branch>.
   Before you report code-ready, run the repository's checks for the touched paths on the committed head and rebase onto current <trunk or parent branch>.
   Push every finished unit before you start the next. Force-push only your own branch, with --force-with-lease pinned to the SHA you last pushed. On any push you did not make, stop and report.
   Report every new head SHA, then code-ready, then green once CI passes. Never merge.
   ```

3. **Verify once at the code-ready head.** Read the owner's report and diff yourself, then start one verifier with `delegate_task` on the `reviewer` role. When the reviewer default is the owner's model family and the backup is another family that can run, use the backup. The verifier gets the task, its verification, and the exact head SHA. It reruns the checks, proves the behavior on the real surface, audits the diff, and returns `pass` or `fail` with the failing run.
   - Block a PR only for a problem you can show: a failing run at the head, or a doc line the PR made wrong. A problem trunk already has blocks only when the PR copies it or newly reaches it. Everything else becomes a follow-up task.
   - On `fail`, send the findings to the owner with `t3_thread_send`, then verify its new head.
   - A verdict covers the patch, not the commits. After a rebase, run `git patch-id` on the old and new diffs. When they match, the verdict stands. A conflict resolution or a minor fix gets one verifier at the new head. A wording-only change gets none. New behavior or a large new diff gets a full verification again.
   - After 3 failed rounds on one task, stop fixing and ask the user whether to accept known limits, redesign, or drop it.

4. **Fix the recipe.** When two owners make the same kind of mistake, call the Skill tool with `correct` before launching or verifying more work.

5. **Watch the run.** Keep one hourly `schedule_task` heartbeat while any owner works, with the prompt "Continue the coordinate run `<run>`." Each wake rereads this skill and the run file and fixes drift, such as an unreported head or an unrecorded thread, by having its owner record it. Probe every owner with `t3_thread_read` and judge it by what it did, such as pushes and new heads, not by its status text. An owner is stuck when it errors, cannot start turns, or shows nothing new past its stuck-after time. Replace a stuck owner at once with the same brief, based on its last pushed head. An owner waiting on you or the user is not stuck, so answer it.

6. **Refill.** When a task is verified, or its PR merges, launch the tasks that waited for it.

7. **Stop at verified.** A task is done when its PR is verified and green at its current head. Hand the PRs to the user. After the handoff, nobody pushes without the user's go. When the user merges a PR, remove its owner's worktree. A PR stacked on it moves onto trunk only on the user's go, and keeps its verdict when `git patch-id` is unchanged.

8. **Stand down at once on the user's stop.** Send every owner a zero-writes order with `t3_thread_send`. Each reports where it stands and keeps its brief until the user releases it.

**Reply:** one table with each task, its PR, its verdict and the head it covers, and the decision it waits on, if any. Raise each decision once.

Delete only what this run created: its owner worktrees and branches. Ask before deleting any other branch.
