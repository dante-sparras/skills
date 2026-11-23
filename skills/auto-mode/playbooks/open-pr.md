### Open the PR

**Run when you made a small change yourself. It ends at a reviewed PR with green CI.**

1. **Prove.** Run the repo's full checks. Then prove the behavior on the surface where a user meets it, with the repo's `verify-<app>` skill when it has one. Keep the output as evidence.
2. **Commit** in small steps that each pass. For a bug fix, the failing test lands before the fix.
3. **Review.** Call **code-review** with the default branch as the fixed point, the issue or the contract as the spec, and the goal from your first line as the intent.
4. **Fix** every finding the review proved, and rerun the command that proved it. For each Standards finding, fix it or say in the reply why it stays. Review again when a fix changed behavior.
5. **Open.** Push, and open the PR with a body from **pr**. Mark it as closing its issue when it has one.
6. **Wait for CI.** Done when CI is green on the head you reviewed, or you have reported the failing job and its output. The merge is the user's, unless the task said to land it.

**Reply:** what changed, the evidence, each review finding with what happened to it, the PR link, and the CI state.
