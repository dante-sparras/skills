# skills

My personal collection of agent skills, installable with the [`skills`](https://github.com/vercel-labs/skills) CLI.

There are currently no skills in this repository.

## Adding a skill

1. Create the `skills` directory and run `npx skills init <name>` inside it.
2. Edit `skills/<name>/SKILL.md`. The frontmatter needs a lowercase, hyphenated `name` and a `description` that says what the skill does and when to use it.
3. Test locally from the repo root: `npx skills add ./ --list`.
4. Document the skill here, then commit and push.
