# skills
Dante's agent skills

## Upstream

The skills below started as copies of [mattpocock/skills](https://github.com/mattpocock/skills) at commit [`5863806dd4e15c63174bee4e7515a4256792ecfa`](https://github.com/mattpocock/skills/tree/5863806dd4e15c63174bee4e7515a4256792ecfa) and have been edited since. Each one lives in `skills/<name>/`.

### Engineering

- [code-review](./skills/code-review/SKILL.md)
- [codebase-design](./skills/codebase-design/SKILL.md)
- [coordinate](./skills/coordinate/SKILL.md)
- [diagnosing-bugs](./skills/diagnosing-bugs/SKILL.md)
- [domain-modeling](./skills/domain-modeling/SKILL.md)
- [grill-with-docs](./skills/grill-with-docs/SKILL.md)
- [implement](./skills/implement/SKILL.md)
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
- [wizard](./skills/wizard/SKILL.md)

### Productivity

- [grilling](./skills/grilling/SKILL.md)
- [handoff](./skills/handoff/SKILL.md)
- [teach](./skills/teach/SKILL.md)
- [to-questionnaire](./skills/to-questionnaire/SKILL.md)
- [wait-what](./skills/wait-what/SKILL.md)
- [writing-for-agents](./skills/writing-for-agents/SKILL.md)

### pstack

[correct](./skills/correct/SKILL.md) started as a copy of the `correct` skill in Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack) at commit [`e5136d82418d2db3165ea1050d17577cd618cc05`](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/skills/correct). It also absorbs the upstream `retro` skill from mattpocock/skills.

[code-review](./skills/code-review/SKILL.md) takes its adversarial reviewer panel from the `interrogate` skill in pstack at commit [`ab1f702ce8e8b6557edb56b09f52cde8bfb83f17`](https://github.com/cursor/plugins/tree/ab1f702ce8e8b6557edb56b09f52cde8bfb83f17/pstack/skills/interrogate): the adversary brief, picking reviewers from different model families, and rerunning each finding before it is reported.

[setup-skills](./skills/setup-skills/SKILL.md) takes its model role configuration from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

[coordinate](./skills/coordinate/SKILL.md) adapts the Autopilot-stack and Autopilot-full playbooks, the files-per-PR rule of the Multi-phase plan playbook, and the `separate-before-serializing-shared-state` principle from pstack at commit [`2f87c854fe3e2fcda44ca86b46ede35aad3c46b7`](https://github.com/cursor/plugins/tree/2f87c854fe3e2fcda44ca86b46ede35aad3c46b7/pstack/skills/poteto-mode/playbooks) to T3 threads.

### Other credits

[pr](./skills/pr/SKILL.md) adapts its visual examples and placement guidance from Dex Horthy's [`show-me` skill](https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md).

[codebase-design](./skills/codebase-design/DESIGN-IT-TWICE.md) uses John Ousterhout's Design It Twice method.

## License

The upstream skills are by Matt Pocock and are used under the MIT License. See [LICENSES/mattpocock-skills.md](./LICENSES/mattpocock-skills.md).

The pstack skills are by Lauren Tan and are used under the MIT License. See [LICENSES/pstack.md](./LICENSES/pstack.md).
