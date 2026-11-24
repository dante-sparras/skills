---
name: triage
description: "Move issues and external PRs through a state machine of triage roles. Use when a person asks what on the tracker needs attention, wants a specific issue or PR triaged, or wants one moved to a state such as ready-for-agent."
disable-model-invocation: true
---

# Triage

Move issues on the tracker through a small state machine of triage roles. The user says what they want in plain words: "show me what needs attention", "let's look at #42", "move #42 to ready-for-agent", "what's ready for agents?".

[tracker.md](../setup-skills/factory/tracker.md) has the tracker's commands. Open every comment and issue you post with the AI marker it gives.

**PRs.** Triage covers a PR when the user names one, or asks for the external PRs. A PR is an issue with attached code: same roles, same states. Resolve a bare `#42` to an issue or a PR as tracker.md says.

## Roles

Every triaged issue carries one category and one state.

| Category | Meaning |
| --- | --- |
| `bug` | Something is broken |
| `enhancement` | A new feature or an improvement |

| State | Meaning | For a PR |
| --- | --- | --- |
| `needs-triage` | The user needs to evaluate it | The same |
| `needs-info` | Waiting on the reporter | The same |
| `ready-for-agent` | Fully specified, and an agent can take it | A brief is attached, and an agent takes the next step on the diff |
| `ready-for-human` | Needs a person to implement it | Ready for a person to merge |
| `wontfix` | Will not be actioned | The same |

An unlabeled issue goes to `needs-triage` first, and from there to any other state. `needs-info` returns to `needs-triage` when the reporter replies. The user can override at any time. When two state roles conflict, or a transition looks unusual, flag it and ask before you act.

## Show what needs attention

Query the tracker and present three buckets, oldest first, with a count and one line per item. The user picks.

1. **Unlabeled**: never triaged.
2. **`needs-triage`**: evaluation in progress. An issue the factory stopped on lands here too, with a comment that says why.
3. **`needs-info` with reporter activity since the last triage notes**: needs another look.

When the user asks for PRs too, include the external ones, listed as tracker.md says, and tag each line `[PR]` or `[issue]`. A collaborator's PR is left out of these buckets, and is still triaged when the user names it.

## Show what is ready

The factory starts each `ready-for-agent` issue within ten minutes of its last blocker closing, and `t3 workflow list` shows what it runs. List the rest of the queue: the `ready-for-agent` issues with an open blocker, per tracker.md's count of open blockers, grouped under their spec, each with what blocks it.

## Work that is not on the tracker yet

Triage starts from an issue or a PR. When the user describes something new, send them on: a bug goes to `/debug`, which reproduces and files it, a change that fits one PR goes to `/ticket`, and a feature goes to `/spec`.

## Triage one issue or PR

1. **Gather.** Read all of it: body, comments, labels, author, dates, and the diff for a PR. If earlier triage notes exist, check which questions the reporter has answered, and treat settled questions as settled. Then check the codebase, in the glossary's vocabulary:
   - **Already built?** Search for the requested behavior by domain concept, not by the request's wording, and say where you looked.
   - **Already rejected?** Search the closed `wontfix` issues for the same request, and surface any match with the reason it was given.

2. **Recommend** a category and a state, with your reasons and what the code showed. Wait for the user's direction.

3. **Verify the claim** before any interview. Reproduce a bug from the reporter's steps. For a PR, read the diff first. Check it out and run its tests only when the user says to, since an outside contributor's code would run with your access. Report one of three results: confirmed (with the code path), failed, or too little detail to tell, which points to `needs-info`. Keep the exact steps or command and their output, since the brief carries them to the agent that builds the fix.

4. **Interview** when the request needs fleshing out: read [interview](../interview/SKILL.md) and follow it.

5. **Apply** the state.

   | State | Do |
   | --- | --- |
   | `ready-for-agent` | Post an agent brief, per [agent-brief.md](../setup-skills/factory/agent-brief.md), and follow [handoff.md](../setup-skills/factory/handoff.md). Only work that fits one PR gets this state: anything bigger becomes a spec and its tickets, so read [spec](../spec/SKILL.md) and follow it, then [ticket](../ticket/SKILL.md). The factory starts from issues, so a PR gets an issue of its own that carries the brief and names the PR, and a worker continues the PR's branch |
   | `ready-for-human` | Post a brief of the same shape, and say why it cannot be delegated: a judgment call, external access, a design decision, manual testing |
   | `needs-info` | Post triage notes from the template below |
   | `needs-triage` | Apply the role, and comment when there is partial progress to keep |
   | `wontfix`, already built | Close with a comment that points to where the behavior lives |
   | `wontfix`, rejected | Close with a polite comment that gives the decision and its reason, so a later request for the same thing finds it |

6. **Hand off.** Tell the user what happens next. For `ready-for-agent`, say that the factory starts it within ten minutes of its last blocker closing. For `needs-info`, say that the issue returns to `needs-triage` when the reporter replies.

## Quick state override

When the user says "move #42 to ready-for-agent", trust them. Say what you are about to do (role changes, comment, close), then do it, with no interview. For a move to `ready-for-agent` with no interview behind it, ask whether they want an agent brief written.

## Needs-info template

```markdown
## Triage Notes

**What we've established so far:**

- point 1
- point 2

**What we still need from you (@reporter):**

- question 1
- question 2
```

Put everything the interview settled under "established so far", so the work is kept. Make each question specific enough to answer in one reply.
