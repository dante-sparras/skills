---
name: debug
description: "Diagnosis loop for hard bugs and performance regressions. Use when asked to diagnose or debug something, when something throws, fails, or gives wrong results and the cause is unknown, or when something got slower."
disable-model-invocation: true
---

# Debug

Six phases, in order. Skip one only with a stated reason. Read `GLOSSARY.md`, when the repo has one, for the modules involved.

**Redact every secret** in the commands, output, and captured artifacts you show: write `<REDACTED>` in its place. Build loops against env vars, so the credential stays in the environment. Quote only the lines of an artifact that carry the signal. If the redacted output is too little to diagnose from, say so and ask the user.

## Phase 1: Build a feedback loop

**This is the skill.** With a **tight** pass/fail signal that goes **red** on this bug, you will find the cause: bisection, hypotheses, and instrumentation all consume it. Without one, reading code will not save you. Spend most of your effort here. Be aggressive and creative.

Ways to build one, roughly in this order:

1. **A failing test** at the seam that reaches the bug: unit, integration, or e2e.
2. **A curl or HTTP script** against a running dev server.
3. **A CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **A headless browser script** that drives the UI and asserts on DOM, console, or network.
5. **A replayed trace.** Save a real request, payload, or event log to disk and replay it through the code path in isolation.
6. **A throwaway harness.** A minimal subset of the system, one service with mocked deps, that hits the bug's code path with one function call.
7. **A property or fuzz loop.** For "sometimes wrong output", run 1,000 random inputs and look for the failure mode.
8. **A bisection harness.** When the bug appeared between two known states (commits, datasets, versions), automate "boot at state X, check" so `git bisect run` can drive it.
9. **A differential loop.** The same input through the old version and the new, or two configs, with the outputs diffed.
10. **A person in the loop.** Last resort. When a person must click, give them numbered steps in your thread, one batch at a time, and ask them to paste back what each step showed.

Then **tighten** it:

- **Faster**: cache setup, skip unrelated init, narrow the test scope.
- **Sharper**: assert on the specific symptom, not "didn't crash".
- **Deterministic**: pin time, seed the RNG, isolate the filesystem, freeze the network.

**A non-deterministic bug** needs a higher reproduction rate, not a clean repro. Loop the trigger 100 times, parallelise, add stress, narrow timing windows, inject sleeps. A bug that fails half the time is debuggable, and one that fails 1% of the time is not, so keep raising the rate.

**When you cannot build a loop**, stop and say so. List what you tried, and ask the user for one of: access to an environment that reproduces it, a redacted artifact (a HAR file, log dump, core dump, or timestamped screen recording), or permission to add temporary production instrumentation.

Phase 1 is done when you can name **one command** you have already run, shown with its redacted output, that is:

- [ ] **Red-capable**: it drives the real bug code path and asserts the user's exact symptom, so it goes red on this bug and green once it is fixed.
- [ ] **Deterministic**: the same verdict every run, or a pinned, high reproduction rate for a flaky bug.
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable**: it runs unattended. A person is involved only for the steps nothing else can drive.

If you catch yourself reading code to build a theory before this command exists, stop. That jump is the failure this skill prevents.

## Phase 2: Reproduce and minimise

Run the loop and watch it go red. Confirm:

- [ ] The failure is the one the **user** described, not a nearby one. The wrong bug gets the wrong fix.
- [ ] It reproduces across runs, or at a rate high enough to debug against.
- [ ] You captured the exact symptom (error message, wrong output, timing), so later phases can check the fix against it.

Then shrink the repro to the smallest scenario that still goes red. Cut inputs, callers, config, data, and steps one at a time, rerunning the loop after each cut. A minimal repro leaves fewer parts to suspect, and it becomes the regression test.

Done when every remaining element is load-bearing: removing any one turns the loop green.

## Phase 3: Hypothesise

Write **three to five ranked hypotheses** before you test any, so the first plausible idea does not anchor you. Each one is **falsifiable**:

> If <X> is the cause, then <changing Y> will make the bug disappear, or <changing Z> will make it worse.

A hypothesis with no prediction is a vibe: sharpen it or drop it.

Show the ranked list to the user before testing, with `send_to_user`, and go on with your ranking. They may re-rank it at once ("we just deployed a change to #3") or rule some out.

## Phase 4: Instrument

Each probe maps to one prediction from Phase 3. Change one variable at a time.

1. **A debugger or REPL**, when the environment has one. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that tell the hypotheses apart.

Tag every debug log with a unique prefix, such as `[DEBUG-a4f2]`, so cleanup is one grep.

**A performance regression** needs measurements, not logs. Take a baseline with a timing harness, a profiler, or a query plan, then bisect. Measure first, fix second.

## Phase 5: Fix and regression test

Write the regression test before the fix, at a **correct seam**: one where the test exercises the real bug pattern as it occurs at the call site. A seam that is too shallow, such as a single-caller test for a bug that needs several callers, gives false confidence.

**No correct seam is itself a finding.** The architecture is keeping the bug from being locked down. Say so in your report, and name the seam that would have held the test.

With a correct seam:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail. If you forced the red by mutating code or a fixture, `diff` against a pristine copy to prove the mutation landed.
3. Apply the fix.
4. Watch it pass.
5. Rerun the Phase 1 loop against the original, un-minimised scenario.
6. Ask whether a type, a lint, or a CI check could have caught this bug before it shipped. If one could, name it in your report as a follow-up for the `correct` skill.

## Phase 6: Clean up

Done when:

- [ ] The original repro no longer reproduces, by a rerun of the Phase 1 loop.
- [ ] The regression test passes, or the missing seam is documented.
- [ ] Every `[DEBUG-...]` log is gone: grep the prefix.
- [ ] Throwaway harnesses are deleted, or moved to a clearly marked debug location.
- [ ] The commit or PR message states the hypothesis that proved correct, so the next debugger learns from it.
