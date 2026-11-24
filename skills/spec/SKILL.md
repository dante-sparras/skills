---
name: spec
description: "Turn the current conversation into a spec on the issue tracker: the problem, the solution, the user stories, and the decisions made. Use when a person has talked a feature through and wants it written up, or brings a feature bigger than one PR, usually before /ticket."
disable-model-invocation: true
---

# Spec

Write the **spec** for one feature from what this conversation and the codebase already hold, and publish it after one approval. `/ticket` then slices it into work for the factory.

[tracker.md](../factory/tracker.md) has the tracker's commands.

## Steps

1. **Gather.** Work from the conversation, and explore the code the feature touches. Write everything in the glossary's vocabulary.

2. **Settle what is open.** A spec records decisions, so each one is made first. When the conversation left one open, read [interview](../interview/SKILL.md) and follow it on the open decisions alone. With none open, ask nothing.

3. **Seams.** Choose the seams the tests go at. Take an existing seam over a new one, and the highest seam you can: the ideal number is one.

4. **Approve.** Show the user the seams and the user stories. Ask whether the seams match what they expect, and whether a story is missing. Done when the user approves.

5. **Publish** the spec from the template, with the `spec` label and no state label. The label keeps it out of the triage queue and marks it as the parent of tickets, not as work to grab. The factory puts `ready-for-agent` on a spec itself, once its last ticket lands, to check it. Done when you have given the user the spec's reference, and said that `/ticket` slices it into work for the factory.

Keep file paths and code snippets out of the spec, since they go stale. The exception is a snippet that states a decision more exactly than prose can, such as a state machine, a schema, or a type shape. Trim it to the decision.

## Template

```md
## Problem Statement

The problem, from the user's perspective.

## Solution

The solution, from the user's perspective.

## User Stories

A numbered list, one story per actor and outcome:

1. As a <actor>, I want <feature>, so that <benefit>

Cover every actor and outcome, then stop.

## Implementation Decisions

The decisions made: the modules built or changed and their interfaces, architecture, schema changes, API contracts, and clarifications from the developer.

## Testing Decisions

- The seams the tests go at, as the user approved them
- The modules that get tests, and prior art for those tests in the codebase

## Out of Scope

What this spec leaves out.

## Further Notes
```
