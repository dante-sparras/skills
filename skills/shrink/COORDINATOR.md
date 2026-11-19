# Run the novelty method in T3

## Prepare the run

- Record the repository, the source revision, the selected skills, and the start time. Use the same `scripts/novelty.py` on both machines.
- Call `t3_environment_links`. Match the laptop and desktop, then find the same repository on each with `t3_project_list`. Use a revision the desktop can fetch for remote jobs. If its checkout differs, use `git archive` on the pinned revision and extract it to a scratch input directory. Keep skills with unpublished edits on the machine that has them.
- Call `orchestrator_capabilities` before delegating. Resolve the `coordinator`, `explorer`, `reviewer`, and `implementer` pairs using [setup-skills](../setup-skills/MODEL-ROLES.md#resolve-a-role). Use the coordinator's seat for the child thread. Check the catalog on the destination environment too.
- Choose three distinct answerer families from the configured pairs, starting with the explorer. For each family, choose a different judge family starting with the reviewer pair. Preserve the saved effort and model for each seat. Use setup-skills to fill in missing families and check that all selected seats can run on their assigned machines.
- Use native Claude Max, Grok, and ChatGPT subscription seats. Check that overage billing and paid credits are disabled or absent on both machines before launching. Stop the affected lane if included usage runs out. The worker strips API keys and checks subscription logins before starting model calls. Codex needs a file-backed ChatGPT login so the worker can isolate authentication from personal instructions.
- Save a seat file per worker with this shape. Each variable below stands for a resolved object with `driverKind`, `providerInstanceId`, `model`, and `effort`. The driver kinds are `claudeAgent`, `grok`, and `codex`.

  ```python
  {
      "answerers": [claude, grok, gpt],
      "judges": {"claude": grok, "grok": gpt, "gpt": claude},
      "implementer": implementer,
  }
  ```

## Dispatch and collect

1. Keep a local ledger with the skill, environment, input revision, seat file, state directory, and child task ID. On a cold run, split skills evenly by estimated size across the two machines. Start with the largest skills. On a rerun, reuse the recorded assignments and seat order. Choose a stable machine-local state directory outside the checkout for this repository.
2. Launch one async `delegate_task` per skill with `target.environmentId` and `target.projectId` for remote work. Use a stable request ID per skill and attempt. Start with two active skills per machine and four concurrent answer-and-judge jobs per skill. Fill each vacancy while the queue has work. On timeouts or throttling, lower the affected machine's concurrency before retrying.
3. In each brief, give the worker the exact paths to the input tree, adapter, and state directory, plus the resolved seats. Ask for the final JSON summary and any verified patch file.

   ```sh
   python skills/shrink/scripts/run.py --root <input-tree> --skill <name> --seats <seats.json> --state <state-dir> --concurrency 4
   ```

4. Follow the T3 continuation for each task. If a task fails or times out, cancel it if it is still running and send a fresh child to the same machine with the same cache. Keep successful work and retry missing results. Use three child attempts for transient failures and record the remaining failures if a machine or subscription stays unavailable.
5. Collect the summaries. Verify that each skill's bucket counts sum to its claim count at both grading levels. A shorter candidate carries a `patch` path only when it passes the worker's checks. Collect remote patches through T3. Keep scoring artifacts off the Git remote.
6. Review each patch for intact headings, links, and instructions the claims did not cover. Apply passing patches in the user's checkout with `git apply --check -p2 <patch>` followed by `git apply -p2 <patch>`. If the input changed, rescore from the current version. Run the repo's punctuation and Use when checks on the edited tree.

## Cache and rewrites

The adapter uses the scorer's `draft`, `score`, and `apply` commands and keeps its claims, answers, grades, and decisions as JSONL. It round-robins claims across answerers and uses the same answerer and judge for both arms of each claim. The judge sees the reply and grading rubric.

Each call has three attempts. If an arm still has no successful grade, the adapter retries both arms with the next configured answerer and that seat's cross-family judge. It saves successful answers and grades as it goes. A run with any missing grade exits unsuccessfully and prints the artifact path for diagnosis.

Without-skill answers are keyed by question and answerer seat. The adapter drafts only new or changed paragraphs on reruns. It keeps the claims from unchanged paragraphs and reuses the same question when a revised draft identifies the same source span. It shows the whole skill when answering with the skill. If an edit changes how another paragraph should be interpreted, use a fresh state directory for a full with-skill evaluation. The scorer revision and answerer panel determine the cache namespace.

The worker runs `apply` on a scratch copy with the configured implementer seat. It accepts candidates only when they are shorter and the original taught claims still pass on the scales where they taught. This check uses the rewritten skill and the original questions, including for instructions that moved or disappeared. It reuses validation results for identical candidates. Use `--score-only` when the user asks only for scores.
