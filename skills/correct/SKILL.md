---
name: correct
description: "Turn each mistake agents repeat in this repo into a check that fails: architecture, then types, then a lint, then a test, docs last."
disable-model-invocation: true
---

# Correct

The operator keeps correcting agents in this repo for the same mistakes. Change the repo so the next agent can't make them.

Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repo so a change that looks right from one file is right for the whole repo.

Run this each time the operator corrects an agent, and whenever the operator asks for a look back at a session.

## 1. Read the evidence

1. Read the session the operator names, from its transcript or the session logs on this machine. With no session named, read the current one.
2. Read recent commits, reverts, PR review comments, `AGENTS.md`, and `CODING_STANDARDS.md`.
3. Read the repo's own check command: its `package.json` or build-tool `lint` and `check` scripts, its pre-commit hooks, and its CI workflow. A check that already exists but sits unwired or silently broken is the finding, so repair it before you build a new one. A repo with no **guardrail** (no pre-commit hook and no CI job running its lint, typecheck, or test command) is itself a finding.

Done when every correction, revert, and failed attempt in the evidence has a line in your notes.

## 2. Group the mistakes into classes

Group the notes into **mistake classes**. A class counts once it has happened twice, or once the operator has corrected it. Wrong code is one kind of class. The session also shows these:

- **Navigation**: the agent took a long time to find a file or a fact, or missed a hidden dependency between files.
- **Tool economy**: the agent made an expensive tool call, or a CLI or MCP tool spent many tokens for little output.
- **Information access**: a crucial piece of information was out of the agent's reach, such as dev server output or the state of a third-party service.
- **Steering**: a line in `AGENTS.md` (in the repo or the operator's global scope) changes nothing the agent does, or steers behavior that a check or `CODING_STANDARDS.md` should own.

Rank the classes by how often they happened and how much each one cost.

## 3. Fix each class at the highest level that works

Try each level in order and stop at the first one that makes the mistake impossible or loud.

1. **Eliminate it with architecture.** Give each piece of state one owner and each task one supported way. Hide internals so the wrong import fails. Replace hand-synced lists with one source of truth. Delete old ways and dead code an agent would copy. Co-locate files that change together, which also fixes most navigation classes. Fix tool economy here too, with a script or CLI flag that prints only what the agent needs. Fix information access by teeing logs to a file the agent can read, or by giving it read-only access to the service.
2. **Enforce it with types**, so the bad state can't be written.
3. **Add a lint or CI check whose error names the fix.** A **mechanical** mistake (a fixed syntax pattern, a banned API, an import shape, a file-location rule) gets a deterministic check at this level whenever types can't catch it. Use a custom rule in the repo's own linter, a pre-commit hook, or a CI job, whichever the repo's language and existing guardrail make cheapest. The error message names the file, type, or function to use instead. If the pattern is already common, fail only when a change adds more.
4. **Test the behavior.** Fix or delete any test that still passes when the behavior it checks breaks, or that fails when only the internals change.
5. **Write docs last, only for judgment calls**, such as cross-file consistency or matching the surrounding style. Nothing fails when an agent skips a doc. Call the `writing-for-agents` skill before you write one, and put it where the reader in [Implementation vs review](#implementation-vs-review) will see it.

### Implementation vs review

All work passes through two agents. The **implementation agent** carries the most **context pressure**: it explores, writes code, and debugs failures. The **review agent** carries the least: it receives a diff, so it explores little and rarely writes code. Judgment-call rules belong to the review agent.

| File | Read by | Holds |
| --- | --- | --- |
| `AGENTS.md` | every agent, every turn | navigation pointers only |
| `CODING_STANDARDS.md` | the review agent, via `/code-review` | judgment-call rules and the rule table |
| `GLOSSARY.md` | any agent naming a domain concept | domain terms, per the `domain-modeling` skill |
| a skill | the agent its description triggers, or the operator | a repeatable procedure |
| other docs | an agent following a pointer | reference too long for the files above |

Search for an existing doc before you write a new one. Add navigation pointers to docs folders once `CODING_STANDARDS.md` passes 1,000 lines.

## 4. Fix and prove

Fix the top classes now, one commit each. Prove each new check against the real past mistake:

1. Reapply the commit or diff that made the mistake, or check it out.
2. Run the check and confirm it fails with an error that names the fix.
3. Restore the fix and confirm the check passes.

Run the same command locally and in CI. Exceptions live in one allowlist file the check reads, each entry with the path, a reason, an expiry date, and the human who approved it.

## 5. Keep the rule table

Keep a table in `CODING_STANDARDS.md` that pairs each rule with what enforces it:

| Rule | Enforced by |
| --- | --- |
| Import the database client only from `src/db/index.ts` | `no-restricted-imports` in `eslint.config.js` |
| Name handlers after the domain event they handle | review |

When the operator corrects an agent, fix the mistake and add the rule. A rule already in the table that only review enforces is a repeat, so move it up a level in the same change. Drop a rule once its mistake can't happen, and delete `AGENTS.md` lines that change nothing.

## Reply

List the classes in order of severity. For each, give its evidence, the level you picked, why a higher level didn't work, and the output of the check failing on the past mistake. List the classes you left unfixed as candidates for the next run.
