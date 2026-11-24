---
name: to-pr
description: "PR title and body template. Use when opening a pull request, writing or rewriting a PR description, or updating one after the change grew."
disable-model-invocation: true
---

# To PR

Title the PR in the repo's commit convention, and as `type(scope): subject` when it has none. A squash merge makes the title the commit subject.

Write the body from this template:

```markdown
## Summary

<diagram, diff-sketch, or tree>

## Evidence

- **Before:** <screenshot/output/failing test run>
  **After:** <screenshot/output/passing test run>

## Merge Danger

**Door:** <one-way or two-way>

<optional: description>

**Blast Radius:** <what the change could affect, in one line>

<optional: potential ramifications of merge>

<details><summary>Agent notes</summary>

**Seams:** <where the tests go, when an agent chose them>
**Friction:** <what cost the agent time, or "none">

</details>

Closes #<issue>
```

Keep the `Closes` line for each issue the PR resolves, and drop it when there is none. Keep the agent notes when an agent wrote the PR, and drop them otherwise.

Keep the body to 40 lines, not counting the agent notes. Start each section with its content, keep prose brief, and use the domain language from `GLOSSARY.md`.

## Summary

Pick the smallest view that makes the key point clear. One or two usually do. Place each next to the short text it supports, and keep only the calls, files, props, states, and boundaries that show what this PR changes.

| The point is | Draw |
| --- | --- |
| Logic or an algorithm | Pseudocode |
| Runtime control flow | A call tree |
| UI structure | A component tree, with the state and module boundaries that matter |
| File responsibility, or a broad refactor | A shallow file tree |
| How components interact, or how data flows | A Mermaid diagram |
| What changes inside a shape that already exists | Any view above as a `diff` block |
| A block that is mostly new, or one where omitted context would hide ownership or order | The whole block |

A call-tree change as a `diff` block:

```diff
 submitForm
   createSession
     persistPrompt
+    expandSkillMention
     launchAgent
-  navigateToSession
+  navigateToSession
+    subscribeToEvents
```

## Evidence

Show that the change works, before and after.

- **A visual change**: screenshots or a short video, when the environment can take them. Reference each file in the body by its local path, as `![the login error state](./after.png)`, and upload it with `gh pr edit <number> --body-file <body file> --attach ./before.png --attach ./after.png`. `gh` uploads each file and rewrites the reference to point at it, so nothing is hosted elsewhere or committed. Attach as your last edit to the body: a later `pull_request_update` with a body would put the local paths back. `gh pr edit --help` lists `--attach` when your `gh` has it.
- **Anything else**: a run. Name the exact test or command and paste the lines of its real output that show the result, failing before the change and passing after.

## Merge Danger

- **Door**: two-way when the change is cheap to roll back. One-way when it involves a destructive action or a decision that is hard to reverse.
- **Blast radius**: everything the change could affect, such as layout shift, breakage for consumers, or mobile responsiveness.
