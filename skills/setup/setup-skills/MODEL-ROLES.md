# Model roles

## Configure model roles

1. Call T3's `orchestrator_capabilities` for the live catalog.
2. Use `~/.config/skills/roles.json` by default. In a repository, offer `.skills/roles.json` at its root for a project override. Show any active project overrides. For a user write, start from the user file. For a project write, start from the effective roles after applying overrides.
3. Propose all three default and backup pairs. For unset roles, pick models from the live catalog by the table below, each at high effort. Prefer native providers. Flag unavailable targets and offer runnable replacements. Ask the user to confirm or edit all three pairs, including effort.
4. Validate the confirmed targets using the catalog checks below. Write all three pairs to the chosen file. Reread the JSON and report the saved path and choices.

The coordinator is the thread the user talks to, so it runs on that thread's model and has no role here. An `auto-mode` worker runs on `implementer`, and a verifier on `reviewer`.

| Role | Default | Backup |
| --- | --- | --- |
| `implementer` | The strongest coding model in the catalog | The strongest coding model from another model family |
| `reviewer` | The same model as `implementer` | Another model family, so `code-review` gets two |
| `explorer` | A fast, low-cost model | A fast model from another model family |

Both files use a `roles` object keyed by role name. Each role holds a default and backup with `providerInstanceId`, `model`, and `effort`. Store the catalog's exact provider and model IDs and the chosen effort value.

```json
{
  "roles": {
    "reviewer": {
      "default": {
        "providerInstanceId": "<provider id from the catalog>",
        "model": "<model id from the catalog>",
        "effort": "high"
      },
      "backup": {
        "providerInstanceId": "<another provider id>",
        "model": "<a model id from another family>",
        "effort": "high"
      }
    }
  }
}
```

## Resolve a role

1. Read `~/.config/skills/roles.json` and overlay roles from `<repo-root>/.skills/roles.json`. A project entry replaces the whole pair for that role. If the role is absent from both files, omit `target` so the child inherits. Report malformed config with its path.
2. Use the live `orchestrator_capabilities` catalog before the first delegation. Check `canRunChildTask` and, for a different provider, `canRunCrossProviderChildTask`. Use catalog search if the target model is missing from the short list and the provider lists omitted models.
3. Find the model's reasoning option in the catalog and check that it accepts the saved `effort` value. Build `delegate_task.target` with `providerInstanceId`, `model`, and `options` using that option ID. The option ID differs by provider: `"effort": "high"` becomes `options: { effort: "high" }` under one and `options: { reasoningEffort: "high" }` under another.
4. Launch the `default`. If its target is unavailable, T3 rejects it, or the child hits a usage limit before returning the required result, resolve and launch the `backup` once. Refresh the catalog after a failed launch. Report the switch and why. If both fail, report both and leave that delegation blocked. Before retrying a write, check what the first child already changed.
