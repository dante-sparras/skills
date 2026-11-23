### Bug

**The cause is unknown. A worker names it from evidence before anything ships.**

1. **Diagnose and fix.** Run **implement** with the bug as its single task, and have its implementer build with `diagnosing-bugs`. In the brief:
   - Point at the repo's `verify-<app>` skill when one reaches the surface the bug shows on.
   - Say to stop and report when the fix needs a design decision or a second PR.

   Done when the implementer's report names the cause, shows the original reproduction passing, and shows a regression test or says why no seam could hold one.
2. **Size the fix.** If the implementer stopped on a design decision or a second PR, re-route to `feature` with the diagnosis as its starting context.
3. **Land.** Carry on with `implement` from the code-ready head. Done when the PR has landed, or holds a passing verdict and waits on the merge list.

**Reply:** what was broken, the cause, the fix, the failing-then-passing output, the PR with its verdict, and whether it landed or waits on the user's merge.
