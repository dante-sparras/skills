---
name: domain-modeling
description: "Build and sharpen a project's domain model and write it down in GLOSSARY.md. Use when changing the model rather than reading it: a term is fuzzy, overloaded, or contested, a design names a new concept, or GLOSSARY.md or GLOSSARY-MAP.md needs creating or editing."
---

# Domain modeling

Build and sharpen the project's domain model as you design: challenge terms, invent edge cases, and write each term down the moment it settles.

## Where the glossary lives

- **One context**, which is most repos: `GLOSSARY.md` at the repo root.
- **Several contexts**: `GLOSSARY-MAP.md` at the root points to each context's own `GLOSSARY.md`. Infer which context the topic belongs to, and ask when it is unclear.
- **Neither file exists**: create a root `GLOSSARY.md` when the first term settles.

[GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md) has the format for both files.

## During the session

- **Challenge against the glossary.** When the user's term conflicts with `GLOSSARY.md`, say so at once: "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"
- **Sharpen fuzzy language.** For a vague or overloaded term, propose one precise term: "You're saying 'account'. Do you mean the Customer or the User?"
- **Test with scenarios.** When relationships between concepts are on the table, invent specific edge cases that force the user to say where one concept ends and the next begins.
- **Check the code.** When the user says how something works, see whether the code agrees, and surface a contradiction: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"
- **Write it down now.** Update `GLOSSARY.md` the moment a term settles, one term at a time.

`GLOSSARY.md` holds terms and their meanings, and nothing else. Implementation details, decisions, and notes go elsewhere.
