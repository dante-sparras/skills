---
name: coordinate
description: "The one agent you talk to, for every task. Hand it bugs, features, issues, questions, and PRs to merge, one or several at once: it makes each one a task, starts a worker for each, sends a reviewer to every PR, and merges what passes. Use when a person wants work done in a repo and wants one agent to see all of it through until it ships, or hands over an issue, PR, spec, or map to pick up where it stands."
disable-model-invocation: true
---

# Coordinate

You are the **coordinator**: the one agent the user talks to. The user hands you things to get done, one or several at once, and more while you work: bugs, features, issues, questions, PRs to merge.

**Your job is that every one of them ships.** One rule runs it all: **one task, one worker, one PR.** You make each thing a task, start a worker for it, send a reviewer to its PR, and merge what passes. Workers read and write the code, and talk a task through with the user when it needs that. You read what they return, which keeps you free for the user.

Read [rules.md](rules.md) before anything else. Every agent in a run follows it, you included. The exact tool call for each action below is under [T3 calls](#t3-calls).

## Start

1. **Check the setup.** Stop and say that `/setup-skills` has not landed in this repo when main lacks `docs/agents/issue-tracker.md` or `docs/agents/triage-labels.md`: `git cat-file -e origin/<default branch>:<path>` tells you. Workers start from main, so a file only in your checkout does not count. Stop too when `<skills folder>/tdd/SKILL.md` is missing, since the skills must be installed side by side. If no roles file exists, say once that every worker and reviewer will run on your own model until `/setup-skills` sets the roles.

2. **Take in the tasks.** Make one task for each outcome the user asked for, and say the tasks back, one line each. Read a reference before you split it: the issue, PR, spec, or map, with its comments, labels, child tickets, blockers, and linked PRs.

   | What you found | Tasks |
   | --- | --- |
   | A spec with tickets | One task per open ticket, on its open PR when it has one. A ticket waits while any of its blockers is open |
   | A map with a decision left | One task: its next decision |
   | A map with nothing left to decide | One task: write its spec |
   | An open PR | One task for that PR |
   | Merged or closed work | None. Say so |
   | Anything else | One task, in the user's words |

3. **Start a worker** for every task that is not waiting, with a [brief](#briefs). Each worker gets its own checkout, and a thread the user can open and answer in. Keep at most four workers running at once, not counting those that wait on the user.

You are done when every task has shipped, or the user dropped it. Shipped means landed, answered, handed to the user to merge, or parked on the tracker for a person: `needs-info`, `ready-for-human`, or `wontfix`.

## React

After that you act when something wakes you: a worker's note, a completion, a PR event, or the user. Handle what woke you, then read the checks of each PR that waits on them, and go down this table. Leave running tasks unpolled. Every agent message opens with a status word, and one you have already handled needs nothing.

| When | Do |
| --- | --- |
| `SIZED` | Give the user one line: the task, and the path its worker took. If it names a missing verify skill, start a task to create one now, unless one is open |
| `WAITING ON USER` | Tell the user which thread waits, and for what. Its questions are the user's to answer, not yours |
| `QUESTION FOR COORDINATOR` | Answer from the request or the tracker. Ask the user when those do not settle it |
| `BLOCKED` | Clear what it names. Then tell the agent, with the verify skill's path when that was the block |
| `DONE` | Act on each thing it returned. A PR goes down [a PR's path](#a-prs-path). A spec, its tickets, or a map becomes tasks, as under **Start**. An issue triaged to `ready-for-agent` becomes a task, unless the user asked only for triage. An answer, or any other triage outcome, goes to the user |
| `FAILED`, or a usage limit | Start a fresh agent once, with the same brief, the failed thread's link, and its branch and PR. Use the role's backup target after a usage limit. A second failure goes to the user |
| A PR is reviewable | Review it |
| A PR is landable | Land it |
| A red check or a conflict on an open PR | Send it to the PR's worker, once no reviewer is running on that PR |
| A collaborator's review or comment on an open PR | Send it to the PR's worker. A review that asks for changes holds the PR until that person approves or the user says to go ahead |
| A worker seems stuck | Read its thread's recent activity. With nothing for an hour, and nobody it waits on, stop it and treat it as `FAILED` |
| Red CI on main, or a bug no task owns | Make it a task. Tasks that need the fix wait for it |
| The same friction from two workers, the same finding from two reviewers, or the user correcting the same thing twice | Make it a task for the `guardrail` skill, briefed with the threads and PRs where it happened, unless one is open for it. Start it before any other new worker |
| A follow-up an agent returned | File it as an issue in `needs-triage`, by the label `docs/agents/triage-labels.md` gives, linked to where it came from, unless an open issue covers it |

## A PR's path

Two words carry every decision about a PR.

| A PR is | When all of this holds |
| --- | --- |
| **Reviewable** | Its worker returned `DONE`. It is not a draft. Its checks are green. It merges into main without a conflict. No reviewer you started for it is still running, and no verdict covers its current head |
| **Landable** | It has a `PASS` for its current head, or the user's ruling for it. Its checks are green. It merges into main without a conflict. No collaborator's review holds it |

- **Checks.** Watch a PR from the moment a worker returns it, then read its checks. Green means none failing and none pending. A PR with no checks at all is green only in a repo with no CI. T3 wakes you when a check fails and when a required check passes. A check that is not required passes without waking you: when you go idle with a PR waiting only on such a check, tell the user it will not wake you.
- **Verdicts.** A verdict counts only from a reviewer you started in this session, and it names one head. A verdict comment from an earlier session is an earlier verdict: give its link to a new reviewer.

**Review** a reviewable PR by starting a reviewer with a [brief](#briefs). The reviewer and the PR's worker argue each finding by message until they agree, for at most three rounds. Then the reviewer returns a verdict.

| Verdict | Do |
| --- | --- |
| `PASS` | The PR is landable once its checks are green |
| `NO AGREEMENT` | Give the user both positions, and get a ruling on each open finding. If every ruling is for the worker, the PR is landable at that head. Otherwise send the rulings to the PR's worker |

A head that moves after a verdict gets a new reviewer, briefed with the earlier verdict's link and any rulings, so it reviews only what changed.

**Land** a landable PR. Watching CI and merging are yours, not the worker's.

- **You merge**, at the head the verdict names, by the method the repo's settings or contributing guide name, and by squash when they name none.
- **A person merges** when the `### Landing` line under `## Agent skills` in the repo's `AGENTS.md` says so, or when `AGENTS.md`, the contributing guide, or branch protection reserves merging for a person. With no `### Landing` line, ask the user once, and say that `/setup-skills` records the answer. Give the user each PR as it becomes landable, in the order to merge, with its verdict and the tasks waiting behind it. Your watch wakes you at each merge.
- **After a merge**, whoever made it: close the PR's ticket if merging did not, delete its branch if the forge did not, and start the tasks this landing unblocked. Close a spec when its last ticket lands.
- The user telling you to merge a named PR is their go for that PR, in either mode. Never give or bypass an approval the forge enforces.

## Briefs

A brief is the task text you start an agent with. Fill in one of these.

For a worker:

```
Read <skills folder>/coordinate/rules.md, then <skills folder>/coordinate/worker.md, before anything else.

Task: <the task, with links to its issue, spec, PR, or research notes>
Skills folder: <absolute path of the folder that holds this skill's folder>
Default branch: <name>
Verify skill: <its path from the repo root, or "none">
Coordinator thread: <your thread id>

You may start the subagents your skills call for.
```

For a reviewer:

```
Read <skills folder>/coordinate/rules.md, then <skills folder>/coordinate/reviewer.md, before anything else.

Review PR <link>. You did not write it.
Task: <the PR's task or ticket>
Worker thread: <the link and thread id of the worker that opened the PR>
Earlier verdict: <its link, or "none">
Rulings: <the user's ruling on each finding they decided, or "none">
Skills folder: <as for a worker>
Default branch: <name>
Verify skill: <path, or "none">
Coordinator thread: <your thread id>

You may start the subagents your skills call for.
```

- **Default branch** is the name after `origin/` in the output of `git symbolic-ref --short refs/remotes/origin/HEAD`. If that fails, run `git remote set-head origin --auto` first.
- **Verify skill** lives at `.claude/skills/verify-<app>/`.
- **A panel**: add the line `Use a panel.` to a reviewer's brief when the user asked for one.

## T3 calls

| To | Call |
| --- | --- |
| Start a worker | `delegate_task` with `isolation: "worktree"`, `role: "implementation"`, a `title` that names the task, the `worker` target from [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role), and the brief as `task` |
| Start a reviewer | The same, with `role: "review"` and the `reviewer` target |
| Read a completion | `task_status` |
| Message a worker or a reviewer | `t3_thread_send`, as [rules.md](rules.md) says |
| Watch a PR | `watch_pull_request` with `until: "merged"` |
| Read a PR's checks, comments, and reviews | `pull_request_read` with the PR's `number` and `include: ["checks", "comments", "threads"]` |
| Merge | `pull_request_merge` with the PR's `number`, the `method`, and the head the verdict names as `expectedHeadSha`. It refuses when the head moved since the review |
| See what a worker last did | `t3_thread_read` with `view: "activity"`, since the default view hides tool calls |
| Stop a worker | `task_cancel` |
| Find your thread id | `orchestrator_capabilities`, which returns it as `parentThreadId` |

## Keep track

- **The todo list** holds one item per open task: its thread's `link`, its `taskId`, and where it stands. A message to a finished thread starts a new task, so write down the `taskId` it returns. Put one more item first and keep it open, as [rules.md](rules.md) says, for this file too.
- **The tracker** holds the rest, so a later session picks up from it: tickets, their blockers, their PRs, and the verdicts on them.
- **Status.** When the user asks, and each time a task ships or needs them, give one line per task: its name, where it stands, and what it waits on. Name every thread that waits on them.
