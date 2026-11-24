---
name: writing-for-agents
description: "Reference for writing documents agents consume. Use when creating or editing a skill or its description, or editing AGENTS.md, CLAUDE.md, or any doc an agent reaches through a pointer."
---

# Writing for Agents

Reference for writing any document an agent consumes: a skill, an `AGENTS.md`, a doc reached by a pointer. The goal is a predictable agent: one that takes the same _process_ every run.

When the document is a skill, also read [`skill-mechanics.md`](skill-mechanics.md) for frontmatter, the invocation choice, and router skills.

## Context pointers

A **context pointer** is a reference in the agent's context that names material outside it and states the condition for reaching it. A skill's description is one, and so is a line in `AGENTS.md` that names a doc. The pointer's wording, not its target, decides when the agent reaches the material and how reliably. When a must-have target is reached unreliably, sharpen the pointer first, and inline the material only if that fails.

A pointer says what the material is, and lists the **branches** that should trigger it. A branch is a distinct case the document handles. An always-loaded pointer costs on every turn, so prune it harder than the body:

- **Front-load the leading word.** The pointer is where it does its triggering.
- **One trigger per branch.** Synonyms for one branch are that branch written twice.
- **Cut identity the body already carries.**
- **Leave the steps to the body.** An agent follows a pointer that summarises the process in place of the document it names.

## The two loads

Every document and pointer spends one of two budgets:

- **Context load**: the cost of always-loaded material on the agent's window. An `AGENTS.md` line or a skill description spends tokens and attention every turn, whether or not it fires.
- **Cognitive load**: the cost on the human, who has to know which documents exist and when to reach for each. It is the price of human agency. Spend it where human judgement matters, and remove it where it does not.

Material behind a pointer costs only the pointer's line in context. Material with no pointer rides entirely on cognitive load.

## Information hierarchy

A document holds **steps**, the ordered actions the agent performs, and **reference**, the definitions, rules, and facts it consults on demand. Any mix is fine. Place each piece on the **information hierarchy** by how immediately the agent needs it:

1. **In-file step**: what the agent does, in order.
2. **In-file reference**: consulted on demand. A flat set of peers, such as every rule of a review, is a fine arrangement.
3. **Disclosed reference**: in another file, behind a context pointer, loaded only when the pointer fires.

Push too little down and the top bloats. Push too much and you hide what the agent needs.

- **Progressive disclosure** moves material down the ladder so the top stays legible. Branching is the test: inline what every branch needs, and put behind a pointer what only some branches reach. In-file reference that buries the steps makes attending to them a coin-flip.
- **Co-location** decides what sits beside a piece. Keep a concept's definition, rules, and caveats under one heading, so reading one part brings the rest.
- **Sprawl** is the failure: a document too long even when every line is live and unique. Attention thins across it. Cure it with the ladder, and by splitting along branches or sequence.

## Steps and completion criteria

Every step ends on a **completion criterion**: the condition that tells the agent the work is done. It has two properties.

- **Clarity**: can the agent tell done from not done? A vague bound, such as "understanding reached", invites **premature completion**, pulled by the steps still visible ahead. Sharpen the bound first, which is local and cheap. Only when it is irreducibly fuzzy and you have seen the rush, hide the later steps by splitting the sequence. Hiding works only across a real context boundary, such as a hand-off or a subagent.
- **Demand**: how much it requires. "Every modified model accounted for" forces thorough work where "produce a change list" does not. Demand drives **legwork**, the digging latent in the wording. It binds reference too: "every rule applied" sets an exhaustiveness bar on a flat list.

The strongest criteria are both checkable and exhaustive.

## When to split

A split spends one of the two loads, so make it only when the cut earns that.

- **By sequence**: split a run of steps where the later steps tempt the agent to rush the one in front of it. Merging sequences has the reverse effect.
- **By invocation**: see [`skill-mechanics.md`](skill-mechanics.md).

## Leading words

A **leading word** is a compact concept the model already holds from pretraining, which the agent thinks with while it runs the document: _lesson_, _fog of war_, _tracer bullets_. Repeated as a token, never as a sentence, it anchors a whole region of behaviour in few tokens. A coined word works when you define it clearly, but it recruits no priors, so reach for an existing word first.

It anchors twice. In the body it anchors execution: the agent reaches for the same behaviour each time the word appears. In a pointer it anchors invocation: when the same word lives in your prompts, your docs, and your code, the agent links that language to the material.

Hunt for passages a leading word can replace:

- "fast, deterministic, low-overhead" → _tight_, as in a _tight_ loop.
- "a loop you believe in" → _red_, which turns a fuzzy gate into an observable state.

**Negation** is the failure beside this lever. A prohibition names the forbidden behaviour and makes it more available: _don't think of an elephant_. State the target behaviour ("write one-line comments") so the banned one is never spoken. Keep a prohibition only as a hard guardrail you cannot phrase positively, and pair it with the positive target.

## Pruning

- **Single source of truth.** Keep each meaning in one authoritative place. **Duplication** costs maintenance and tokens, and lifts a meaning above its real rank.
- **The environment is a source of truth too**: `package.json` scripts, config files, the directory layout, `--help` output. A document that restates it is a **cache**, worth its load only when the lookup is expensive. Cache what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha no config confesses.
- **Relevance.** Check that every line still bears on what the document does. Lines lose it by being exposition, by belonging to a branch that should be disclosed, or by going stale. Without pruning, a document turns to **sediment**: stale layers that settle because adding feels safe and removing feels risky.
- **No-ops.** An instruction the model already obeys by default pays load to say nothing. The test is whether the sentence changes behaviour against the default, and it is settled by running the document, not by debate. Delete a failing sentence whole. A leading word too weak to beat the default, such as _be thorough_, is a no-op too: replace it with a stronger word, such as _relentless_.
