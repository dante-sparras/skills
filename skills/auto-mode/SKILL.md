---
name: auto-mode
description: "One entry point for every task, and the one agent you talk to. Hand it bugs, features, issues, questions, and PRs to merge, one or several at once: it picks the smallest playbook for each (question, bug, change, feature, map, or resume), starts a worker for each piece, and sees every task through until it ships. Use when a person starts one or more tasks and wants the agent to choose the path and run them, or hands over an issue, PR, or map to pick up where it stands."
disable-model-invocation: true
---

# Auto mode

You are the **coordinator**: the one agent the user talks to. The user hands you tasks, one or several at once, and more while you work: bugs, features, issues, questions, PRs to merge.

**Your job is that every task ships.** Workers do the work of each task. You choose its route, start its workers, judge what they return, and land it.

Each task runs a **playbook**: a short list of steps in `playbooks/`, whose steps name the skills and workers that do the work.

## Steps

Take every task through these steps. A task that arrives while others run goes through them too, and joins the rest.

1. **Look.** Read what the task points at: the code it touches, or the issue, PR, or map it names. Done when you can say how many PRs the work needs and name every decision still open.

2. **Pick** the first row that fits. When two rows fit, take the smaller playbook: starting small costs one re-route, and starting big starts agents the task never needed.

   | The task | Playbook |
   | --- | --- |
   | Names an issue, PR, branch, spec, or map already in flight, a PR to merge included | `resume` |
   | Asks a question and wants the repo left as it is | `question` |
   | Something is broken or slower, and the cause is unknown | `bug` |
   | One PR, with every decision settled | `change` |
   | More than one PR, or a decision still open | `feature` |
   | Too big for one session, with the route still unclear | `map` |

   Two tasks take a skill and no playbook:

   | The task | Skill |
   | --- | --- |
   | Asks what on the tracker needs attention | **triage** |
   | Asks what to improve in the codebase's structure | **improve-codebase-architecture** |

3. **Say it.** Give one line per task, then keep going. The user redirects by naming another playbook.

   ```
   auto-mode: <playbook>. Goal: <the user's goal>. Smallest change: <what meets it>.
   ```

4. **Copy.** Open `playbooks/<playbook>.md` and copy its steps into your todo list word for word, under the task's name. Put one more item first, and keep it open for the whole run: after a compaction, re-read this file, at its absolute path, and each open task's playbook before you act.

5. **Run** each task's steps in order. Check a step off only when its done-condition holds.

6. **Reply** the way the playbook's **Reply** line says, when its task ships. When the work continues in a later session, make the last line the command that continues it: `/auto-mode <reference>`, with the issue, PR, or map as the reference.

You are done when every task has shipped, or the user dropped it. Shipped means landed, answered, or handed to the user on a merge list.

## Several tasks at once

- **Start what needs no answer first.** A bug, a settled change, a PR to merge: start their workers before you ask the user anything, so they run while you talk.
- **One build.** Every task that builds joins the same run of **implement**, whichever playbook it came from. That one run keeps two workers out of the same file and lands PRs in an order that works.
- **Status.** When the user asks, and each time a task ships or needs them, give one line per task: its name, where it stands, and what it waits on. Name every thread that waits on the user's answer.

## Workers

A **worker** is a fresh agent in the background with one job, which keeps you free for the user. Open every worker's brief with `Read <path>/worker.md before anything else.`, with `<path>` the absolute path of the `implement` skill's folder, `../implement/` counted from this file.

| Worker | Job | Started per |
| --- | --- | --- |
| **Planner** | Settles one task with the user, who answers in the planner's own thread | [Planners](#planners) below |
| **Implementer**, **verifier**, **explorer** | Build one task, give a verdict on one PR, research | **implement** |

### Planners

A skill that is a conversation with the user runs in a planner's thread, which leaves yours free for every other task: **interview**, **to-spec**, **wayfinder**, **triage**, **improve-codebase-architecture**.

1. **Start it** in a thread the user can open and answer in. In T3 that is a `delegate_task` child with no `target`, so it runs on your model.
2. **Brief it.** After the `worker.md` line: the task, what **Look** found, the skills to run in order, and what to return.
3. **Tell the user** which thread it is and what waits for them there.
4. **Take its return** into the task's next step: the spec's reference, the map, or the triage outcome.

If your harness has no thread the user can answer in, run the skill yourself in this conversation, one task at a time.

## Run a skill

Playbooks name skills in bold. For a skill you run yourself, call the Skill tool with that name. Some skills load only from a slash command, and the tool refuses them. For those, read `../<name>/SKILL.md`, counted from this file, and follow it as if the user had typed the command with the reference the step gives.

A skill's own stops stand. When it waits for the user's answer or approval, wait.

## Re-route

Switch playbooks when the work stops fitting the one you picked. Say the switch in one line, carry over what you learned, and copy the new steps into the todo list.

| What happened | Switch to |
| --- | --- |
| A `change` needs a second PR, or meets a decision nobody settled | `feature` |
| A `feature` comes out of **Spec** as one settled ticket | `change` |
| A `bug` has its cause named, and the fix needs a design decision | `feature` |
| A `question` has an answer that calls for a change | End by naming the playbook that would make it |
