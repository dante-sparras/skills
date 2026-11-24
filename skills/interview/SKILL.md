---
name: interview
description: "Interview the user relentlessly until a plan, decision, or idea reaches shared understanding. Use when the user asks to be interviewed, wants a plan or design stress-tested, or brings a decision whose open branches need settling before work starts."
disable-model-invocation: true
---

# Interview

Interview the user relentlessly until you reach a shared understanding. Map the work as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are settled: the questions you can ask now without guessing at answers you have not heard. Ask the whole frontier in one round, then wait for the answers. A question that depends on another question in the same round belongs to a later round.

Number each question, give your recommended answer, and word the question so "yes" accepts it:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round of answers pushes the frontier outward. Recompute it and ask the next round.

- **A fact from the environment.** Read [Resolve a role](../setup-skills/model-roles.md#resolve-a-role) and start a fresh `explorer` to look it up. Ask the rest of the frontier while it runs.
- **A term that settles or sharpens.** In a repo, read [glossary](../glossary/SKILL.md) and follow it as terms come up, so each lands in `GLOSSARY.md` during the session.

The session is done when the frontier is empty: every branch visited, nothing left silently assumed. Act on it only once the user confirms you have reached a shared understanding.
