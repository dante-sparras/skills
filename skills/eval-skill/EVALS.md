# Compare the original and the candidate on tasks

Claims test single instructions. Task evals test whether the shorter skill still does whole jobs. The script runs them in the same isolated CLIs as the claims, so neither version can pick up an installed skill.

1. Use the skill's existing task evals in `.skills/evals/<skill>.json` when available. Add a representative case for any changed behavior they miss. If the skill has none, define tasks and checks before running either version. Cover the changed facts, actions, and ordering requirements.
2. Write the tasks to `.skills/evals/<skill>.json` as a list of objects with `id`, `prompt`, and `checks`. A prompt is a user request. Each check is one observable thing the reply commits to, such as an action, its order, a name, or a value.

   ```json
   [
     {
       "id": "webhooks",
       "prompt": "Find out how Stripe retries failed webhook deliveries and leave me notes in the repo.",
       "checks": ["Uses Stripe's official documentation as the source", "Says where the notes file was saved"]
     }
   ]
   ```

3. The script loads that file on its own, and `--tasks <dir>` points at another folder. It refuses a malformed file before the run starts. For each proposal, the script runs every task on every answerer with the original and with the candidate, and that answerer's judge grades each check, falling back to a seat from another family when the judge fails. It caches each pair, so a rerun with new tasks asks only the new ones.
4. The proposal is rejected when any check the original passed fails with the candidate. If a result looks flaky, rerun with a fresh `--state` before drawing a conclusion. If you cannot write a representative task, leave the candidate unapplied and report the missing evidence.
