# Skills

Agent skills that plan, build, test, review, and land work in a repository.

## Coordination

**Operator**:
The person a run works for. Skills written for a conversation call this person the user, and `triage` calls them the maintainer.
_Avoid_: Owner, end user

**Coordinator**:
The one agent the operator talks to. It takes every task the operator hands it, starts the workers for each, and makes sure each one ships. It owns the verdict on each head and the landing order, and it is the only agent that merges.
_Avoid_: Orchestrator, main agent

**Worker**:
A fresh agent the coordinator starts with one job and a brief that opens with `implement/worker.md`. There are four: planner, implementer, verifier, and explorer.
_Avoid_: Helper, child

**Planner**:
The worker that settles one task with the operator, who answers in the planner's own thread: an interview, a spec and its tickets, a map, or a triage.
_Avoid_: Interviewer, sub-coordinator

**Implementer**:
The worker that builds one task and carries its PR from the first commit until it lands.
_Avoid_: Owner, author

**Verifier**:
The worker that checks one head it did not write and returns `PASS` or `FAIL`. It runs on the `reviewer` model role.
_Avoid_: Reviewer, checker, QA agent

**Explorer**:
The worker that researches the code or the docs when a build's tickets need it.
_Avoid_: Researcher, scout

**Task**:
What one implementer builds, landing through one PR: one ticket, several tickets that share a file, or a job the coordinator adds.
_Avoid_: Unit, job

**Plan comment**:
The one comment a coordinator keeps on a spec's issue, holding the build's tasks, the files each may touch, what blocks what, and the landing mode.
_Avoid_: Ledger, status comment

**Verdict comment**:
The comment a coordinator posts on a PR for each verdict: `PASS` or `FAIL`, the head SHA, the patch-id, and the findings.
_Avoid_: Review, approval

**Friction**:
What cost a worker time during its task, reported as facts at the end of its report and kept on the PR.
_Avoid_: Mistake log, complaints

**Repeat**:
The same friction, failure reason, or question from two workers, or one correction from the operator. A repeat starts a `correct` task.
_Avoid_: Pattern, recurring issue

**Playbook**:
A short list of steps in `auto-mode/playbooks/` that names the skills one size of task runs through.
_Avoid_: Mode, workflow, lane

## Verification

**Verification skill**:
A project-local skill, named `verify-<app>`, that launches the real app, drives it the way a user does, and captures evidence. The `create-verification-skill` skill generates one.
_Avoid_: Control skill, verify script, e2e harness

**Feature map**:
The `features/` folder of a verification skill: an index plus one file per user-facing feature, saying how to reach it, how to drive it, and what end state proves it works.
_Avoid_: Test plan, feature list

**Doctor**:
The read-only check in a verification skill that answers whether a running instance is worth driving.
_Avoid_: Health check, preflight

**Evidence**:
What a verification run captures to prove behavior: the action and the resulting state, such as screenshots, transcripts, response bodies, exit codes, and side effects. It survives cleanup.
_Avoid_: Artifacts, output
