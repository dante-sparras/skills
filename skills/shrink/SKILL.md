---
name: shrink
description: "Score what skill instructions teach across model families and propose cuts based on the results. Use when the user says shrink a skill, run the novelty method, or rescore skills after edits."
---

# Shrink skills

1. Find the repository's `scripts/novelty.py`. While it is on a separate branch, fetch that branch and extract the script with `git show <ref>:scripts/novelty.py` into a temporary file. Pass the path with `--scorer`. Use the same scorer revision on every worker.
2. Resolve the seats and dispatch one T3 child per skill using [the coordinator procedure](COORDINATOR.md). Run children in parallel across the laptop and desktop. Keep each skill on its assigned machine on later runs to reuse its cache.
3. Collect each child's JSON summary and artifact path. The run is complete when every selected skill returns a successful summary with both grades for both arms of every claim. Retry failed children against the same inputs and cache. Report an incomplete run if a subscription is unavailable and eligible retries are exhausted.
4. Report the four bucket counts at both grading levels, elapsed time, failed call count, and how many claims were reused. If the user requests rewrites, pass `--rewrite` and review the proposed files against the scored revision before applying them.
