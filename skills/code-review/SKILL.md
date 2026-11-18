---
name: code-review
description: "Adversarial review of the changes since a fixed point (commit, branch, tag, or merge-base). Parallel reviewers from different model families each try to break the change and report on three separate axes: Breakage (wrong behavior, edge cases, blast radius), Spec (does it do what the issue or spec asked?), and Standards (does it follow this repo's documented standards?). Behavior findings survive only when a rerun proves them. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\"."
---

Adversaries try to break the diff between `HEAD` and a fixed point the user supplies. Each one reports on three axes:

- **Breakage**: does the change do something wrong that the spec never mentions? Edge cases, error paths, and callers outside the diff that it breaks.
- **Spec**: does the change faithfully implement the originating issue or spec?
- **Standards**: does the change follow this repo's documented coding standards?

Run the available reviewers with fresh context, one per configured model family. A Breakage or Spec finding survives only when you rerun its command and the output shows the failure. Report the findings. Do not apply fixes.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-skills`.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point (a commit SHA, branch name, tag, `main`, `HEAD~5`, etc.). If they didn't specify one, ask for it.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`. When the working tree has uncommitted changes the user wants reviewed, save `git diff HEAD` to a patch file outside the repo.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here, not inside the reviewers.

### 2. State the intent

Restate in two or three sentences what the change is for, from the user's message, the commit messages, and the PR description. Ask the user when the intent is unclear. Every reviewer gets this restatement, and a finding counts only when it breaks it.

### 3. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, etc.), fetched via the workflow in the tracker doc.
2. A path the user passed as an argument.
3. A spec file under `docs/` or `specs/` matching the branch name or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't one, the reviewers skip the Spec axis and the report says "no spec available".

### 4. Identify the standards and what tooling already checks

Search the repo for every file that documents how code should be written. When `CODING_STANDARDS.md` or `CONTRIBUTING.md` exists, it must be on the list. Note `GLOSSARY.md` (or each context's glossary under `GLOSSARY-MAP.md`) when it exists.

Then read the repo's check command: its `package.json` or build-tool `lint`, `typecheck`, and `test` scripts, its pre-commit hooks, and its CI workflows. List what they enforce. Reviewers skip anything on that list, because a check already fails on it.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below: a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins. Where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation.

Each smell reads *what it is* → *how to fix*. Match it against the diff:

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it. If no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it, and inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 5. Pick the panel

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) for the `reviewer`.

1. Run one reviewer per model family represented by the runnable default and backup. Compare model families across providers. For example, `claude-opus-5-5` and `anthropic/claude-opus-5-5` are both Claude, as is Fable.
2. Run the default first for its family. Run the backup in parallel when it adds a family. If the default is unavailable or hits a usage limit, promote the backup. Reuse its review if it already started.
3. When the role resolves to inheritance, run one reviewer on the current model. Report any fallback and the families that returned reviews.

### 6. Launch the reviewers in parallel

Launch reviewers in parallel, each with a fresh context and an isolated worktree at `HEAD`. In T3, use `delegate_task` with `mode: "async"` and `isolation: "worktree"`. Outside T3, use the native agent tool with worktree isolation. When step 1 saved a patch, require each reviewer to apply it before probing.

Every reviewer gets the same prompt:

- The diff command, the commit list, and the patch path if there is one.
- The intent from step 2, and the spec path or fetched contents from step 3.
- The standards files and the tooling list from step 4, the glossary path, and the smell baseline pasted in full (the reviewer has no other access to it).
- This brief:

> Break this change. Read the diff, then the code around it and the callers it touches. Try each of these: inputs and states the author did not test (empty, huge, concurrent, malformed, repeated), error and retry paths, a spec requirement that is missing, partial, or wrong, and code outside the diff that depends on what changed.
>
> Prove each Breakage and Spec finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. Keep repros in your own worktree and do not edit the reviewed checkout. Report each one with a title, the exact command, the output it printed, and the output the intent or spec requires. A Spec finding also quotes the spec line. Leave out any Breakage or Spec finding you did not run.
>
> For Standards, cite the documented rule (file and rule) for each breach, and name each baseline smell with the hunk it applies to. Smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything the tooling list already enforces. Use the glossary's terms for domain concepts, and flag a new name for a concept the glossary already names.
>
> No findings is a valid result. Report under `## Breakage`, `## Spec`, and `## Standards`, under 600 words.

Collect every reviewer's report. If one returns nothing, continue with the rest and note the dropout.

### 7. Verify

Rerun each Breakage and Spec finding's command yourself. Keep a finding when the output shows the failure and the failure breaks the intent or the spec. Drop the rest. Merge findings that share a root cause, and list every reviewer that found it.

Standards findings are not rerun. Keep each one that cites a real rule or names a smell against a real hunk. Merge duplicates the same way.

Mark each mechanical finding (a fixed syntax pattern, a banned API, an import shape, a file-location rule) as a candidate for the `correct` skill to turn into a check, not as a review rule.

### 8. Report

- **Intent**: the restatement from step 2.
- **Panel**: each seat's model and family, any seat that fell back and why, and whether the families actually differed.
- `## Breakage`, `## Spec`, `## Standards`: each verified finding with its command and output (Breakage and Spec) or its rule or smell (Standards), and the reviewers that found it. Say "no verified findings" for an empty axis, and "no spec available" when step 3 found none.
- **Dropped**: for each reviewer, the count of dropped findings and why.

Do **not** merge or rerank findings across axes (see _Why separate axes_). Agreement across families is stronger evidence than agreement within one, so say which kind each shared finding has.

End with a one-line summary: verified findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

## Why separate axes

A change can pass one axis and fail another:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**
- Code that meets the spec and the standards but corrupts state on a retry the spec never mentioned → **Spec and Standards pass, Breakage fail.**

Reporting them separately stops one axis from masking another.
