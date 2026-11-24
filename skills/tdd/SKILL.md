---
name: tdd
description: "Test-driven development, and proof for the work a test cannot cover. Use when fixing a bug, building domain rules, calculations, parsers, or state transitions, writing a regression or integration test, or when the user mentions TDD or red-green."
disable-model-invocation: true
---

# TDD

TDD is the red → green loop. This skill says when the loop runs, how to run it so the tests are worth keeping, and how to prove the work the loop skips.

Read `GLOSSARY.md`, when the repo has one, so test names and interfaces use the project's domain language.

## Test first, or prove another way

Write the test first for:

- **A bug fix.** Reproduce the bug as a failing test before you change production code.
- **Core logic.** Domain rules, calculations, parsers, state transitions, and anything else whose result a caller reads back.

Skip the new test when it is expensive or proves nothing:

- **Expensive**: it needs broad harness setup, brittle mocks, slow end-to-end infrastructure, production-only state, vague reproduction steps, or large unrelated fixture churn.
- **Proves nothing**: a test cannot judge the result, as with UI layout, or it would mostly test mocks, depend on timing or unrelated global state, or be deleted right after it proves the fix.

No new test beats a bad test. Every skip still ends in proof: see [Prove skipped work](#prove-skipped-work).

## Seams: where tests go

A **seam** is the place you test at: where a module's interface lives, and where you observe behavior without reaching inside.

**Test only at agreed seams**, which puts the effort on the critical paths and not on every edge case.

- Take the seams from the spec, ticket, or brief when it names them.
- Otherwise propose them, each with one line on what it catches and what it misses, and confirm them with the user before you write a test. A worker chooses its own seams, and states them in its PR's agent notes.
- When the interface itself is in question (how deep the module is, where the seam belongs, what it exposes), read [deepen-modules](../deepen-modules/SKILL.md) for the vocabulary.

## The loop

1. **Understand the behavior.** Name the intended behavior, the current behavior, the affected path, and the smallest observable reproduction.
2. **Choose the narrowest check at a seam.** Use the test file and harness the codebase already has for that path. If there is no practical test path, skip per [Test first, or prove another way](#test-first-or-prove-another-way).
3. **Write one failing test**, with its expected value taken from the requirement.
4. **Run it and see red**, for the intended reason. If it passes, or fails for another reason, fix the test before you touch the implementation.
5. **Write only enough code to pass.** The smallest production change that satisfies the test and keeps nearby contracts.
6. **Rerun and see green.** Then start the next slice.

Work in **vertical slices**: one seam, one test, one minimal implementation per cycle, each test a **tracer bullet** that responds to what the last cycle taught you. Writing all the tests first locks in imagined behavior.

For a bug fix in a repo that squash-merges, commit the failing test before the fix, so the PR's commits show red then green. Where commits land on main one by one, keep them in one commit and show the red run in the PR's evidence.

Refactoring stays out of the loop. Tidy what you wrote once it is green, and leave a larger refactor as a follow-up.

## What a good test is

A test is a claim about what callers can observe through the interface: return values, errors, state they can read back, and effects on outside systems. It reads like a specification: "user can checkout with valid cart" names a capability and survives any refactor that keeps it.

Judge each test against two imagined edits:

| Edit | The test must | A test that does not is |
| --- | --- | --- |
| **Break the behavior**: a wrong value, a skipped or doubled effect | Fail | **Tautological**: its expected value is computed the way the code computes it, or it asserts on data the test built itself |
| **Change the internals** and keep every observable result | Pass | **Implementation-coupled**: it mocks internal collaborators, tests private methods, or verifies through a side channel such as a database query |

Keep a test that passes both. Rewrite or delete the rest. To get there:

- Drive the code through its public interface with a concrete input.
- Take the expected value from an independent source: the requirement, a known-good literal, a worked example.
- Assert what an external service receives. A call to an internal helper is not behavior.
- Pair every "this never happens" assertion with a case where it does happen.
- Assert the error type callers branch on, not the message.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for where mocks belong.

## Guardrails

- **Fix the code, not the test.** Change a test or loosen an assertion only when the expected behavior itself changed, and state the reason.
- Keep a regression test focused on its bug, with no broad fixture churn or unrelated coverage.
- For a flaky bug, make the test deterministic and name the signal it locks down.
- When a bug exposes a broader class of failures, land the focused regression test first, then add sibling coverage.

## Prove skipped work

Work without a new test still gets an executable check: a targeted script, a reproduction command, browser automation or a screenshot for UI layout, a snapshot comparison, a log assertion, or a focused integration check.

- **Check the real artifact.** Run the feature, read the actual value, inspect the diff. "It compiles", a self-report, and cached output are proxies.
- **Check a bug fix on the surface where the bug showed up.** A unit test shows branch behavior, not that the bug is gone.
- **Use the running app when the check needs it** (a UI, CLI, or service flow), through the repo's `verify-<app>` skill. Outside a `coordinate` run, read [create-verify-skill](../create-verify-skill/SKILL.md) and follow it first when the repo has none. A worker uses the one its brief names, and tells the coordinator when it names none.
- **Script the check** when you can, so it reruns the same way.
- **When a check fails**, suspect the observation method before the system.

## Report

Report the evidence, not only the outcome:

- The failing-before test or check, and the failure it produced.
- The passing-after run, and any nearby checks.
- For skipped work, why you skipped the test, and the check you ran instead with its output.
