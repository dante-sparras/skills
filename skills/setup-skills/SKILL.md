---
name: setup-skills
description: "Set a repo up for these skills: create its labels, set the model roles, and install or update the factory. Use when a person starts using these skills in a repo, a skill reports that the factory is missing or stale, or a person wants to change the model roles."
disable-model-invocation: true
---

# Setup Skills

For model setup alone, go straight to [Configure model roles](model-roles.md#configure-model-roles).

Otherwise set this repo up: its labels, the model roles, and the factory, which ships the work. Nothing is written into the repo itself.

## 1. Check the repo

The skills keep issues on GitHub, through the `gh` CLI. `git remote -v` shows whether this repo is there. With no GitHub remote, get the repo URL from the user and wire it up: `git init` if needed, then `git remote add origin <url>`. Done when `gh repo view` prints the project from inside this directory. If it cannot, stop and say what is missing.

A repo that an earlier version of this skill set up holds `docs/agents/` and an `## Agent skills` block in `AGENTS.md`. Nothing reads them now, so offer to remove them.

## 2. Create the labels

Create each label that [tracker.md](factory/tracker.md#labels) names and the repo lacks, with `gh label create`. `gh label list` shows what exists.

## 3. Set model roles

Follow [Configure model roles](model-roles.md#configure-model-roles).

## 4. Install the factory

The [factory](factory/factory.md) is the T3 Code workflow that ships the work: it starts a worker for each issue labelled `ready-for-agent`, and asks the user before every merge. Nothing ships without it.

If `t3 workflow list` fails, workflows are off. Say that **Settings → Labs → Workflows** turns them on, and that this section runs again with `/setup-skills`. Skip it for now.

Otherwise follow [Install](factory/factory.md#install): copy the file, then register this repo. Fill `worker` and `reviewer` from the roles you just set, resolved as [Resolve a role](model-roles.md#resolve-a-role) says, and leave them out when no roles are set. Show the user the settings before you write them, and finish with the dispatcher check.

On a repo that is already registered, copy the file again when it differs from the installed one, and leave the settings as they are unless the user wants one changed.

## Report

Tell the user which labels you created, which roles are set, and whether the factory is installed and current.
