# skills

My personal collection of agent skills, installable with the [`skills`](https://github.com/vercel-labs/skills) CLI.

## Install

```sh
# Interactive: pick skills and agents
npx skills add dante-sparras/skills

# One skill
npx skills add dante-sparras/skills --skill work
```

## Skills

| Skill | Description |
| --- | --- |
| [work](skills/work/SKILL.md) | Runs a task as a cost-efficient agent tree in T3 Code: the agent you invoke it on coordinates and spawns only what it needs, explorers locate code, implementers build each ticket in its own worktree onto one integration branch, the repo's checks prove the integrated result, and two reviewers on different models approve it before it is pushed. You pick the model for each role at the start (recommended: Grok 4.7 Fast explorers, Opus 5.5 implementers, Opus 5.5 and GPT-6.1 Sol reviewers). After that it lands the change on its own and comes back only for a decision that is yours. Builds on [Matt Pocock's skills](https://github.com/mattpocock/skills), which must be installed: it takes their specs and tickets as input and calls `tdd`, `code-review`, `diagnosing-bugs`, and `pr`. Start with `/work <task>`. |

## Adding a skill

1. `cd skills && npx skills init <name>`
2. Edit `skills/<name>/SKILL.md`. The frontmatter needs a lowercase, hyphenated `name` and a `description` that says what the skill does and when to use it.
3. Test locally from the repo root: `npx skills add ./ --list`.
4. Document the skill here, then commit and push.
