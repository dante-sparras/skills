---
name: pr-body
description: "PR body template: a Summary drawn as the smallest diagram that makes the point, Before and After evidence, and the Merge Danger door and blast radius. Use when opening a pull request, writing or rewriting a PR description, or updating one after the change grew."
---

Title the PR in the repo's commit convention, and as `type(scope): subject` when it has none. A squash merge makes the title the commit subject.

Write the body from this template. Start each section with its content, keep prose brief, and use the domain language from `GLOSSARY.md`.

```markdown
## Summary

<diagram, diff-sketch, or tree>

## Evidence

- **Before:** <screenshot/output/failing test run>
  **After:** <screenshot/output/passing test run>

## Merge Danger

**Door:** <one-way or two-way>

**Blast Radius:** <what the change could affect, in one line>

<details><summary>Agent notes</summary>

**Seams:** <where the tests go, when an agent chose them>
**Friction:** <what cost the agent time, or "none">

</details>

Closes #<issue>
```

Drop the `Closes` line when the PR resolves no issue, and the agent notes when a person wrote the PR.

## Summary

Pick the smallest view that makes the key point clear. One or two usually do. Keep only the calls, files, props, states, and boundaries that show what this PR changes.

| The point is | Show it as |
| --- | --- |
| Logic or an algorithm | Pseudocode |
| Runtime control flow | A call tree |
| UI structure | A component tree, with the state and module boundaries that matter |
| File responsibility, or a broad refactor | A shallow file tree with a comment per folder |
| How components interact, or how data flows | A Mermaid sequence diagram |
| What changes in a shape that already exists | A `diff` of any of the above |
| Something mostly new, or a shape to copy | The whole block |

A diff of a call tree:

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

A diff of a file tree:

```diff
 src/
 ├── commands/
+│   └── expand-skill.ts  # expands the slash command
 ├── sessions/
-└── transport.ts
+└── transport/
+    ├── client.ts
+    └── stream.ts
```

## Evidence

Show that the change works, before and after.

- **A visual change**: screenshots or a short video. Reference each file in the body by its local path, as `![the login error state](./after.png)`, and upload it with `gh pr edit <number> --body-file <body file> --attach ./before.png --attach ./after.png`. `gh` uploads each file and rewrites the reference, so nothing is hosted elsewhere or committed.
- **Anything else**: a run. Name the exact test or command and paste its real output, failing before the change and passing after.

## Merge Danger

- **Door**: two-way when the change is cheap to roll back. One-way when it involves a destructive action or a decision that is hard to reverse.
- **Blast radius**: everything the change could affect, such as layout shift, breakage for consumers, or mobile responsiveness.
