---
name: research
description: "Research a question against primary sources, in the background. Use when the user asks to research a topic, or when a decision waits on facts the repo's code cannot give: a library's docs, a third-party API, or a standard."
---

# Research

Read [Resolve a role](../factory/model-roles.md#resolve-a-role) for the `worker`, since findings that settle a decision need the stronger model. Start it in the background with a fresh context, told to change no files, so you can keep working.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Return the findings as one write-up, with each claim's source cited beside it, and what it could not settle marked as open.

Give the user the findings in this conversation. Research makes no branch, commit, or PR. Save the write-up to a file, or post it on an issue, only when the user asks for that.
