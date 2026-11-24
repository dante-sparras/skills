# The out-of-scope knowledge base

The `.out-of-scope/` directory in a repo records rejected enhancement requests: why each was rejected, and every issue that asked for it. A new request that matches an old rejection then meets the earlier decision, with no need to argue it again.

## Read it

During triage's **Gather** step, read every file. Match by concept, not by keyword: "night theme" matches `dark-mode.md`. On a match, tell the maintainer: "This is similar to `.out-of-scope/dark-mode.md`. We rejected it before because <reason>. Do you still feel the same way?"

| The maintainer | Do |
| --- | --- |
| Confirms | Add the issue to the file's Prior requests, then close it |
| Reconsiders | Delete or update the file, and triage the issue as usual. Old issues stay closed |
| Says the requests differ | Triage the issue as usual |

## Write to it

Write here only when an **enhancement** is rejected as `wontfix`, whether it arrived as an issue or as a PR. A request closed because it is already built stays out: recording it would make later checks report a rejection that never happened.

1. If a file for the concept exists, add the issue to its Prior requests. Otherwise create one.
2. Post a comment on the issue that explains the decision, names the file, and links the PR that adds or updates it.
3. Close the issue as `wontfix`.

## The file

One file per **concept**, not per issue, named in kebab-case so the directory reads at a glance: `dark-mode.md`, `plugin-system.md`, `graphql-api.md`.

Write it like a short design note, with paragraphs, code samples, and examples where they make the reasoning clear to someone meeting it for the first time. Give a reason that lasts: the project's scope, a technical constraint, or a strategic choice. "We're too busy right now" is a deferral, and belongs nowhere in this directory.

````markdown
# Dark Mode

This project does not support dark mode or user-facing theming.

## Why this is out of scope

The rendering pipeline assumes a single color palette defined in
`ThemeConfig`. Supporting multiple themes would require:

- A theme context provider wrapping the entire component tree
- Per-component theme-aware style resolution
- A persistence layer for user theme preferences

This is a significant architectural change that doesn't align with the
project's focus on content authoring. Theming is a concern for downstream
consumers who embed or redistribute the output.

```ts
// The current ThemeConfig interface is not designed for runtime switching:
interface ThemeConfig {
  colors: ColorPalette; // single palette, resolved at build time
  fonts: FontStack;
}
```

## Prior requests

- #42: "Add dark mode support"
- #87: "Night theme for accessibility"
- #134: "Dark theme option"
````
