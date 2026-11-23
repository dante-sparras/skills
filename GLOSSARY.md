# Skills

Agent skills that plan, build, test, review, and land work in a repository.

## Coordination

**Operator**:
The person a run works for. Skills written for a conversation call this person the user, and `triage` calls them the maintainer.
_Avoid_: Owner, end user

**Coordinator**:
The one agent the operator talks to. It makes everything the operator asks for a task, starts a worker for each, and makes sure each one ships. It sends a reviewer to every PR once its checks are green, and it is the only agent that watches CI and merges.
_Avoid_: Orchestrator, main agent

**Task**:
One outcome the operator asked for, or one ticket. One worker carries it, and it lands through one PR when it changes code.
_Avoid_: Unit, job

**Worker**:
A fresh agent the coordinator starts with one task and a brief that opens with `auto-mode/worker.md`. It sizes the task, then opens a PR for it or splits it into tickets, and fixes what review finds. The operator answers it in its own thread.
_Avoid_: Helper, child, implementer, planner

**Reviewer**:
The agent the coordinator sends to one PR it did not write. It proves the behavior, runs `code-review`, and argues each finding with the PR's worker by message until they agree: the worker fixes it, or the reviewer withdraws it. Then it posts `PASS` or `NO AGREEMENT` on the PR. It runs on the `reviewer` model role.
_Avoid_: Verifier, checker, QA agent

**Verdict comment**:
The comment a reviewer posts on a PR once it and the worker are done: `PASS` or `NO AGREEMENT`, the head SHA, and whether each finding was fixed or withdrawn.
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
