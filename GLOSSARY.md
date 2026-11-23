# Skills

Agent skills that plan, build, test, review, and land work in a repository.

## Coordination

**Operator**:
The person a run works for. Skills written for a conversation call this person the user, and `triage` calls them the maintainer.
_Avoid_: Owner, end user

**Coordinator**:
The one agent the operator talks to. It makes everything the operator asks for a task, starts a worker for each, and makes sure each one ships. It is the only agent that merges.
_Avoid_: Orchestrator, main agent

**Task**:
One outcome the operator asked for, or one ticket. One worker carries it, and it lands through one PR when it changes code.
_Avoid_: Unit, job

**Worker**:
A fresh agent the coordinator starts with one task and a brief that opens with `auto-mode/worker.md`. It sizes the task, then builds it or splits it into tickets. The operator answers it in its own thread.
_Avoid_: Helper, child, implementer, planner

**Verifier**:
The agent that checks one head it did not write and posts `PASS` or `FAIL` on the PR. It runs on the `reviewer` model role.
_Avoid_: Reviewer, checker, QA agent

**Verdict comment**:
The comment a verifier posts on a PR: `PASS` or `FAIL`, the head SHA, and the findings.
_Avoid_: Review, approval

**Friction**:
What cost a worker time during its task, returned as facts at the end of its report and kept on the PR.
_Avoid_: Mistake log, complaints

**Repeat**:
The same friction or failure reason from two workers, or the same correction from the operator twice. A repeat becomes a task for the `correct` skill.
_Avoid_: Pattern, recurring issue

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
