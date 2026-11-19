# skills
Dante's agent skills

## Upstream

The skills below started as copies of [mattpocock/skills](https://github.com/mattpocock/skills) at commit [`5863806dd4e15c63174bee4e7515a4256792ecfa`](https://github.com/mattpocock/skills/tree/5863806dd4e15c63174bee4e7515a4256792ecfa) and have been edited since. Each one lives in `skills/<name>/`.

### Engineering

- [code-review](./skills/code-review/SKILL.md)
- [codebase-design](./skills/codebase-design/SKILL.md)
- [diagnosing-bugs](./skills/diagnosing-bugs/SKILL.md)
- [domain-modeling](./skills/domain-modeling/SKILL.md)
- [grill-with-docs](./skills/grill-with-docs/SKILL.md)
- [implement-spec](./skills/implement-spec/SKILL.md)
- [improve-codebase-architecture](./skills/improve-codebase-architecture/SKILL.md)
- [pr](./skills/pr/SKILL.md)
- [prototype](./skills/prototype/SKILL.md)
- [research](./skills/research/SKILL.md)
- [setup-skills](./skills/setup-skills/SKILL.md)
- [tdd](./skills/tdd/SKILL.md)
- [to-spec](./skills/to-spec/SKILL.md)
- [to-tickets](./skills/to-tickets/SKILL.md)
- [triage](./skills/triage/SKILL.md)
- [wayfinder](./skills/wayfinder/SKILL.md)

### Productivity

- [grilling](./skills/grilling/SKILL.md)
- [writing-for-agents](./skills/writing-for-agents/SKILL.md)

### pstack

[correct](./skills/correct/SKILL.md) started as a copy of the `correct` skill in Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack) at commit [`e5136d82418d2db3165ea1050d17577cd618cc05`](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/skills/correct). It also absorbs the upstream `retro` skill from mattpocock/skills.

[code-review](./skills/code-review/SKILL.md) takes its adversarial reviewer panel from the `interrogate` skill in pstack at commit [`ab1f702ce8e8b6557edb56b09f52cde8bfb83f17`](https://github.com/cursor/plugins/tree/ab1f702ce8e8b6557edb56b09f52cde8bfb83f17/pstack/skills/interrogate): the adversary brief, picking reviewers from different model families, and rerunning each finding before it is reported.

[implement-spec](./skills/implement-spec/SKILL.md) takes its landing flow from the poteto-mode playbooks in pstack at commit [`35a90942a7f02e1ebbc2443643179815f2147954`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/poteto-mode/playbooks): one owner and one PR per task off trunk, the ledger, the rebase-when-trunk-matters rule, and the forge-approval guardrail from Autopilot-full, the hand-off mode from Autopilot-stack, the per-task file plan from Multi-phase plan, and independent verdicts carried across a rebase by `git patch-id` and bottom-up landing from Shipping. Grouping tickets that share a file comes from pstack's `principle-separate-before-serializing-shared-state`.

[tdd](./skills/tdd/SKILL.md) takes its test-first rules from pstack at commit [`35a90942a7f02e1ebbc2443643179815f2147954`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/tdd): the bug-fix loop that sees red before the fix, when to skip a test, the closest checks that prove skipped work, the guardrails, and the evidence report. It also takes the two imagined edits that judge a test from [`principle-test-behavior-not-implementation`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/principle-test-behavior-not-implementation), real-artifact proof from [`principle-prove-it-works`](https://github.com/cursor/plugins/tree/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/principle-prove-it-works), and the red-then-green commit order and same-surface verification from the [Bug fix playbook](https://github.com/cursor/plugins/blob/35a90942a7f02e1ebbc2443643179815f2147954/pstack/skills/poteto-mode/playbooks/bug-fix.md). Seams, vertical slices, and the mocking and test examples stay from mattpocock/skills.

[setup-skills](./skills/setup-skills/SKILL.md) takes its model role configuration from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

### Other credits

[pr](./skills/pr/SKILL.md) adapts its visual examples and placement guidance from Dex Horthy's [`show-me` skill](https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md).

[codebase-design](./skills/codebase-design/DESIGN-IT-TWICE.md) uses John Ousterhout's Design It Twice method.

## License

The upstream skills are by Matt Pocock and are used under the MIT License. See [LICENSES/mattpocock-skills.md](./LICENSES/mattpocock-skills.md).

The pstack skills are by Lauren Tan and are used under the MIT License. See [LICENSES/pstack.md](./LICENSES/pstack.md).
