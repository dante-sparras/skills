# skills

Agent skills that shape work into issues, and a **factory** that builds, reviews, and merges each issue on its own.

## Quick start

You need T3 Code with **Settings → Labs → Workflows** on, a GitHub repo, and `gh` signed in.

1. Install every skill: `npx skills add dante-sparras/skills`.
2. Type `/factory` once in each repo. It creates the labels, sets the model roles, and installs the factory.
3. Type the skill that fits what you have. Each one files issues the factory can build.
4. Review each PR, and add the `approved` label. The factory merges it.

Type `/factory` again at any time to see everything that waits on you.

## How it works

```mermaid
%%{init: {"flowchart": {"subGraphTitleMargin": {"top": 6, "bottom": 12}}}}%%
flowchart TD
    you(["<b>You</b>"]):::you
    intake["<b>/debug · /triage</b><br/><b>/spec · /ticket</b><br/>Your agent files the issues"]:::you
    ready[("<b>ready-for-agent</b><br/>Issues an agent can build")]
    ask["<b>Your review</b><br/>Add the approved label"]:::you
    triage[("<b>needs-triage</b><br/>Issues that wait on you")]:::you

    subgraph factory["The factory runs on its own"]
        start{{"<b>On each pass</b><br/>Starts each unblocked issue"}}
        worker["<b>Worker</b><br/>Builds the issue in one PR"]
        checks{"Checks"}
        review["<b>Reviewer</b><br/>Argues each finding with the worker"]
        merge["<b>Merge</b>"]
        learn["<b>After the merge</b><br/>Proves each finished spec<br/>Counts repeated friction"]
    end

    you -- "A bug, a change, an idea" --> intake
    intake --> ready
    ready --> start
    start --> worker
    worker -- "A PR" --> checks
    checks -- "Red, or a conflict" --> worker
    checks -- "Green" --> review
    review -- "PASS, or no agreement" --> ask
    worker <-. "A question, your answer" .-> ask
    ask -- "approved" --> merge
    merge --> learn
    start -. "A red main, as a bug" .-> ready
    learn -. "Spec gaps and guardrails" .-> ready
    learn -. "Follow-ups" .-> triage
    triage --> you

    classDef you fill:#1f6feb,stroke:#1158c7,color:#ffffff
    style factory fill:#8b949e1f,stroke:#8b949e
```

Blue is where you come in. A solid arrow follows one issue to its merge. A dotted arrow is something the factory does unasked.

### 1. Shape

| You have | Type |
| --- | --- |
| A bug | [`/debug`](./skills/debug/SKILL.md) |
| A change that fits one PR | [`/ticket`](./skills/ticket/SKILL.md) |
| A feature | [`/spec`](./skills/spec/SKILL.md), then `/ticket` |
| A decision to stress-test first | [`/interview`](./skills/interview/SKILL.md) |
| Issues nobody has looked at, or a PR with no issue | [`/triage`](./skills/triage/SKILL.md) |
| A question the code cannot answer | [`/research`](./skills/research/SKILL.md) |
| A codebase that is hard to change | [`/deepen-modules`](./skills/deepen-modules/SKILL.md), then `/spec` |

### 2. Ship

The [factory](./skills/factory/factory.md) is a T3 Code workflow. For each ready issue whose blockers are closed:

1. A **worker** builds it in one PR, and fixes red checks and conflicts.
2. A **reviewer** argues each finding with the worker, for at most three rounds.
3. The PR waits for your review. It never asks whether to open or merge a PR.
4. Your `approved` label merges it.

### 3. Learn

- When a spec's last ticket lands, a reviewer proves the spec on main. Each gap becomes a ticket.
- Friction that repeats across runs becomes an issue the factory fixes itself.
- Follow-ups land in `needs-triage`.

## What waits on you

The factory merges only what you approved, unless you turn on `autoMerge` for a repo. `/factory` lists all of this.

| Where | What waits there |
| --- | --- |
| The PR, on GitHub | Your review. Add `approved` to merge it, or comment and the worker picks it up. Merging or closing it yourself works too |
| The worker's thread, in T3 Code | A PR that is ready, your ruling when the reviewer and the worker disagree, or a worker's question. Every thread that is done settles itself |
| `needs-triage`, on the tracker | Follow-ups, and issues the factory stopped on, each with a comment that says why. Put `ready-for-agent` back on one to retry it |

GitHub does not let you approve a PR your own account opened, so the label is your approval.

[factory.md](./skills/factory/factory.md) has the details, and [GLOSSARY.md](./GLOSSARY.md) defines the terms.

## Skills

You type the skills under **Shape**, and `/factory`. Agents pick up the rest when their work calls for it.

| Skill | What it does |
| --- | --- |
| [factory](./skills/factory/SKILL.md) | Sets up the factory, shows what waits on you, and retries, stops, or pauses its runs |
| [create-verify-skill](./skills/create-verify-skill/SKILL.md) | Generates a `verify-<app>` skill that drives the real app |
| [interview](./skills/interview/SKILL.md) | Questions you in rounds until a decision is settled |
| [triage](./skills/triage/SKILL.md) | Moves issues and outside PRs up to `ready-for-agent` |
| [research](./skills/research/SKILL.md) | Investigates a question against primary sources, in the background |
| [glossary](./skills/glossary/SKILL.md) | Keeps the project's terms in `GLOSSARY.md` |
| [spec](./skills/spec/SKILL.md) | Turns a conversation into a spec |
| [ticket](./skills/ticket/SKILL.md) | Slices a spec, or one small change, into tickets |
| [tdd](./skills/tdd/SKILL.md) | Test-first for bug fixes and core logic |
| [prove](./skills/prove/SKILL.md) | Proves a change on the real artifact, with evidence |
| [debug](./skills/debug/SKILL.md) | Reproduces a bug and files it, or finds the cause and fixes it |
| [deepen-modules](./skills/deepen-modules/SKILL.md) | Finds modules worth deepening |
| [pr](./skills/pr/SKILL.md) | Writes a PR description: summary, evidence, and merge danger |
| [review-pr](./skills/review-pr/SKILL.md) | Adversarial review of a PR, by models from different families |
| [correct](./skills/correct/SKILL.md) | Turns a mistake agents repeat into a check that fails |
| [writing-for-agents](./skills/writing-for-agents/SKILL.md) | Reference for writing docs that agents read |

## Install

```
npx skills add dante-sparras/skills
```

Install all of them: the skills link to each other by relative path.

To work from a clone, run `python scripts/link-skills.py`. It links every skill into `~/.claude/skills` and `~/.agents/skills`. Run it again after a pull that adds, renames, or removes a skill.

## Checks

Run `python scripts/check.py` before you push. CI runs the same command.

## Credits

- [mattpocock/skills](https://github.com/mattpocock/skills) by Matt Pocock, under the MIT License: [LICENSES/mattpocock-skills.md](./LICENSES/mattpocock-skills.md)
- [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan, under the MIT License: [LICENSES/pstack.md](./LICENSES/pstack.md)
- [humanlayer/skills](https://github.com/humanlayer/skills) by Dex Horthy
