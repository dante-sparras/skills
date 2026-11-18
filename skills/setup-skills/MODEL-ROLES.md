# Model roles

## Configure model roles

1. Discover and call T3's `orchestrator_capabilities`. Outside T3, skip model setup and tell the user that children inherit their thread's model.
2. Use `~/.config/skills/roles.json` by default. In a repository, offer `.skills/roles.json` at its root for a project override. Show any active project overrides. For a user write, start from the user file. For a project write, start from the effective roles after applying overrides.
3. Propose all four default and backup pairs. For unset roles, match the models and high effort options below to the live catalog. Prefer native providers. Flag unavailable targets and offer runnable replacements. Ask the user to confirm or edit all four pairs, including effort.
4. Validate the confirmed targets using the catalog checks below. Write all four pairs to the chosen file. Reread the JSON and report the saved path and choices.

| Role | Default | Backup |
| --- | --- | --- |
| `coordinator` | Claude Opus 5.5, high | Grok 4.7, high |
| `implementer` | Claude Opus 5.5, high | Grok 4.7, high |
| `reviewer` | Claude Opus 5.5, high | Grok 4.7, high |
| `explorer` | Grok 4.7, high | Claude Haiku 5.5, high |

Both files use a `roles` object keyed by role name. Each role holds a default and backup with `providerInstanceId`, `model`, and `effort`. Store the catalog's exact provider and model IDs and the chosen effort value.

```json
{
  "roles": {
    "reviewer": {
      "default": {
        "providerInstanceId": "claudeAgent",
        "model": "claude-opus-5-5",
        "effort": "high"
      },
      "backup": {
        "providerInstanceId": "grok",
        "model": "grok-4.7",
        "effort": "high"
      }
    }
  }
}
```

## Resolve a role

1. Outside T3, use native subagents with the current model. In T3, read `~/.config/skills/roles.json` and overlay roles from `<repo-root>/.skills/roles.json`. A project entry replaces the whole pair for that role. If the role is absent from both files, omit `target` so the child inherits. Report malformed config with its path.
2. Use the live `orchestrator_capabilities` catalog before the first delegation. Check `canRunChildTask` and, for a different provider, `canRunCrossProviderChildTask`. Use catalog search if the target model is missing from the short list and the provider lists omitted models.
3. Find the model's reasoning option in the catalog and check that it accepts the saved `effort` value. Build `delegate_task.target` with `providerInstanceId`, `model`, and `options` using that option ID. For example, `"effort": "high"` becomes `options: { effort: "high" }` for native Claude and `options: { reasoningEffort: "high" }` for native Grok.
4. Launch the `default`. If its target is unavailable, T3 rejects it, or the child hits a usage limit before returning the required result, resolve and launch the `backup` once. Refresh the catalog after a failed launch. Report the switch and why. If both fail, report both and leave that delegation blocked. Before retrying a write, check what the first child already changed.
