# The factory

The **factory** is a T3 Code workflow, [factory.ts](factory.ts), that runs the coordinator's loop with no coordinator agent and no person to start it. Every ten minutes it looks for open issues labelled `ready-for-agent` and starts a run for each one it can. Each run is the same path a coordinator gives a task:

1. **A worker** sizes the issue and takes its path, briefed with `rules.md` and `worker.md`.
2. **Checks.** The run waits for the PR's checks. A red check or a conflict wakes the worker on its own thread.
3. **A reviewer** reviews the head, briefed with `rules.md` and `reviewer.md`, and argues each finding with the worker as it does under `/coordinate`.
4. **A person's go.** Every merge waits on your answer: merge, merge it yourself, or stop. A `NO AGREEMENT` verdict waits on your ruling.
5. **The merge** goes through `gh pr merge --match-head-commit`, so GitHub refuses it if the head moved after the review. A moved head goes back through checks and review.

Workers and reviewers return their results as data, which T3 checks against a schema, so a result with a field missing is sent back to the agent to fix. A run survives a restart of T3 Code. It picks up at the step it was on.

## What it needs

- T3 Code with **Settings → Labs → Workflows** on. `t3 workflow list` exits 0 when it is.
- A GitHub repo set up by `setup-skills`, with `gh` signed in. The factory reads blockers and merges through `gh`.
- The skills installed side by side, as for `/coordinate`.

## Install

`setup-skills` does this, under [Install the factory](../setup-skills/SKILL.md#6-install-the-factory).

1. **Copy** `factory.ts` to `skills-factory.ts` in the `workflows` folder of T3 home: `~/.t3/workflows/` by default. T3 reloads the folder on its own. Copy it again after the skills update, since T3 does not see changes to the original.
2. **Register the repo** in the workflow store, under `skills-factory/projects/<owner>/<repo>`:

   ```sh
   t3 workflow store set skills-factory/projects/<owner>/<repo> '<settings as JSON>'
   ```

   | Field | Value |
   | --- | --- |
   | `project` | The repo's folder, as an absolute path, or its T3 project id |
   | `repository` | `<owner>/<repo>` |
   | `skillsFolder` | The absolute path of the folder that holds the `coordinate` folder |
   | `defaultBranch` | The name after `origin/` in `git symbolic-ref --short refs/remotes/origin/HEAD` |
   | `readyLabel` | The `ready-for-agent` label in `docs/agents/triage-labels.md` |
   | `needsTriageLabel` | The `needs-triage` label there, for the follow-ups it files |
   | `verifySkill` | The verify skill's path from the repo root, or `null` |
   | `maxActive` | How many runs may hold a worker at once. `4` matches `/coordinate` |
   | `mergeMethod` | `squash`, `merge`, or `rebase`, by the repo's settings |
   | `enabled` | `true`. Set `false` to pause the repo |
   | `worker`, `reviewer` | Optional. A model role as `{"default": <model>, "backup": <model>}`, each `<model>` being `{"instanceId", "model", "options": [{"id", "value"}]}` from `orchestrator_capabilities`. Leave a role out to use the project's default model |

3. **Check** that the dispatcher runs: `t3 workflow start skills-factory-dispatch --input '{"scheduledAt":"<now, as ISO 8601>"}' --key check/<now>`, then `t3 workflow show <run>`. With no ready issue it ends as `skipped`.

## Run it

- **Hand it work** by labelling an issue `ready-for-agent`. An issue waits while any of its blockers is open: GitHub's own dependencies, or a `Blocked by` line or section in its body.
- **Answer it** in T3 Code's Workflows page, or with `t3 workflow questions` and `t3 workflow signal`. A worker that asks you something does it in its own thread, as under `/coordinate`.
- **Retry** an issue by adding `ready-for-agent` back. Every run ends by removing the label, whether it merged, stopped, or was cancelled, and a stopped run says why in a comment on the issue.
- **Stop** one run with `t3 workflow cancel <run>`. **Pause** a repo by setting `enabled` to `false` in its settings.
- **Follow-ups** become issues in `needs-triage`. **Friction** lines stay in the store, under `skills-factory/friction/<owner>/<repo>/`.

## What stays with `/coordinate`

The factory takes issues one at a time from the tracker. Use `/coordinate` for work you hand over in conversation, for a spec check once a spec's tickets land, and for spotting the same friction across runs.
