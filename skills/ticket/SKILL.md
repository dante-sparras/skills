---
name: ticket
description: "Slice a spec, a written plan, or the current conversation into tracer-bullet tickets the factory builds, each naming what blocks it. Use when a spec is ready to be built, or a person describes a change that fits one PR with nothing left to decide."
disable-model-invocation: true
---

# Ticket

Slice work into **tickets**, each one PR for one worker, and publish them in `ready-for-agent` after one approval.

Every ticket is work for the factory, so follow [handoff.md](../setup-skills/factory/handoff.md). [tracker.md](../setup-skills/factory/tracker.md) has the tracker's commands.

## Steps

1. **Gather.** Take the spec the user named, with its body and comments, or the conversation. Explore the code the work touches, and write everything in the glossary's vocabulary.
   - **Work that fits one PR** is one ticket, and needs no spec.
   - **Work that needs several tickets** hangs off a spec, since the factory checks a spec once its tickets land. With no spec, stop and say that `/spec` writes it.
   - **A decision still open** is the user's to make. Name it, and say that `/interview` settles it.

2. **Slice** the work into tracer-bullet tickets.
   - Each cuts a narrow, complete path through every layer: schema, API, UI, tests.
   - Each is demoable or verifiable alone, and fits one fresh context window.
   - Prefactoring comes first, in its own tickets: make the change easy, then make the easy change.
   - Each names its **blockers**: the tickets that must land before it can start.
   - A [wide refactor](#wide-refactors) is sliced another way.

3. **Approve.** Show the user the tickets as a numbered list: title, blockers, and the end-to-end behavior each delivers. Ask whether any ticket should merge or split, and whether every blocker really gates its ticket. Done when the user approves.

4. **Publish.** One issue per ticket, with `ready-for-agent` and the category that fits, `enhancement` or `bug`. Its body is an agent brief, per [agent-brief.md](../setup-skills/factory/agent-brief.md). Done when every ticket is on the tracker and you have given the user each reference.
   - A ticket of a spec is its sub-issue, names it under `## Parent`, and takes its seams from the spec's testing decisions. With no spec, choose the seams yourself: an existing seam over a new one, and the highest seam you can.
   - Publish blockers first, so every ticket references real identifiers, and link each blocker with the tracker's native dependencies.
   - Leave the spec open and unedited. Give it the `spec` label when it has none.

## Wide refactors

A **wide refactor** is one mechanical change, such as renaming a column or retyping a shared symbol, that breaks call sites across the whole codebase at once. No vertical slice of it lands green, so sequence it as **expand-contract**:

1. **Expand.** Add the new form beside the old. Nothing breaks.
2. **Migrate** the call sites in batches sized by blast radius, such as one package or directory per ticket. Each is blocked by the expand and leaves main green, since the old form still exists. Merge batches that only go green together into one ticket.
3. **Contract.** Delete the old form, in a ticket blocked by every migrate batch.
