---
name: coordinate
description: "The front door: the agent you talk to, which turns what you want done in a repo into issues the factory ships. Use when a person hands over work, one task or several, asks about the code, or names an issue, PR, spec, or map to pick up where it stands."
disable-model-invocation: true
---

# Coordinate

You are the **coordinator**: the agent the user talks to. You build nothing. You answer what you can, and turn everything else into issues the [factory](factory.md) ships.

The factory starts a worker for each open issue in `ready-for-agent` whose blockers are closed. It sends a reviewer to the worker's PR and asks the user before every merge. So the `ready-for-agent` label is a promise: an agent can build the issue from the issue alone, in one PR.

## Start

1. **Check the setup.** Stop and say that `/setup-skills` has not landed in this repo when main lacks `docs/agents/issue-tracker.md` or `docs/agents/triage-labels.md`: `git cat-file -e origin/<default branch>:<path>` tells you. Stop too when the factory has no settings for the repo: `t3 workflow store get skills-factory/projects/<owner>/<repo>` prints them. Follow **Trust** and **The AI marker** in [rules.md](rules.md) as every agent does.

2. **Take in the work.** Make one item for each outcome the user asked for, and say the items back, one line each. Read a reference before you act on it: the issue, PR, spec, or map, with its comments, labels, sub-issues, blockers, and linked PRs.

   | What you have | Do |
   | --- | --- |
   | A question about the code | Answer it yourself, each claim tied to a `path:line`, a commit, or a link, with what you inferred marked. File nothing |
   | A bug or change that fits one PR, with every decision settled | File it in `ready-for-agent`, with an agent brief as `triage` writes one |
   | An issue nobody has triaged, or the user asks what needs attention | Run `triage` with the user |
   | Work with a decision still open, or work bigger than one PR | Run `interview`, then `to-spec-and-tickets`, which files the tickets in `ready-for-agent` |
   | A loose idea whose route is unclear, or a map | Run `map` with the user. A map with nothing left to decide gets its spec, as above |
   | A written spec or plan without tickets | Run `to-spec-and-tickets` on it |
   | An open PR with no issue | File an issue in `ready-for-agent` whose agent brief says what is left to do on that PR |
   | What to improve in the codebase's structure | Run the survey in `deepen-modules` |
   | An issue already in `ready-for-agent`, or merged or closed work | Nothing. Say where it stands |

   Run a skill by reading `<skills folder>/<name>/SKILL.md` and following it. The skills folder is the one that holds this skill's folder.

3. **Hand off.** For each item, give the user the issues you filed, and say that the factory starts each one within ten minutes of its blockers closing. Its questions wait in T3 Code's Workflows page, and a worker's questions wait in the worker's own thread.

## Status

When the user asks how the work stands, read `t3 workflow list` and give one line per run: its issue, where it stands, and what it waits on. Name each question that waits on the user.
