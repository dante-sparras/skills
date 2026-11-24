---
name: factory
description: "Set up and run the factory, the T3 Code workflow that ships issues labelled ready-for-agent: a repo's labels, the model roles, the workflow's install, and its runs. Use when a person starts using these skills in a repo, a skill reports that the factory is missing or stale, or a person asks what the factory is doing."
disable-model-invocation: true
---

# Factory

The [factory](factory.md) ships the work: it starts a worker for each issue labelled `ready-for-agent`, and asks the user before every merge. This skill sets it up and runs it. It takes in no work: the user types `/debug`, `/ticket`, `/spec`, or `/triage` for that.

- **Model setup alone**: go straight to [Configure model roles](model-roles.md#configure-model-roles).
- **A question about a run, or a request to retry, stop, or pause**: follow [Run it](factory.md#run-it).
- **Otherwise** set this repo up, with the steps below. Nothing is written into the repo itself.

## 1. Check the repo

The skills keep issues on GitHub, through the `gh` CLI. `git remote -v` shows whether this repo is there. With no GitHub remote, get the repo URL from the user and wire it up: `git init` if needed, then `git remote add origin <url>`. Done when `gh repo view` prints the project from inside this directory. If it cannot, stop and say what is missing.

A repo that an earlier version of these skills set up holds `docs/agents/` and an `## Agent skills` block in `AGENTS.md`. Nothing reads them now, so offer to remove them.

## 2. Create the labels

Create each label that [tracker.md](tracker.md#labels) names and the repo lacks, with `gh label create`. `gh label list` shows what exists.

## 3. Set model roles

Follow [Configure model roles](model-roles.md#configure-model-roles).

## 4. Install the factory

If `t3 workflow list` fails, workflows are off. Say that **Settings → Labs → Workflows** turns them on, and that this step runs again with `/factory`. Skip it for now.

Otherwise follow [Install](factory.md#install): copy the file, then register this repo. Fill `worker` and `reviewer` from the roles you just set, resolved as [Resolve a role](model-roles.md#resolve-a-role) says, and leave them out when no roles are set. Show the user the settings before you write them, and finish with the dispatcher check.

On a repo that is already registered, copy the file again when it differs from the installed one, and leave the settings as they are unless the user wants one changed.

## Report

Tell the user which labels you created, which roles are set, and whether the factory is installed and current.
