---
name: tdd
description: Test-driven development. Use when fixing a bug, building core logic test-first, writing a regression or integration test, or the user mentions "red-green".
---

# Test-Driven Development

TDD is the red → green loop. This skill decides when the loop runs, how to run it so the tests are worth keeping, and how to prove the work the loop skips.

When exploring the codebase, read `GLOSSARY.md` (if it exists) so test names and interface vocabulary match the project's domain language.

## Test first, or prove another way

Write the test first for:

- **A bug fix.** Reproduce the bug as a failing test before you change production code.
- **Core logic.** Domain rules, calculations, parsers, state transitions, and anything else whose result a caller reads back.

Skip the new test when it is expensive or proves nothing:

- **Expensive**: it needs broad harness setup, brittle mocks, slow end-to-end infrastructure, production-only state, vague reproduction steps, or large unrelated fixture churn.
- **Proves nothing**: a test can't judge the result, as with UI layout, or it would mostly test mocks, depend on timing or unrelated global state, or be deleted right after it proves the fix.

No new test beats a bad test. Every skip still ends in proof: see [Prove skipped work](#prove-skipped-work).

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Take the seams from the spec or ticket when it names them. Otherwise write down the seams you propose, each with a one-line note on what it catches and what it misses, and confirm them with the user before writing any test. Inside the `implement` skill, confirm them with the coordinator instead, who asks the user if needed. Agreeing seams up front puts testing effort on the critical paths and complex logic instead of every edge case.

When the shape of that interface is itself in question (how deep the module is, where the seam belongs, what the interface should expose), call the Skill tool with "codebase-design" for the vocabulary. It is a reference to consult, not a session to run.

## The loop

1. **Understand the behavior.** Name the intended behavior, the current behavior, the affected path, and the smallest observable reproduction.
2. **Choose the narrowest check at a seam.** Prefer the test file and harness the codebase already uses for that path. If no practical test path exists, skip per [Test first, or prove another way](#test-first-or-prove-another-way) instead of building one from scratch.
3. **Write one failing test.** Derive the expected value from the requirement, per [What a good test is](#what-a-good-test-is).
4. **Run it and see red.** Confirm it fails for the intended reason. If it passes, or fails for an unrelated reason, fix the test or the reproduction before you touch the implementation.
5. **Write only enough code to pass.** Make the smallest production change that satisfies the test and keeps nearby contracts. Add no speculative features.
6. **Rerun and see green.** Then start the next slice: one seam, one test, one minimal implementation per cycle.

For a bug fix, commit the failing test before the fix, so history shows red then green.

Refactoring is not part of the loop. It belongs to the review stage (see the `code-review` skill).

## What a good test is

A test is a claim about what callers can observe through the interface: return values, errors, state they can read back, and effects on outside systems. Private helpers, internal call order, and intermediate data are implementation. A good test reads like a specification: "user can checkout with valid cart" names a capability and survives any refactor that keeps it.

Judge each test against two imagined edits:

- **Break the behavior** (a wrong value, a skipped or doubled effect). The test must fail.
- **Change the internals** and keep every observable result. The test must pass.

Keep a test that passes both. Rewrite or delete the rest. To get there:

- Drive the code through its public interface with a concrete input.
- Take the expected value from an independent source: the requirement, a known-good literal, a worked example.
- Assert what an external service receives. A call to an internal helper is not behavior.
- Pair every "this never happens" assertion with a case where it does happen.
- Assert the error type callers branch on, not the message.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for where mocks belong.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). It fails the internals edit.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a constant asserted equal to itself), or asserts on data the test built itself. It passes the break edit.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior and lock in test structure before you understand the code. Work in **vertical slices**: each test a **tracer bullet** that responds to what the last cycle taught you.

## Guardrails

- **Never weaken a test to make it pass.** Fix the code until the test passes. Change a test or loosen an assertion only when the expected behavior itself changed, and state the reason.
- Keep a regression test focused on its bug, with no broad fixture churn or unrelated coverage.
- For a flaky bug, make the test deterministic and name the signal it locks down.
- When a bug exposes a broader class of failures, land the focused regression test first, then add sibling coverage.

## Prove skipped work

Work without a new test still gets an executable check: a targeted script, a reproduction command, browser automation or a screenshot for UI layout, a snapshot comparison, a log assertion, or a focused integration check.

- Check the real artifact: run the feature, read the actual value, inspect the diff. "It compiles", a self-report, and cached output are proxies, not proof.
- Verify a bug fix on the surface where the bug showed up. A unit test shows branch behavior, not that the bug is gone.
- When the check needs the running app (a UI, CLI, or service flow), drive it with the repo's `verify-<app>` skill. If the repo has none, call the Skill tool with `create-verification-skill` first. Inside the `implement` skill, use the one the coordinator names.
- Script the check when you can, so it reruns the same way.
- When a check fails, suspect the observation method before the system.

## Report

Report the evidence, not just the outcome:

- The failing-before test or check, and the failure it produced.
- The passing-after run, and any nearby checks.
- For skipped work, why you skipped the test and the check you ran instead, with its output.
