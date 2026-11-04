# skills

My personal collection of agent skills, installable with the [`skills`](https://github.com/vercel-labs/skills) CLI.

## Install

```sh
# Interactive: pick skills and agents
npx skills add dante-sparras/skills

# One skill
npx skills add dante-sparras/skills --skill setup-repo

# Everything, globally, for Claude Code, no prompts
npx skills add dante-sparras/skills -g -a claude-code -y

# List what's available without installing
npx skills add dante-sparras/skills --list

# Pull in updates
npx skills update
```

`bunx skills ...` works the same way.

## Skills

| Skill | Description |
| --- | --- |
| [moa](skills/moa/SKILL.md) | Mixture of Agents: sends one task to several independent agents, possibly on different models, and aggregates their answers. For reviews, designs, plans, hard bugs, and choosing between patches. |
| [setup-repo](skills/setup-repo/SKILL.md) | Sets up an existing repo, or scaffolds a new project, with the standard baseline: AGENTS.md, CONTRIBUTING.md, `.github/` templates and workflows, docs, license, and GitHub settings. |
| [work](skills/work/SKILL.md) | Runs a task with Opus as lead in T3 Code: Haiku explorers read in parallel, Sonnet coders write the code in their own worktrees (at most 3 at a time), and Opus plans, decides, and sees the PR through to merge. T3 Code only; start with `/work <task>`. |

## Adding a skill

1. `cd skills && npx skills init <name>`
2. Edit `skills/<name>/SKILL.md`. The frontmatter needs a lowercase, hyphenated `name` and a `description` that says what the skill does and when to use it.
3. Test locally from the repo root: `npx skills add ./ --list`
4. Add it to the table above, then commit and push.
