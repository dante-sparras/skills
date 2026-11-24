# Skill mechanics

What changes when the document is a skill: the invocation choice, splitting by invocation, and router skills. Everything else is in [`SKILL.md`](SKILL.md).

## Invocation

| | Model-invoked | User-invoked |
| --- | --- | --- |
| **Who reaches it** | The agent on its own, other skills through the Skill tool, and the human by name | Only the human typing its name. The Skill tool will not load it |
| **Cost** | Context load: the description stays in context every turn | Cognitive load: you are the index that must remember it exists |
| **Frontmatter** | Omit `disable-model-invocation` | `disable-model-invocation: true` |
| **Description** | Written for the model, ending in a `Use when` sentence that carries the trigger branches | Written for the human: what the skill does, then a `Use when` sentence naming when a person reaches for it |

Choose model-invoked only when the agent, or another skill, must reach the skill on its own. If it only ever fires by hand, make it user-invoked and pay no context load.

- **Running a user-invoked skill from another skill.** An agent that reads `../<name>/SKILL.md` and follows it has run the skill. This is how a `coordinate` worker reaches `plan` and `triage`.
- **Shared reference.** A model-invoked skill that is all reference is a home for material several skills need, since any of them can invoke it. Reference shared by two user-invoked skills goes in a plain file both point at.

## Splitting by invocation

Split off a model-invoked skill when it has a distinct leading word that should trigger it on its own, one you use in your prompts, or when another skill must reach it. The new description costs context load on every turn, so that independent reach has to be worth it.

## Router skills

When user-invoked skills multiply past what you can remember, add a **router skill**: one user-invoked skill that names the others and when to reach for each. A router that only names them can hint and no more. A router that reads their `SKILL.md` files by path runs them, as `coordinate`'s workers do.
