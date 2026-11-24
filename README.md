# skills
Dante's agent skills

## How the skills fit together

Start with [`/coordinate`](./skills/coordinate/SKILL.md) and hand it your tasks, one or several at once: bugs, features, issues, questions, PRs to merge. The agent you typed it to becomes the **coordinator**: the one agent you talk to, whose job is that every task ships.

One rule runs it all: **one task, one worker, one PR.** The skills are written for T3 Code: each worker is a `delegate_task` child with its own thread and checkout.

1. **The coordinator makes each thing a task** and starts a worker for it.
2. **The worker sizes its own task**, and the coordinator tells you how. If it fits in one PR, the worker builds it. It asks you about a single open decision in its own thread. If the task is more than one PR, the worker interviews you there, writes a spec and its tickets, and hands the tickets back. Each ticket becomes a new task.
3. **The coordinator sends a reviewer to each PR**, once its checks are green. The reviewer and the worker argue each finding until they agree: the worker fixes it, or the reviewer withdraws it. After three rounds without agreement, the coordinator brings both positions to you.
4. **The coordinator merges** once the checks are green again, or hands you a merge list when merging is yours.
5. **Anything that comes up becomes a new task**: a bug nobody owns, a teammate's review, a mistake that repeats.

```mermaid
%%{init: {"sequence": {"mirrorActors": false}}}%%
sequenceDiagram
    autonumber
    actor You
    participant C as Coordinator
    participant W as Worker
    participant R as Reviewer

    You->>C: Tasks, one or many
    C->>W: One task per worker
    W->>C: How it sized its task
    C->>You: One line per task

    alt Path A: the task fits in one PR
        W->>C: Opens a PR
        Note over C: Waits for green checks
        C->>R: Review this PR
        loop Until they agree on every finding, at most three rounds
            R->>W: Findings
            W->>R: Per finding: a fix, or a counter-argument
        end
        R->>C: PASS, or no agreement
        Note over C: Merges once checks are green.<br/>No agreement goes to you
        C->>You: Merged, or on your merge list
    else Path B: the task is more than one PR
        W->>You: Interview, in the worker's own thread
        You->>W: Answers, and approval of the tickets
        W->>C: A spec and its tickets
        Note over C: Each ticket becomes a new task, from step 2
    end
```

Read the diagram top to bottom. Each arrow is a message, and the numbers give the order. A task takes path A or path B.

The whole flow is four files: one per role, and the rules they share. [GLOSSARY.md](./GLOSSARY.md) defines the terms.

| File | Who reads it | What it holds |
| --- | --- | --- |
| [`coordinate/SKILL.md`](./skills/coordinate/SKILL.md) | The coordinator | The loop: intake, start, receive, review, land, check |
| [`coordinate/worker.md`](./skills/coordinate/worker.md) | Every worker | How to size a task, build it, or split it |
| [`coordinate/reviewer.md`](./skills/coordinate/reviewer.md) | The reviewer of a PR | How to review it, and argue each finding with its worker |
| [`coordinate/rules.md`](./skills/coordinate/rules.md) | All three | Trust, the AI marker, messages, git, PR tools, and how to run a skill |

Every other skill is a tool a worker picks up when its task calls for it. You type one more yourself: [setup-skills](./skills/setup-skills/SKILL.md), once per repo.

## Skills

Every skill lives at `skills/<name>/`, the same layout it installs to.

| Skill | What it does |
| --- | --- |
| [coordinate](./skills/coordinate/SKILL.md) | The entry point. Makes each request a task, starts a worker for it, and ships it |
| [debug](./skills/debug/SKILL.md) | Finds the cause of a hard bug or a slowdown, then fixes it with a regression test |
| [deepen](./skills/deepen/SKILL.md) | The deep-module vocabulary, and a survey that finds modules worth deepening |
| [glossary](./skills/glossary/SKILL.md) | Keeps the project's domain terms in `GLOSSARY.md` |
| [guardrail](./skills/guardrail/SKILL.md) | Turns a mistake agents repeat into a check that fails |
| [interrogate](./skills/interrogate/SKILL.md) | Adversarial review of a diff by models from different families |
| [interview](./skills/interview/SKILL.md) | Questions you in rounds until a plan or decision is settled |
| [map](./skills/map/SKILL.md) | Charts work too big for one session as decision tickets |
| [new-verify-skill](./skills/new-verify-skill/SKILL.md) | Generates a `verify-<app>` skill that drives the real app |
| [plan](./skills/plan/SKILL.md) | Turns a conversation into a spec and its tickets |
| [pr-body](./skills/pr-body/SKILL.md) | Writes a PR description: a summary diagram, evidence, and merge danger |
| [research](./skills/research/SKILL.md) | Investigates a question against primary sources in the background |
| [setup-skills](./skills/setup-skills/SKILL.md) | Sets up a repo's tracker, labels, and model roles for these skills |
| [tdd](./skills/tdd/SKILL.md) | Test-first for bug fixes and core logic, and proof for everything else |
| [triage](./skills/triage/SKILL.md) | Moves issues and outside PRs through triage states |
| [writing-for-agents](./skills/writing-for-agents/SKILL.md) | Reference for writing skills and other docs that agents read |

