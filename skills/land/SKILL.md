---
name: land
description: "Let many agents write to one repository without collisions: path leases claimed before work starts, one queue that is the only writer to trunk, a review that holds only for the exact SHA reviewed, and a slot governor for builds and tests. Use for 'land this', 'merge queue', 'lease these paths', 'many agents on one repo', or before a coordinator delegates writing work in parallel."
---

# Land

Writing scales. Integration does not. Land makes integration a property of the repository, decided once, so no coordinator asks where work lands and no two writers collide.

The rules:

1. One trunk per repository. Every change lands there through the queue.
2. A writer claims a lease on the paths it will change before it starts. Overlapping claims are refused.
3. Writers never integrate. A worker commits in its own worktree and stops. It never merges, rebases a shared branch, or pushes trunk.
4. The queue is the only writer to trunk. It is a lock, not a process. Whoever runs `land` while the lock is free drains the queue. Everyone else gets `queue busy`.
5. A review holds only for the exact change reviewed. The queue lands the pinned SHA and bounces it when the rebased change differs from the reviewed one.
6. Builds and tests run under a governor slot, so parallel workers don't overload the machine.

## The script

`<skills>/land/scripts/land.py`, where `<skills>` is the directory holding this skill. It runs on Windows, macOS, and Linux with Python 3.9 or later. Run it from any checkout of the repository, or pass `--repo <path>`. State lives in SQLite under `${XDG_STATE_HOME:-~/.local/state}/skills/land/`, one store per repository. Every command takes `--help`.

```bash
L="python3 <skills>/land/scripts/land.py --repo <checkout>"
$L init --trunk main [--mode human|push|local] [--check "<cmd>" ...] [--setup "npm ci"] [--cap 4] [--batch 1] [--timeout 1800] [--base <commit>]
$L lease claim --holder <run>/<task> --paths src/engine,package.json   # prints L<n>, or who holds the overlap
$L lease check --holder <run>/<task> --paths src/engine   # what a claim would answer now, claiming nothing
$L lease renew L3 [--if-live] ; $L lease widen L3 --paths docs ; $L lease release L3 ; $L lease list
$L submit --holder <run>/<task> --branch <b> --sha <reviewed sha> --lease L3 --reviewer <provider>/<model> [--title "..." --body-file pr.md]   # prints E<n>
$L land                      # drain the queue: prints what landed, bounced, opened, or still waits
$L status [E3] ; $L status --holder <run>/ [--sha <sha>] [--json] ; $L resume ; $L cap 4
$L slot -- npm test          # a heavy command under a worker slot
$L slot --slots 2 -- npm test   # a command that runs several heavy processes
$L slot --exclusive -- npm run bench   # hold every slot while it measures
```

A holder is `<run>/<task>`. A holder ending in `/` in `status --holder` matches every task of that run.

## Set up a repository once

Run `init` the first time any coordinator writes to a repository. The mode decides whether the user stays the gate on trunk, so it is the user's call. Ask once per repository unless the user already said. Default to `human`.

| Mode | The queue does | The user |
| --- | --- | --- |
| `human` | Rebases the entry onto trunk, runs the checks, pushes `landing/e<n>`, and opens a PR. | Merges every PR. |
| `push` | Rebases, runs the checks, and pushes trunk only if the remote still points at the tested base. No PRs. | Reviews after the fact, in the history. |
| `local` | Lands on `refs/landing/<trunk>`, which no checkout uses. No remote. | Merges that ref into a branch when ready. |

Checks are the repository's own test, type check, and lint commands. In `push` and `local` mode they are the only gate, and `init` and `status` warn while there are none. `--setup` installs dependencies, because the queue's worktree is cleaned with `git clean -ffdx` before every attempt. A rerun of `init` keeps every stored value whose flag is omitted. It refuses to change trunk, remote, or mode while anything is queued, landing, or awaiting merge.

`human` mode needs an authenticated `gh`. The cap bounds changes in flight on the repository: every submitted lease and every active lease that has not expired, whoever holds it.

## Run writers through it

For every unit of writing work:

1. **Claim.** Run `lease claim` on the files and directories the unit will change, before delegating. When the claim is refused, fold the unit into the holder's work or hold it until that lease is released. A cap refusal names every holder in flight. Claim `.` only when the unit really touches everything. A lease lasts 6 hours. `lease renew` extends a live lease. Renewing an expired lease is a new claim on its paths and is refused when another lease now overlaps. `--if-live` refuses an expired lease instead.
2. **Brief.** Tell the worker to work only in its own worktree branched from `<remote>/<trunk>` (`refs/landing/<trunk>` in local mode), change only the leased paths, keep history linear with no merge commits, run builds and tests through `land.py slot --` and every benchmark or timing through `land.py slot --exclusive --`, commit, and report the branch and head SHA. Paste rule 3 into the brief word for word.
3. **Review** the exact head SHA with a reviewer from another model family when one can run.
4. **Submit** that SHA with the lease and the reviewer. In `human` mode, pass `--title` and `--body-file` so the PR says what changed and how it was verified. Without them the PR takes the reviewed commit's subject and body. A submit that changes paths outside the lease is refused. Widen the lease or split the change.
5. **Land.** Run `land`. When it prints `queue busy`, run it again, at most 3 more times, 5 seconds apart.
6. **Settle.** Read `status E<n>`.
   - `landed`: the lease is released. Remove the worker's worktree with `git worktree remove` and delete its branch.
   - `bounced`: the lease is active again for the fix. Send the bounce reason to a worker with the original brief. A conflict, or `the rebased change differs from the reviewed one`, needs a new review after the fix. Resubmitting prints a new entry id.
   - `awaiting-merge` (`human` mode): the PR is open for the user. Keep the queue moving.

## Keep the queue moving

`land` prints every holder's entries. Act only on lines whose holder is yours.

In `human` mode, once `land` opens a PR, call `watch_pull_request` on it. A merge does not wake the watch, so also keep one `schedule_task` heartbeat while any of your entries is queued or awaiting merge: `{"type": "interval", "everyMs": 900000}` with the prompt "Run `python3 <skills>/land/scripts/land.py --repo <checkout> land` and act on what it prints per the land skill." Create it only if none is running. On each wake, run `land`. It marks a merged PR `landed`, deletes `landing/e<n>`, and bounces a PR closed without merging. Delete the heartbeat with `delete_scheduled_task` and call `unwatch_pull_request` once `status --holder <run>/` shows nothing queued or awaiting merge.

The queue checked the PR's head commit. When the user merges that head, the entry lands. When the PR head changes outside the queue, `status E<n>` says so, and a merge at that head bounces the entry with `review what reached trunk`. Tell the user to merge queue PRs as they are, without updating the branch on GitHub.

When `land` prints `queue paused`, read [pauses](reference/pauses.md) before you act.

## Capacity

Read [capacity](reference/capacity.md) before you set the slot count or hold slots for a measurement.
