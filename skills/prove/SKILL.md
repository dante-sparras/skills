---
name: prove
description: "Prove a change on the real artifact, and capture the evidence. Use when a change is finished and needs proof that it works, a test cannot judge the result, a reviewer checks what a PR does, or a person asks whether something really works."
disable-model-invocation: true
---

# Prove

A change is proven when you ran the real thing and captured what it did. "It compiles", a passing unit test, a self-report, and cached output are proxies.

## The check

Every proof is an executable check: a targeted script, a reproduction command, browser automation or a screenshot for UI layout, a snapshot comparison, a log assertion, or a focused integration check.

- **Check the real artifact.** Run the feature, read the actual value, inspect the diff.
- **Check on the surface where a user meets the change.** For a bug fix, that is the surface where the bug showed up: a unit test shows branch behavior, not that the bug is gone.
- **Use the running app when the check needs it** (a UI, CLI, or service flow), through the repo's `verify-<app>` skill. A factory worker uses the one its brief names, and returns `BLOCKED` on the verify skill when it names none. Anyone else reads [create-verify-skill](../create-verify-skill/SKILL.md) and follows it first when the repo has none.
- **Script the check** when you can, so it reruns the same way.
- **When a check fails**, suspect the observation method before the system.

## Standards

- Exercise the real user path, not internal setters or test-only endpoints.
- Capture the action and the resulting state, not only the final screen.
- Verify side effects (files written, rows inserted, messages sent) alongside what is visible.
- Mock only where a production boundary already isolates the external system.
- When the safe path is a dry run or test mode, observe what it skips (files, network, git refs) instead of trusting its name. Some dry runs still touch the network or open a browser.

## Report

Report the evidence, not only the outcome:

- The check, as a command someone else can rerun, and the lines of its real output that show the result.
- For a fix, the failing run before the change and the passing run after it.
- What you skipped, and what stays unproven.
