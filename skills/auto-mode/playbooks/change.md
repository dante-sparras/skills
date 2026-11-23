### Change

**One PR, every decision settled. A worker builds it. You verify it and land it.**

1. **Contract.** Write down what done means, as criteria you can check.
   - When the task names an issue, take them from its agent brief or acceptance criteria. Otherwise restate the user's request.
   - Name the seams the tests go at, proposed and confirmed with the user the way **tdd** asks, so the implementer's brief carries them.
2. **Build.** Run **implement** with the contract as its single task. Done when the PR has landed, or holds a passing verdict and waits on the merge list.

**A tiny change is yours to make:** one or two files, proven by a check the repo already has. Branch off the default branch, make the edit, and run `open-pr.md` in place of **Build**.

**Reply:** the contract, the PR with its verdict, and whether it landed or waits on the user's merge.
