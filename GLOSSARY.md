# Skills

Agent skills that plan, build, test, review, and land work in a repository.

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
