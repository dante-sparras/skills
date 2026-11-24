---
name: plan
description: "Turn the current conversation, or a written plan, into a spec and its tracer-bullet tickets on the issue tracker, with one approval and no interview. Use when a person has talked a feature through and wants it written up and split into tickets that workers can build."
disable-model-invocation: true
---

Write the **spec** from what this conversation and the codebase already hold, slice it into **tickets**, and publish both after one approval. Synthesize: the interview already happened.

Read `docs/agents/issue-tracker.md` for the tracker and `docs/agents/triage-labels.md` for the label strings. If either is missing, stop and say that `/setup-skills` has not run in this repo.

## Steps

1. **Gather.** Work from the conversation, and explore the code the feature touches. Write everything in the glossary's vocabulary. If the user passed a reference to a written spec or plan, fetch its body and comments: that issue is the spec, so you write only its tickets. A finished map is different: write a new spec from its Destination, Notes, and Decisions so far.

2. **Seams.** Choose the seams the tests go at. Take an existing seam over a new one, and the highest seam you can: the ideal number is one.

3. **Slice** the work into tracer-bullet tickets.
   - Each cuts a narrow, complete path through every layer: schema, API, UI, tests.
   - Each is demoable or verifiable alone, and fits one fresh context window.
   - Prefactoring comes first, in its own tickets: make the change easy, then make the easy change.
   - Each names its **blockers**: the tickets that must land before it can start.
   - A [wide refactor](#wide-refactors) is sliced another way.

4. **Approve.** Show the user the seams, then the tickets as a numbered list: title, blockers, and the end-to-end behavior each delivers. Ask whether the seams match what they expect, whether any ticket should merge or split, and whether every blocker really gates its ticket. Done when the user approves.

5. **Publish.** Done when every ticket is on the tracker and you have given the user the spec's reference.
   - The spec, from its template, with the `spec` label. The label keeps it out of the triage queue and marks it as the parent of tickets, not as work to grab.
   - One issue per ticket, from its template, each a sub-issue of the spec. Publish blockers first, so every ticket references real identifiers, and use the tracker's native blocking relationship where it has one. Apply `ready-for-agent` and the category that fits, `enhancement` or `bug`.
   - A spec that already existed gets the `spec` label and is otherwise left as it is: open and unedited.
   - A map the spec was written from gets a link to the spec, and is closed.

Keep file paths and code snippets out of both templates, since they go stale. The exception is a snippet that states a decision more exactly than prose can, such as a state machine, a schema, or a type shape. Trim it to the decision.

## Wide refactors

A **wide refactor** is one mechanical change, such as renaming a column or retyping a shared symbol, that breaks call sites across the whole codebase at once. No vertical slice of it lands green, so sequence it as **expand-contract**:

1. **Expand.** Add the new form beside the old. Nothing breaks.
2. **Migrate** the call sites in batches sized by blast radius, such as one package or directory per ticket. Each is blocked by the expand and leaves main green, since the old form still exists. Merge batches that only go green together into one ticket.
3. **Contract.** Delete the old form, in a ticket blocked by every migrate batch.

## Spec template

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

## Ticket template

```md
## Parent

A reference to the spec.

## What to build

The end-to-end behavior this ticket makes work, from the user's perspective.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Seams

The seams this ticket's tests go at, from the spec's testing decisions.

## Blocked by

A reference to each blocking ticket, or "None". Omit this section when the blockers are native links.
```
