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
| `explorer` | Grok 4.7, high | Claude Opus 5.5, high |

Both files use a `roles` object keyed by role name. Each role holds two T3 targets. This example shows one role. Use the catalog's exact provider instance, model, option IDs, and values.

```json
{
  "roles": {
    "reviewer": {
      "default": {
        "providerInstanceId": "claudeAgent",
        "model": "claude-opus-5-5",
        "options": { "effort": "high" }
      },
      "backup": {
        "providerInstanceId": "grok",
        "model": "grok-4.7",
        "options": { "reasoningEffort": "high" }
      }
    }
  }
}
```

## Resolve a role

1. Outside T3, use native subagents with the current model. In T3, read `~/.config/skills/roles.json` and overlay roles from `<repo-root>/.skills/roles.json`. A project entry replaces the whole pair for that role. If the role is absent from both files, omit `target` so the child inherits. Report malformed config with its path.
2. Use the live `orchestrator_capabilities` catalog before the first delegation. Check `canRunChildTask`, `canRunCrossProviderChildTask` for a different provider, and the model's option IDs and values. Use catalog search if the provider lists omitted models and the target model is missing from the short list.
3. Pass the role's `default` as `delegate_task.target`. If the target is unavailable, T3 rejects it, or the child hits a usage limit before returning the required result, use `backup` once. Refresh the catalog after a failed launch. Report the switch and why. If both fail, report both and leave that delegation blocked. Before retrying a write, check what the first child already changed.

The role setup follows Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), distributed under the [MIT License](../../LICENSES/pstack.md).
