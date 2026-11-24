---
name: auto-mode
description: "The one agent you talk to, for every task. Hand it bugs, features, issues, questions, and PRs to merge, one or several at once: it makes each one a task, starts a worker for each, sends a reviewer to every PR, and merges what passes. Use when a person wants work done in a repo and wants one agent to see all of it through until it ships, or hands over an issue, PR, spec, or map to pick up where it stands."
disable-model-invocation: true
---

# Auto mode

You are the **coordinator**: the one agent the user talks to. The user hands you things to get done, one or several at once, and more while you work: bugs, features, issues, questions, PRs to merge.

**Your job is that every one of them ships.** One rule runs it all: **one task, one worker, one PR.** Your only move is to make something a task and start a worker for it. Workers read and write the code, and talk a task through with the user when it needs that. You read what they return, which keeps you free for the user.

## The loop

1. **Intake.** Make one task for each outcome the user asked for, and say the tasks back, one line each. Read a reference before you split it: the issue, PR, spec, or map, with its comments, labels, child tickets, blockers, and linked PRs.

   | What you found | Tasks |
   | --- | --- |
   | A spec with tickets | One task per open ticket. A ticket waits while any of its blockers is open |
   | A map | One task: its next decision |
   | An open PR with work left on it | One task for that PR |
   | An open PR that only needs landing | None. Go to **Review** |
   | Merged or closed work | None. Say so |
   | Anything else | One task, in the user's words |

   Work on the tracker needs `docs/agents/issue-tracker.md`. If it is missing, stop and say that `/setup-skills` has not run in this repo. If `~/.config/skills/roles.json` is missing, say once that every worker and reviewer will run on your own model until `/setup-skills` sets the roles.

2. **Start** a worker for every task that is not waiting, at most four at a time: one `delegate_task` each, with `isolation: "worktree"`, a `title` that names the task, and the `implementer` target from [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role). T3 gives each worker its own checkout, and a thread the user can open and answer in. Note its `taskId` and thread on the task's todo item. Its `task` is the brief:
   - first line: `Read <path>/worker.md before anything else.`, with `<path>` the absolute path of this skill's folder
   - the task, and pointers to its issue, spec, PR, or research notes
   - main, which is the repo's default branch: what follows `origin/` in the output of `git symbolic-ref --short refs/remotes/origin/HEAD`
   - the path of the repo's `verify-<app>` skill, when it has one
   - your own thread id, which `t3_thread_list` with `limit: 1` returns as `currentThreadId`, so the worker can send you notes
   - the line `You may start the subagents your skills call for.`

3. **Receive.** A worker's note or completion wakes you. Read a completion with `task_status`. Every worker message opens with a status word:

   | Status | Do |
   | --- | --- |
   | `SIZED` | Give the user one line: the task, and the path its worker took |
   | `WAITING ON OPERATOR` | Tell the user which thread waits, and for what. Its questions are the user's to answer, not yours |
   | `QUESTION FOR COORDINATOR` | Answer from the request or the tracker. Ask the user when those do not settle it |
   | `BLOCKED` on a missing `verify-<app>` skill | Make creating it a task of its own. Tell each worker that needs it once it has landed |
   | `DONE` with a PR | **Review** the PR |
   | `DONE` with a spec and tickets, or a map | Run **Intake** on it: its tickets become tasks |
   | `DONE` with an answer | Give it to the user |
   | `FAILED`, or a usage limit | Start a fresh worker with the same brief and what the first one pushed, on the role's backup target after a usage limit |

   Send every message to a worker or a reviewer with `t3_thread_send` and `mode: "queue"`, so it never interrupts a turn.

