# Run the novelty method in T3

## Prepare the run

- Record the repository, input revision, selected skills, and start time.
- Call `orchestrator_capabilities` for the local session. Use any saved [setup-skills roles](../setup-skills/MODEL-ROLES.md#resolve-a-role) as suggestions.
- Before launching workers, ask the user to choose or confirm a model and effort for each role. Present the available choices together and show the suggested configuration if one exists.
  - `coordinator` runs each skill's T3 child.
  - `explorer` supplies at least two answerers from distinct model families. The first answerer also drafts the claims.
  - `reviewer` grades each answer. Pick a judge from a different family for each answerer.
  - `implementer` rewrites the skill. Skip this role for a scoring-only run.
- Validate the chosen models and effort values against the local catalog. Ask again if any choice is unavailable or a judge shares the answerer's model family. Preserve the confirmed choices for retries.
- Use native Claude Max, Grok, or ChatGPT subscription seats. Check that paid overages are disabled or absent before launching. Stop the affected lane if included usage runs out. The worker strips API keys and checks the logins for the selected CLIs. Codex needs a file-backed ChatGPT login so the worker can isolate authentication from personal instructions.
- Save the confirmed worker seats in JSON. Each variable below stands for an object with `driverKind`, `providerInstanceId`, `model`, and `effort`. The driver kinds are `claudeAgent`, `grok`, and `codex`.

  ```python
  {
      "answerers": [claude, grok],
      "judges": {"claude": grok, "grok": claude},
      "implementer": implementer,
  }
  ```

## Dispatch and collect

1. Keep a ledger with each skill, input revision, seat file, state directory, and child task ID. Start with the largest skills. Choose a stable local state directory outside the checkout. Reuse the confirmed seat order on reruns when the user's choices stay the same.
2. Launch one async `delegate_task` per skill using the confirmed coordinator seat on the current computer. Use a stable request ID per skill and attempt. Start with two active skills and four concurrent answer-and-judge jobs per skill. Fill each vacancy while the queue has work. Lower concurrency on timeouts or throttling before retrying.
3. In each brief, give the worker the exact paths to the input tree, adapter, and state directory, plus the resolved seats. Ask for the final JSON summary and any verified patch file.

   ```sh
   python skills/shrink/scripts/run.py --root <input-tree> --skill <name> --seats <seats.json> --state <state-dir> --concurrency 4
   ```

4. Follow the T3 continuation for each task. If a task fails or times out, cancel it if it is still running and start a fresh local child with the same cache. Keep successful work and retry missing results. Use three child attempts for transient failures and report any scores still missing.
5. Collect the summaries. Verify that each skill's bucket counts sum to its claim count at both grading levels. A shorter candidate carries a local `patch` path only when it passes the worker's checks.
6. Review each patch for intact headings, links, and instructions the claims did not cover. Apply passing patches in the user's checkout with `git apply --check -p2 <patch>` followed by `git apply -p2 <patch>`. If the input changed, rescore from the current version. Run the repo's punctuation and Use when checks on the edited tree.

## Cache and rewrites

The adapter uses the scorer's `draft`, `score`, and `apply` commands and keeps its claims, answers, grades, and decisions as JSONL. It round-robins claims across answerers and uses the same answerer and judge for both arms of each claim. The judge sees the reply and grading rubric.

Each call has three attempts. If an arm still has no successful grade, the adapter retries both arms with the next configured answerer and that seat's cross-family judge. It saves successful answers and grades as it goes. A run with any missing grade exits unsuccessfully and prints the artifact path for diagnosis.

Without-skill answers are keyed by question and answerer seat. The adapter drafts only new or changed paragraphs on reruns. It keeps the claims from unchanged paragraphs and reuses the same question when a revised draft identifies the same source span. It shows the whole skill when answering with the skill. If an edit changes how another paragraph should be interpreted, use a fresh state directory for a full with-skill evaluation. The scorer revision and answerer panel determine the cache namespace.

The worker runs `apply` on a scratch copy with the configured implementer seat. It accepts candidates only when they are shorter and the original taught claims still pass on the scales where they taught. This check uses the rewritten skill and the original questions, including for instructions that moved or disappeared. It reuses validation results for identical candidates. Use `--score-only` when the user asks only for scores.
