---
name: research
description: "Start a background agent that investigates a question against primary sources and writes cited findings to a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered before a decision, or reading legwork run in the background while work continues."
---

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) for the `explorer`. Start it in the background with a fresh context so you can keep working. Give it `isolation: "worktree"` when its findings go on a branch, so it never switches the branch under you.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where its reader will look. Findings that answer an issue (a ticket, a spec, a map) go on a `chore/research-<name>` branch, pushed without a PR and linked from that issue, so every session and worktree can reach them from the tracker. Findings kept for the repo's own reference go where the repo already keeps such notes. If it has no convention, put them somewhere sensible and say where.
