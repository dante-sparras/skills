---
name: review-pr
description: "Adversarial review of one PR against its ticket and the spec above it: what it breaks, whether it delivers the ticket, and whether it keeps the repo's standards. Use when asked to review a PR, or when a PR needs a review before it lands."
disable-model-invocation: true
---

# Review PR

Adversaries try to break one PR: the diff between its head and its base. Each reports on three axes:

- **Breakage**: the change does something wrong that the spec never mentions. Edge cases, error paths, callers outside the diff.
- **Spec**: the PR delivers the ticket it closes, and keeps the spec that ticket belongs to.
- **Standards**: the change follows this repo's documented coding standards.

The axes stay apart from the first step to the report, so one never masks another: code can follow every standard and build the wrong thing, or meet the spec and corrupt state on a retry the spec never mentioned.

A Breakage or Spec finding survives when you rerun its command and the output shows the failure, or when nothing can run it and it cites the exact line it breaks. Report the findings and leave the fixes to the caller.

## Steps

1. **Pin the PR.** Take the PR the user or your caller named, by number or link, and ask when they named none. Read it with `pull_request_read`, with `include: ["body"]`. Fetch, and check out its head, detached, unless your caller already has. The fixed point is its base, `origin/<base branch>`. Done when the diff is non-empty.
   - The diff is `git diff <fixed-point>...HEAD`, with three dots, so it compares against the merge-base.
   - The commits are `git log <fixed-point>..HEAD --oneline`.
   - **A re-review.** When your caller names a head an earlier review covered, and that head is an ancestor of the PR's head, make it the fixed point, so the seats review only what changed since.

2. **Find the ticket and the spec.** The ticket is the contract, and the spec says what the ticket is for. Fetch both, with their comments, per `docs/agents/issue-tracker.md`. If that file is missing, say that `/setup-skills` has not run in this repo.
   - **The ticket** is each issue the PR's body closes: a `Closes`, `Fixes`, or `Resolves` line. Its agent brief or its acceptance criteria is what the PR must deliver.
   - **The spec** is the ticket's parent: its parent issue, or the issue its `## Parent` section names. Its user stories and decisions are what the ticket serves. A ticket with no parent has no spec, and the ticket alone is the bar.
   - **A ticket your caller passed** joins these, such as the task in a factory reviewer's brief.
   - **No ticket at all.** Ask the user which issue the PR is for. With none, the seats skip the Spec axis, and the report says "no ticket".

3. **State the intent** in two or three sentences, from the ticket, the PR's title and description, and its commit messages. Ask the user when it is unclear. Every seat gets it, and a finding counts only when it breaks it.

