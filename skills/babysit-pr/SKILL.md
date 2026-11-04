---
name: babysit-pr
description: "Own a pull request in T3 Code until it merges: auto-merge, CI and review fixes, merge-queue re-queues. Use after opening a PR, or when the user asks to babysit, watch, or merge one."
---

# Babysit PR

The thread that opened a PR **owns** it until it merges: it turns on auto-merge, keeps checks green, answers reviews, and re-queues the PR when the merge queue drops it. A PR the user handed you to watch gets the same care, but you merge it only when they asked.

This skill runs on T3 Code's PR tools (`watch_pull_request`, `link_pull_request`, `write_pull_request_guides`, …; they may be deferred, so load them with tool search). Without them, tell the user this skill needs T3 Code and stop.

A delegated child never owns a PR: it reports the PR to its parent, which runs this skill.

## Fixes

Every step below sends fixes the same way. Fix the cause in the code; never weaken, skip, or delete a test to get it green. When children wrote the code, send the fix to the child that wrote it; otherwise make it yourself. Push, and reply on the PR when a comment asked for the change.

## Steps

Link each PR with `link_pull_request` (`link_pull_requests` for several) as your next call after opening it. Watch each PR with one watcher at a time; every watcher on the account shares one GitHub rate limit.

1. Call `write_pull_request_guides` for every PR. The guide is an independent review pass; if the call fails because guides are off, skip the pass and say so in your report.
2. Handle what is already there as in step 3; a PR with no checks can be ready at once. While it isn't merged, call `watch_pull_request` and end your turn. T3 wakes you on failed checks, passed required checks, new comments or reviews, and conflicts; the watch stays on, so call it once.
3. On each wake, read the PR's state yourself (`gh pr view --json state,mergeStateStatus,statusCheckRollup`) and the guide with `read_pull_request_guide` until its run has finished:
   - A failed check: find the root cause and fix it.
   - A review comment or guide finding: decide it, fix what holds up, and reply with a reason to what doesn't.
   - A conflict, or BEHIND when the base requires an up-to-date branch: merge the default branch into the PR branch.
   - Guide finished and handled (or skipped): turn on auto-merge (`gh pr merge --auto`), then go to step 4. When GitHub refuses because the PR is already clean, merge it now instead.
4. The watch doesn't wake on a merge-queue drop, so switch watchers: call `unwatch_pull_request`, run `python <this skill's folder>/scripts/pr-wait <PR URL> --until merged` with `run_in_background`, pass its task ID to `t3_background_wait`, and end your turn.
5. `pr-wait` exits 0 when the PR merges. It exits 1 on the first thing that needs you, named in its last line: a failed check, a conflict or BEHIND branch, a new comment or review, or a drop from the merge queue or auto-merge. Handle it as in step 3; for a drop, fix why and re-queue with `gh pr merge --auto`. Then start `pr-wait` again; it remembers what it already reported. Exit 2 means another `pr-wait` already watches the PR: leave that one running.
6. When T3 reports "Stopped watching, could not read it", the rate limit is usually spent: check `gh api rate_limit --jq .resources.graphql` and wait for its `reset` before watching again.

When a wake needs no action, end your turn without a message.

**Done when** `gh pr view` reports `MERGED`.

## pr-wait

[scripts/pr-wait](scripts/pr-wait) is Theo Browne's watcher from [t3dotgg/tstack](https://github.com/t3dotgg/tstack/blob/6efae36/skills/babysit-pr/scripts/pr-wait) (MIT, [license](scripts/pr-wait.LICENSE)), adapted here: a Windows lock, merge-queue and auto-merge drop events, and `--until merged`. Its docstring lists every event and exit code.