## Install

Install every skill into your agent's skills folder, side by side: `<skills folder>/<name>/`. `npx skills add` does this, and so does linking each `skills/<name>/` folder by hand.

The skills reach each other by relative paths such as `../tdd/SKILL.md` and `../setup-skills/MODEL-ROLES.md`, so a skill installed alone loses them.

The plugin manifest does not list `coordinate`, so a Claude plugin install leaves it out. Add it with `npx skills add` or a link.

Run `python3 scripts/check.py` before you push, or `python scripts/check.py` on Windows. CI runs the same command.

## Upstream

The skills below started as copies of [mattpocock/skills](https://github.com/mattpocock/skills) at commit [`5863806dd4e15c63174bee4e7515a4256792ecfa`](https://github.com/mattpocock/skills/tree/5863806dd4e15c63174bee4e7515a4256792ecfa) and have been edited since. Each one lives in `skills/<name>/`.

- [debug](./skills/debug/SKILL.md)
- [deepen](./skills/deepen/SKILL.md)
- [glossary](./skills/glossary/SKILL.md)
- [interrogate](./skills/interrogate/SKILL.md)
- [interview](./skills/interview/SKILL.md)
- [map](./skills/map/SKILL.md)
- [plan](./skills/plan/SKILL.md)
- [pr-body](./skills/pr-body/SKILL.md)
- [research](./skills/research/SKILL.md)
- [setup-skills](./skills/setup-skills/SKILL.md)
- [tdd](./skills/tdd/SKILL.md)
- [triage](./skills/triage/SKILL.md)
- [writing-for-agents](./skills/writing-for-agents/SKILL.md)

### pstack

These skills started from pstack, or are new here and built on its ideas:

- [coordinate](./skills/coordinate/SKILL.md)
- [guardrail](./skills/guardrail/SKILL.md)
- [new-verify-skill](./skills/new-verify-skill/SKILL.md)

[guardrail](./skills/guardrail/SKILL.md) started as a copy of the `correct` skill in Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack) at commit [`e5136d82418d2db3165ea1050d17577cd618cc05`](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/skills/correct). It also absorbs the upstream `retro` skill from mattpocock/skills.

[interrogate](./skills/interrogate/SKILL.md) takes its adversarial reviewer panel from the `interrogate` skill in pstack at commit [`ab1f702ce8e8b6557edb56b09f52cde8bfb83f17`](https://github.com/cursor/plugins/tree/ab1f702ce8e8b6557edb56b09f52cde8bfb83f17/pstack/skills/interrogate): the adversary brief, picking reviewers from different model families, and rerunning each finding before it is reported.

[tdd](./skills/tdd/SKILL.md) takes its test-first rules from pstack at commit [`35a90942a7f02e1ebbc2443643179815f2147954`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/tdd): the bug-fix loop that sees red before the fix, when to skip a test, the closest checks that prove skipped work, the guardrails, and the evidence report. It also takes the two imagined edits that judge a test from [`principle-test-behavior-not-implementation`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/principle-test-behavior-not-implementation), real-artifact proof from [`principle-prove-it-works`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/principle-prove-it-works), and the red-then-green commit order and same-surface verification from the [Bug fix playbook](https://github.com/cursor/plugins/blob/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/poteto-mode/playbooks/bug-fix.md). Seams, vertical slices, and the mocking and test examples stay from mattpocock/skills.

[new-verify-skill](./skills/new-verify-skill/SKILL.md) started as a copy of the `create-verification-skill` skill in pstack at commit [`e58dd043600587dbaf58ba315e7f2b38373eeb43`](https://github.com/cursor/plugins/tree/e58dd043600587dbaf58ba315e7f2b38373eeb43/pstack/skills/create-verification-skill), including its feature map example.

[coordinate](./skills/coordinate/SKILL.md) takes its entry point from the `poteto-mode` skill in pstack at commit [`7a583913eb1b8d1a0ee76753d1a2cf072e7b54f9`](https://github.com/cursor/plugins/tree/7a583913eb1b8d1a0ee76753d1a2cf072e7b54f9/pstack/skills/poteto-mode): one user-invoked skill a person starts every task with, and a `worker.md` that opens every subagent's brief, since the rules reach a subagent no other way. Its build flow follows the poteto-mode playbooks at commit [`35a90942a7f02e1ebbc2443643179815f2147954`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/poteto-mode/playbooks): one worker and one PR per task off trunk, an independent verdict before a PR lands, the forge-approval guardrail, and the hand-off mode. The coordinator loop and the worker's sizing table are new here.

[setup-skills](./skills/setup-skills/SKILL.md) takes its model role configuration from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

### Other credits

[pr-body](./skills/pr-body/SKILL.md) adapts its visual examples and placement guidance from Dex Horthy's [`show-me` skill](https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md).

[deepen](./skills/deepen/DESIGN-IT-TWICE.md) uses John Ousterhout's Design It Twice method.

## License

The upstream skills are by Matt Pocock and are used under the MIT License. See [LICENSES/mattpocock-skills.md](./LICENSES/mattpocock-skills.md).

The pstack skills are by Lauren Tan and are used under the MIT License. See [LICENSES/pstack.md](./LICENSES/pstack.md).
