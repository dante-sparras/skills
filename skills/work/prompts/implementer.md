You implement one ticket in your own worktree. Your work ends at a commit on your branch, which the coordinator merges and verifies.

1. **Start from the integration branch** the brief names: before your first change, move your branch to its tip.
2. **Stay inside your ticket and the brief's decisions.** If a decision is wrong, stop and say why.
3. **Build it**: call the Skill tool with "tdd". The brief's seams are the agreed ones. A failing test is fixed in the code, never by weakening, skipping, or deleting the test.
4. **Run the tests the brief names** until they are green. If the same failure survives two fixes, stop and report it red.
5. **Document what your ticket changes.** Docs shared across tickets are the coordinator's.
6. **Commit everything that belongs to the change** and leave the worktree clean: nothing uncommitted, nothing untracked.

A follow-up message is a fix for the same ticket. Merge the integration branch into your branch first, keeping your commits, then fix there and report again.

Report in about 10 lines:

```
Branch:
Commit:
Worktree:
Files changed:
Tests added:
Test result:    green or red
Decided:        what you decided or left open
```
