---
name: factory
description: "Hand work to the factory: turn a change, a bug, or a feature the user describes into issues the factory builds, reviews, and lands. Use when a person wants something done in a repo, one thing or several, or names an issue, PR, spec, or map to pick up where it stands."
disable-model-invocation: true
---

# Factory

The user tells you what they want done. You build none of it. You turn each thing into issues the [factory](factory.md) ships, and answer questions yourself.

The factory gives each open issue in `ready-for-agent` to a worker who sees the issue and nothing else, not this conversation. So write every issue so an agent can build it in one PR from the issue alone.

1. **Check the setup.** Stop and say so when `/setup-skills` has not landed in this repo: main lacks `docs/agents/issue-tracker.md` or `docs/agents/triage-labels.md`, which `git cat-file -e origin/<default branch>:<path>` tells you. Stop too when the factory has no settings for the repo: `t3 workflow store get skills-factory/projects/<owner>/<repo>` prints them. Follow **Trust** and **The AI marker** in [rules.md](rules.md).

2. **Take in the work.** Make one item for each outcome the user asked for, and say the items back, one line each. Read a reference before you act on it: the issue, PR, spec, or map, with its comments, labels, sub-issues, blockers, and linked PRs.

   | What the user brings | Do |
   | --- | --- |
   | A question about the code | Answer it, each claim tied to a `path:line`, a commit, or a link, with what you inferred marked. File nothing |
   | A bug or change that fits one PR, with every decision settled | File it in `ready-for-agent`, with an agent brief as `triage` writes one. Reproduce a bug first, so the brief carries the steps |
   | An issue nobody has triaged, or a question about what needs attention | Run `triage` with the user |
   | Work with a decision still open, or work bigger than one PR | Run `interview`, then `to-spec-and-tickets`, which files the tickets in `ready-for-agent` |
   | A loose idea whose route is unclear, or a map | Run `map` with the user. A map with nothing left to decide gets its spec, as above |
   | A written spec or plan without tickets | Run `to-spec-and-tickets` on it |
   | An open PR with no issue | File an issue in `ready-for-agent` whose agent brief says what is left to do on that PR |
   | What to improve in the codebase's structure | Run the survey in `deepen-modules` |
   | An issue already in `ready-for-agent`, or merged or closed work | Nothing. Say where it stands |

   Run a skill by reading `<skills folder>/<name>/SKILL.md` and following it. The skills folder is the one that holds this skill's folder.

3. **Hand off.** Give the user each issue you filed. The factory starts each one within ten minutes of its blockers closing, and everything it needs from the user waits in T3 Code's Workflows page.
