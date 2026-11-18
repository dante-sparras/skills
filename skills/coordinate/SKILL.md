---
name: coordinate
description: "Run many T3 worker threads on one repository at once: group tasks, claim leases with land, launch implementer threads, review each result on its exact SHA, and submit passed work to the land queue. Use for 'coordinate', 'run these tasks in parallel threads', 'fan this out to workers', or when implement-spec's tickets run on a repository with a landing contract."
---

# Coordinate

This thread is the coordinator of one **run**: a set of tasks on one repository. It groups the tasks, claims leases, launches one worker thread per task, reviews every result, and submits passed work to the queue. It never writes code. Code changes and conflict fixes are worker tasks.

| Term | Meaning |
| --- | --- |
| Run | One coordinator's set of tasks. Its name is a short slug, and it is the holder prefix `<run>/`. |
| Task | One unit of work for one worker, with the paths it will change. Its holder is `<run>/<task>`. |
| Playbook | The skill a worker follows for its task: `tdd`, `diagnosing-bugs`, `implement`, or another listed skill. |

For a spec with tickets, start from [implement-spec](../implement-spec/SKILL.md). Its coordinator runs this skill with the frontier tickets as tasks.

Every change lands through the [land skill](../land/SKILL.md). Read it before step 1. Several coordinators can share one repository, because the queue and its leases keep them apart. `L` below is `python3 <skills>/land/scripts/land.py --repo <checkout>`.

## The run file

Keep `${XDG_STATE_HOME:-~/.local/state}/skills/coordinate/<run>/tasks.md`, outside the repository. It holds one table row per task: id, summary, paths, playbook, lease, worker thread, branch, reviewed SHA, review rounds, entry, and state. Update the row after every step below. After a compaction, or when another thread takes over the run, read this file and `$L status --holder <run>/` before acting.

## Steps

1. **Set up.** Run `$L status`. With no contract, ask the user for the landing mode (default `human`) and the repository's check commands, then run `$L init`. Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role). Workers use the `implementer` role and reviewers the `reviewer` role, each default first and backup once on failure. When the user asks for the coordinator in its own thread, launch that thread with the `coordinator` role's model.

2. **Group.** Read every task together before launching any. Merge tasks that will change the same paths into one task, and keep unrelated tasks apart. Give each task a done criterion a reviewer can check, a playbook, and the paths it will change.

3. **Claim.** Run `$L lease claim --holder <run>/<task> --paths <paths>`. On an overlap, fold the task into the task that holds the paths, or hold it until that lease is released. On a cap refusal, hold it until a lease is released.

4. **Launch.** Start each claimed task with `t3_thread_launch`. Use the title `<run> <task>: <summary>`, a new worktree branched from `<remote>/<trunk>` with `startFromOrigin` true, a branch named `<type>/<run>-<task>`, and the `implementer` role's provider, model, and effort as its model selection. The message is the brief:

   ```text
   Task <run>/<task>: <summary>
   Done when: <criterion>
   Context: <pointers to the issue, spec, notes, or commits>
   Playbook: call the Skill tool with `<playbook>`.
   Change only these leased paths: <paths>. If the task needs another path, stop and say which.
   Work only in this worktree. Keep history linear with no merge commits.
   Run builds and tests through `python3 <skills>/land/scripts/land.py slot -- <cmd>`, and benchmarks through `slot --exclusive --`.
   Writers never integrate. A worker commits in its own worktree and stops. It never merges, rebases a shared branch, or pushes trunk.
   When done, reply with the branch, the head SHA, what changed, and how you verified it.
   ```

   Record the thread id and branch in the run file. End the turn while workers run.

5. **Watch.** Keep one `schedule_task` heartbeat, `{"type": "interval", "everyMs": 900000}`, while any worker runs, with the prompt "Continue the coordinate run `<run>`." On each wake, `t3_thread_read` every running worker. A worker idle for more than 10 minutes with no report gets one nudge with `t3_thread_send`. A worker idle again after its nudge is replaced: launch a fresh worker with the same brief, based on the old branch head. Run `$L lease renew L<n> --if-live` on any task that will outlast its lease.

6. **Review.** When a worker reports done, read its report and its diff against trunk yourself. A done report is a claim. Then start one reviewer with `delegate_task`, using the `reviewer` role. When the reviewer default is the worker's model family and the backup is another family that can run, use the backup. The reviewer gets the task, the done criterion, the leased paths, and the exact head SHA, and returns `pass` or `send-back` with findings. A verdict holds only for that SHA.
   - `send-back`: send the findings to the worker with `t3_thread_send`, then review its new head SHA. After 3 send-backs on one task, stop fixing and ask the user whether to accept known limits, redesign, or drop the task.
   - When two workers' reviews find the same kind of mistake, call the Skill tool with `correct` before launching or sending more work.

7. **Submit.** For a `pass`, write a PR body (what changed, how it was verified, and `Closes #<n>` for each issue) to the run directory. Then run `$L submit --holder <run>/<task> --branch <branch> --sha <reviewed sha> --lease L<n> --reviewer <provider>/<model> --title "<conventional commit title>" --body-file <file>`, then `$L land`. Settle and keep the queue moving per the land skill.
   - `bounced`: send the reason to the worker. After its fix, review the new SHA again before resubmitting.
   - `landed`: remove the worker's worktree and branch.

8. **Refill.** After every landing, bounce, or dropped task, claim and launch the next tasks that are now free.

9. **Report.** When every task is landed, awaiting the user's merge, or blocked, reply with one table: task, PR or commit, state, and the decision it waits on, if any. Raise each decision once.

Delete only what this run created: its worker worktrees and branches, and the queue's `landing/e<n>` branches. Ask before deleting any other branch.
