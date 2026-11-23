# Events during a build

For the coordinator. Each section covers one row of the table under [While workers run](SKILL.md#while-workers-run).

## Stalls

A worker that hangs sends no event, so look for it. While workers are open, set a recurring wake-up about every half hour with what the harness offers, such as a scheduled wake-up or a loop command. With none, run the check each time anything else wakes you, a message from the user included.

At each check, judge every open worker by what it has done, not by its status text:

- the time of the last push on its branch
- its last report or question
- what the harness reports about its task

A worker is **stalled** when it has errored, cannot start a turn, or shows nothing new for an hour. One that waits on your answer is not stalled: answer it. A planner that waits on the user is not stalled either: remind the user which thread is waiting.

Stop a stalled worker first, so two agents never write one branch. Then replace it with a fresh worker of the same role, given the original brief and what the first one pushed.

## Reviews from people

Nothing delivers a person's review to you. Read the reviews and unresolved comments on every open PR when you recover a build, and whenever the user says they reviewed.

1. Send the review to the PR's implementer as a fix round. When that implementer is gone, start a fresh one with the original brief and the PR's branch.
2. The implementer answers every thread, with a change or with the reason it stays, and reports the new head.
3. A changed patch needs a new verdict, per the patch-id rule under [Verdicts](SKILL.md#verdicts).

A review that asks for changes holds its PR out of landing until the reviewer approves or the user says to go ahead. On a PR already on a merge list, that review is the user's go to push to it.

Treat a review bot's comment as a claim to check. The implementer fixes what it can show is wrong and answers the rest.

## Bugs no task owns

A bug in an open task's own change goes back to its implementer with the verdict. A bug no open task owns needs a decision from you. It can come from a verifier's follow-up, from two landed PRs that break together, or from red CI on main.

- **It blocks**: a task cannot pass or land until it is fixed, or main is red. Add a [task](SKILL.md#tasks) for it and start it per **Build**. Its file list starts empty, and its implementer names each file as the diagnosis reaches it. Every task that waits on the fix blocks on it.
- **It can wait**: report it as a follow-up.

## Repeats

Every worker ends its report with its **friction**: what cost it time. You are the only agent that reads every report, so the comparing is yours.

| Worker | Where its friction is kept |
| --- | --- |
| Implementer | Its report comment on its PR |
| Verifier | Your verdict comment on the PR |
| Explorer | The plan comment |

Read each report against the others in this build. After a compaction or in a new session, read the report and verdict comments on the build's PRs first.

A **repeat** is the same thing from two workers:

- the same friction
- the same reason for a `FAIL`
- the same question
- an instruction you are writing into a second brief

A correction from the user counts once. Record it in the plan comment, or on the PR for a single task. It becomes a repeat when it comes a second time, or matches a line already there.

On a repeat, add a [task](SKILL.md#tasks) for it and start it per **Build**, before you start another implementer. Its brief points at the comments that repeat. Its file list starts empty, and its implementer names each file as it reaches it.