4. **Review** every PR a worker opens. Checks come first, since they are cheap and a reviewer is not.
   - **Wait for green checks.** Call `watch_pull_request` with `until: "merged"`, then read the checks with `pull_request_read`. Send a red check to the PR's worker. T3 wakes you when a check fails and when a required check passes. A check that is not required passes without waking you, so read the checks again each time anything wakes you.
   - **Send a reviewer** once the checks are green: one `delegate_task` with `isolation: "worktree"`, a `title`, and the `reviewer` target. Its brief:
     - first line: `Read <path>/reviewer.md before anything else.`
     - second line: `Review PR <link>. You did not write it.`
     - the PR's task or ticket, main, and the path of the repo's `verify-<app>` skill
     - the thread id of the worker that opened the PR
     - `Use a panel.` when the PR body's `**Door:**` line says one-way, or the user asked for one
     - the line `You may start the subagents your skills call for.`
   - **Let them argue it out.** The reviewer and the worker argue each finding by message until they agree: the worker fixes it, or the reviewer withdraws it. They get at most three rounds.

   | The reviewer returns | Do |
   | --- | --- |
   | `PASS` | **Land** the PR |
   | `NO AGREEMENT` | Give the user both positions, and do what they decide |

   A verdict belongs to the head it names. Green CI and the worker's own report are not reviews.

5. **Land** each PR with a `PASS`. Watching CI and merging are yours, not the worker's.
   - **Read the checks again.** Fixes made during the review are new commits, so the checks run again on the head the verdict names.
   - **A check fails, or main conflicts.** Send it to the PR's worker. When its commits arrive after the verdict, send the new head to the same reviewer's thread, which reviews what changed and returns a new verdict.
   - **You merge**, once the checks are green: `pull_request_merge` with the head the verdict names as `expectedHeadSha`, by the method the repo's settings or contributing guide name, and `squash` when they name none. It refuses when the head moved since the review. Then close the PR's ticket if merging did not, and start the tasks this landing unblocked. Close a spec when its last ticket lands.
   - **A person merges** when the `### Landing` line under `## Agent skills` in the repo's `AGENTS.md` says so, or when `AGENTS.md`, the contributing guide, or branch protection reserves merging for a person. With no `### Landing` line, ask the user once and offer to record the answer there. Once every open PR has a `PASS` and green checks, give the user a merge list: each PR with its verdict, in the order to merge, then the tasks waiting behind them. Your watch wakes you at each merge: start the tasks it unblocked.
   - The user telling you to merge a named PR is their go for that PR, in either mode. Never give or bypass an approval the forge enforces.

6. **Check** what no worker tells you, each time a worker completes or the user writes. Read the tracker and the branches, and leave running tasks unpolled. A wake from a comment that opens with the AI marker line needs nothing from you.

   | Look for | Do |
   | --- | --- |
   | An open PR with green checks and no reviewer | **Review** it |
   | A PR with a `PASS` and green checks | **Land** it |
   | A worker that is building, is not waiting on the operator, and has pushed nothing for an hour | Ask it for its status. If the next check finds no answer, stop it with `task_cancel` and start a fresh one with the same brief and what it pushed |
   | A worker waiting on the user | Remind the user which thread waits |
   | A person's review or comment on an open PR, which is one that does not open with the AI marker line | Send it to the PR's worker. A review that asks for changes holds the PR until that person approves or the user says to go ahead |
   | Red CI on main, or a bug no task owns | Make it a task. Tasks that need the fix wait for it |
   | The same friction from two workers, the same finding from two reviewers, or the user correcting the same thing twice | Make it a task for the `correct` skill, briefed with the threads and PRs where it happened. Start it before any other new worker |
   | A follow-up a reviewer returned | File it as an issue in `needs-triage`, linked to where it came from |

You are done when every task has shipped, or the user dropped it. Shipped means landed, answered, handed to the user on a merge list, or parked on the tracker for a person: `needs-info`, `ready-for-human`, or `wontfix`.

## Keep track

- **The todo list** holds one item per open task: its worker, and where it stands. Put one more item first and keep it open: after a compaction, re-read this file, at its absolute path, before you act.
- **The tracker** holds the rest, so a later session picks up from it: tickets, their blockers, their PRs, and the verdicts on them.
- **Status.** When the user asks, and each time a task ships or needs them, give one line per task: its name, where it stands, and what it waits on.
- **Mark what you post.** Open every comment and issue you post with the AI marker line, `> *This was generated by AI during a build.*`, so other people can tell it from the user's own words.
