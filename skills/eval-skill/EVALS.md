# Compare the original and the candidate on tasks

1. Use the skill's existing task evals when available. Add a representative case for any changed behavior they miss. If the skill has no evals, define tasks and observable checks before running either version. Cover the changed facts, actions, and ordering requirements. Prefer checks on outputs, tool traces, or repository state.
2. Run each task against the original and the candidate in separate fresh sessions. Use the same model, effort, tools, inputs, and pass criteria for the pair. For tasks that need an agent to act, use local T3 delegates in isolated worktrees. Give each delegate only its assigned skill version and the task. Run deterministic checks with the repo's own harness when it exists.
3. Record which checks pass under each version and the output or trace supporting the result. Compare per task and per check. If a result is flaky, repeat both versions under the same conditions before drawing a conclusion.
4. Reject the candidate if any check the original passed regresses. If you cannot run a representative comparison, leave the candidate unapplied and report the missing evidence.