4. **Find the standards.**
   - List every file that documents how code should be written, with `CODING_STANDARDS.md` and `CONTRIBUTING.md` when they exist. Note `GLOSSARY.md`, or each context's glossary under `GLOSSARY-MAP.md`.
   - List what the repo's tooling already enforces: its `lint`, `typecheck`, and `test` scripts, its pre-commit hooks, and its CI workflows. Seats skip everything on this list, because a check already fails on it.
   - Add the [smell baseline](#smell-baseline), which applies even when the repo documents nothing.

5. **Pick the panel.** Read [Resolve a role](../setup-skills/model-roles.md#resolve-a-role) for the `reviewer`.
   - Run one seat per model family among the runnable default and backup. The same model offered by two providers is one family, and so are one vendor's other models.
   - Start the default and the backup together when the backup adds a family. If the default is unavailable or hits a usage limit, the backup's review stands in for it.
   - A caller that is itself reviewing, in a clean checkout of the head, is the first seat: start only the other family, and remove your own repro files when you are done.
   - When the role resolves to inheritance, run one seat on the current model.
   - **No panel.** When your caller asks for a review without a panel, review the diff yourself against the same brief and say so under **Panel**.

6. **Launch** the seats in parallel, each with a fresh context and an isolated worktree at `HEAD`. Use `delegate_task` with `mode: "async"` and `isolation: "worktree"`. Every seat gets the same prompt:
   - the PR's link, the diff command, and the commit list
   - the intent, and the ticket's and the spec's contents
   - the standards files, the tooling list, the glossary path, and the smell baseline pasted in full, since the seat cannot reach it any other way
   - the [seat brief](#seat-brief)

   If a seat returns nothing, continue with the rest and note the dropout.

7. **Verify.**
   - Rerun each Breakage and Spec finding's command yourself, in the seat's worktree when it still exists, or after writing the reported repro file into a checkout of `HEAD`. Keep a finding when the output shows the failure, and the failure breaks the intent or the spec, or is a regression: the same command passes at the fixed point. Keep a mutation finding when the tests still pass with its patch applied. Keep a finding no command can show, such as a wrong line of config, a migration, or a doc, when it cites the exact hunk, what it breaks, and why it cannot be run.
   - Keep each Standards finding that cites a real rule, or names a smell against a real hunk. These are not rerun.
   - Merge findings that share a root cause, and list every seat that found each.
   - Mark each mechanical finding (a fixed syntax pattern, a banned API, an import shape, a file-location rule) as a candidate for the `correct` skill to turn into a check.

## Report

- **PR, ticket, and spec**: their links, or "no ticket".
- **Intent**: the restatement from step 3.
- **Panel**: each seat's model and family, any seat that fell back and why, and whether the families differed.
- `## Breakage`, `## Spec`, `## Standards`: each verified finding with its command and output, or its rule or smell, and the seats that found it. Agreement across families is stronger evidence than agreement within one, so say which kind a shared finding has. Write "no verified findings" for an empty axis.
- **Dropped**: per seat, how many findings were dropped and why.
- A one-line summary: the verified findings per axis, and the worst issue within each axis. Findings are never ranked across axes.

## Seat brief

> Break this change. Read the diff, then the code around it and the callers it touches. Try each of these: inputs and states the author did not test (empty, huge, concurrent, malformed, repeated), error and retry paths, a spec requirement that is missing, partial, or wrong, and code outside the diff that depends on what changed.
>
> Then test the tests. A test, assertion, or check that the diff weakens, skips, or deletes is a Breakage finding, unless the intent asks for it: cite the hunk. Invert one condition the change adds to the production code, run the tests that cover it, and restore the file. A mutation that stays green is a Breakage finding: report the mutation as a patch, and name the case no test covers.
>
> Prove each Breakage and Spec finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. Keep repros in your own worktree and do not edit the reviewed checkout. Report each one with a title, the absolute path of your worktree, the full contents of any repro file you wrote, the exact command, the output it printed, and the output the intent or spec requires. A Spec finding also quotes the line of the ticket or spec it breaks. Leave out any Breakage or Spec finding you did not run, unless nothing can run it: then cite the exact hunk, what it breaks, and why it cannot be run.
>
> For Standards, cite the documented rule (file and rule) for each breach, and name each baseline smell with the hunk it applies to. Smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything the tooling list already enforces. Use the glossary's terms for domain concepts, and flag a new name for a concept the glossary already names.
>
> No findings is a valid result. Report under `## Breakage`, `## Spec`, and `## Standards`, under 600 words, not counting code blocks and command output.

## Smell baseline

Fowler's code smells (_Refactoring_, ch. 3), matched against the diff. Each is a labelled judgement call, such as "possible Feature Envy", never a hard violation. A documented repo standard wins: where it endorses what a smell would flag, drop the smell.

| Smell | What it is | Fix |
| --- | --- | --- |
| Mysterious Name | A name that hides what the thing does or holds | Rename it. If no honest name comes, the design is murky |
| Duplicated Code | The same logic shape in more than one hunk or file | Extract the shape and call it from both |
| Feature Envy | A method that reaches into another object's data more than its own | Move the method onto the data it envies |
| Data Clumps | The same few fields or params travelling together | Bundle them into one type and pass that |
| Primitive Obsession | A primitive or string standing in for a domain concept | Give the concept its own small type |
| Repeated Switches | The same `switch` or `if` cascade on one type, in several places | Use polymorphism, or one map both sites share |
| Shotgun Surgery | One logical change scattered across many files | Gather what changes together into one module |
| Divergent Change | One module edited for several unrelated reasons | Split it so each module changes for one reason |
| Speculative Generality | Abstraction, parameters, or hooks for needs the spec lacks | Delete it, and inline until a real need shows |
| Message Chains | Long `a.b().c().d()` navigation the caller depends on | Hide the walk behind one method on the first object |
| Middle Man | A class or function that mostly delegates onward | Cut it and call the real target |
| Refused Bequest | A subclass that ignores or overrides most of what it inherits | Drop the inheritance and use composition |
