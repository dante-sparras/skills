# Run the novelty method in T3

## Prepare the run

- Record the repository, input revision, selected skills, and start time.
- Call `orchestrator_capabilities` for the local session. Use any saved [setup-skills roles](../setup-skills/MODEL-ROLES.md#resolve-a-role) as suggestions.
- Before launching workers, ask the user to choose or confirm a model and effort for each role. Present the available choices together and show the suggested configuration if one exists.
  - `coordinator` runs each skill's T3 child and dispatches its model requests.
  - `explorer` supplies at least two answerers from distinct model families. The first answerer also drafts the claims.
  - `reviewer` grades each answer. Pick a judge from a different family for each answerer.
  - `implementer` rewrites the skill. Skip this role for a scoring-only run.
- Validate the chosen models and effort values against the local catalog. Ask again if any choice is unavailable or a judge shares the answerer's model family. Preserve the confirmed choices for retries.
- Use T3 providers configured for Claude Max, Grok, or ChatGPT subscriptions. Check that paid overages are disabled or absent before launching. Stop the affected lane if included usage runs out. Keep each model request on its confirmed provider and effort.
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
2. Launch one async `delegate_task` per skill using the confirmed coordinator seat on the current computer. Use a stable request ID per skill and attempt. Start with a budget of eight outstanding model requests. With two active skills, give each four slots using `--concurrency`. Each worker uses the same slots for both arms and their judges. Keep the sum of active worker slots within the budget. Lower the budget on timeouts or throttling before retrying.
3. In each brief, give the worker the input tree, script path, state directory, and confirmed seats. Tell it to [dispatch the script's model requests](T3-REQUESTS.md) and return the final JSON summary and any candidate patch.

   ```sh
   python skills/shrink/scripts/run.py run --root <input-tree> --skill <name> --seats <seats.json> --state <state-dir> --queue <fresh-dir> --concurrency 4
   ```

4. Follow the T3 continuation for each task. If a task fails or times out, cancel it if it is still running and start a fresh local child with the same cache. Keep successful work and retry missing results. Use three child attempts for transient failures and report any scores still missing.
5. Collect the summaries. Check that the four buckets sum to the claim count at both grading levels. Report counts by answerer because each claim runs on one assigned model. Keep model comparisons to cases where the models received the same claims.
6. Review each patch for intact headings, links, and instructions the claims did not cover. Run [task evals](EVALS.md) before applying it. Apply passing patches in the user's checkout with `git apply --check -p2 <patch>` followed by `git apply -p2 <patch>`. If the input changed, rescore from the current version. Run the repo's punctuation and Use when checks on the edited tree.

## Cache and rewrites

T3 runs the skill workers, every model request, and agent task evals. For claim probes, start a fresh delegate for each response. Keep the task, answerer, effort, and harness fixed across arms. The with-skill arm receives the skill text. The without-skill arm receives the task alone. Keep the expected answer out of both prompts and the arm label out of judging. The grade measures behavior under the selected T3 harness.

Draft up to 30 claims covering facts and instructions. Use concrete user tasks for action claims. Lenient grading checks the general idea. Strict grading checks exact names, values, and order. At each level, a claim is already known if both arms pass, hurts if only the without-skill arm passes, teaches if only the with-skill arm passes, and fails both if neither passes. Keep steering instructions that score as already known. Their value can be making the action repeatable on real tasks.

Each call has three attempts. If an arm still has no successful grade, the adapter retries both arms with the next configured answerer and that seat's cross-family judge. It saves successful answers and grades as it goes. A run with any missing grade exits unsuccessfully and prints the artifact path for diagnosis.

Without-skill answers are keyed by question and answerer seat. The adapter drafts only new or changed paragraphs on reruns. It keeps the claims from unchanged paragraphs and reuses the same question when a revised draft identifies the same source span. It shows the whole skill when answering with the skill. If an edit changes how another paragraph should be interpreted, use a fresh state directory for a full with-skill evaluation. The scorer revision and answerer panel determine the cache namespace.

The worker uses the configured implementer seat to rewrite a scratch copy. It emits a candidate patch only if the copy is shorter and the original taught claims still pass on the scales where they taught. This check uses the rewritten skill and the original questions, including for instructions that moved or disappeared. It reuses claim validation results for identical candidates. Use `--score-only` when the user asks only for scores.
