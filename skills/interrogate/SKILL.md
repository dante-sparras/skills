---
name: interrogate
description: "Adversarial review of the changes since a fixed point (commit, branch, tag, or merge-base). Reviewers from different model families try to break the change on three axes, Breakage, Spec, and Standards, and a behavior finding survives only when a rerun proves it. Use when asked to review a branch, a PR, or work-in-progress changes, to review everything since a commit or tag, or when a finished change needs a verdict before it lands."
---

Adversaries try to break the diff between `HEAD` and a fixed point. Each reports on three axes:

- **Breakage**: the change does something wrong that the spec never mentions. Edge cases, error paths, callers outside the diff.
- **Spec**: the change implements the originating issue or spec faithfully.
- **Standards**: the change follows this repo's documented coding standards.

The axes stay apart from the first step to the report, so one never masks another: code can follow every standard and build the wrong thing, or meet the spec and corrupt state on a retry the spec never mentioned.

A Breakage or Spec finding survives only when you rerun its command and the output shows the failure. Report the findings and leave the fixes to the caller.

## Steps

1. **Pin the fixed point.** Use what the user gave: a SHA, branch, tag, `main`, `HEAD~5`. Ask when they gave none. Done when `git rev-parse <fixed-point>` resolves and the diff is non-empty.
   - The diff is `git diff <fixed-point>...HEAD`, with three dots, so it compares against the merge-base.
   - The commits are `git log <fixed-point>..HEAD --oneline`.
   - For uncommitted changes the user wants reviewed, save `git diff HEAD` to a patch file outside the repo. That leaves out new files, so append each path from `git ls-files --others --exclude-standard` with `git diff --no-index -- /dev/null <path>`, in a POSIX shell. That command exits 1 for a non-empty file, which is not an error.

2. **State the intent** in two or three sentences, from the user's message, the commit messages, and the PR description. Ask the user when it is unclear. Every reviewer gets it, and a finding counts only when it breaks it.

3. **Find the spec.** Take the first that exists:
   1. The spec your caller or the user passed: a path, an issue, or text.
   2. An issue the commit messages reference (`#123`, `Closes #45`), fetched per `docs/agents/issue-tracker.md`. If that file is missing, say that `/setup-skills` has not run in this repo and carry on down this list.
   3. A file under `docs/` or `specs/` that matches the branch name or the feature.
   4. The user's answer when you ask where the spec is. If there is none, the reviewers skip the Spec axis and the report says "no spec available".

4. **Find the standards.**
   - List every file that documents how code should be written, with `CODING_STANDARDS.md` and `CONTRIBUTING.md` when they exist. Note `GLOSSARY.md`, or each context's glossary under `GLOSSARY-MAP.md`.
   - List what the repo's tooling already enforces: its `lint`, `typecheck`, and `test` scripts, its pre-commit hooks, and its CI workflows. Reviewers skip everything on this list, because a check already fails on it.
   - Add the [smell baseline](#smell-baseline), which applies even when the repo documents nothing.

5. **Pick the panel.** Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) for the `reviewer`.
   - Run one reviewer per model family among the runnable default and backup. The same model offered by two providers is one family, and so are one vendor's other models.
   - Start the default and the backup together when the backup adds a family. If the default is unavailable or hits a usage limit, the backup's review stands in for it.
   - A caller that is itself reviewing, in a clean checkout of the head, is the first seat: start only the other family.
   - When the role resolves to inheritance, run one reviewer on the current model.
   - **No panel.** When your caller asks for a review without a panel, review the diff yourself against the same brief and say so under **Panel**.

6. **Launch** the reviewers in parallel, each with a fresh context and an isolated worktree at `HEAD`. Use `delegate_task` with `mode: "async"` and `isolation: "worktree"`. Every reviewer gets the same prompt:
   - the diff command, the commit list, and the patch path with an instruction to apply it first, when step 1 saved one
   - the intent, and the spec's path or contents
   - the standards files, the tooling list, the glossary path, and the smell baseline pasted in full, since the reviewer cannot reach it any other way
   - the [reviewer brief](#reviewer-brief)

   If a reviewer returns nothing, continue with the rest and note the dropout.

7. **Verify.**
   - Rerun each Breakage and Spec finding's command yourself, in the reviewer's worktree when it still exists, or after writing the reported repro file into a checkout of `HEAD`. Keep a finding when the output shows the failure, and the failure breaks the intent or the spec, or is a regression: the same command passes at the fixed point. Keep a finding no command can show, such as a wrong line of config, a migration, or a doc, when it cites the exact hunk, what it breaks, and why it cannot be run.
   - Keep each Standards finding that cites a real rule, or names a smell against a real hunk. These are not rerun.
   - Merge findings that share a root cause, and list every reviewer that found each.
   - Mark each mechanical finding (a fixed syntax pattern, a banned API, an import shape, a file-location rule) as a candidate for the `guardrail` skill to turn into a check.

8. **Report.**
   - **Intent**: the restatement from step 2.
   - **Panel**: each seat's model and family, any seat that fell back and why, and whether the families differed.
   - `## Breakage`, `## Spec`, `## Standards`: each verified finding with its command and output, or its rule or smell, and the reviewers that found it. Agreement across families is stronger evidence than agreement within one, so say which kind a shared finding has. Write "no verified findings" for an empty axis.
   - **Dropped**: per reviewer, how many findings were dropped and why.
   - A one-line summary: the verified findings per axis, and the worst issue within each axis. Findings are never ranked across axes.

## Reviewer brief

> Break this change. Read the diff, then the code around it and the callers it touches. Try each of these: inputs and states the author did not test (empty, huge, concurrent, malformed, repeated), error and retry paths, a spec requirement that is missing, partial, or wrong, and code outside the diff that depends on what changed.
>
> Prove each Breakage and Spec finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. Keep repros in your own worktree and do not edit the reviewed checkout. Report each one with a title, the absolute path of your worktree, the full contents of any repro file you wrote, the exact command, the output it printed, and the output the intent or spec requires. A Spec finding also quotes the spec line. Leave out any Breakage or Spec finding you did not run, unless nothing can run it: then cite the exact hunk, what it breaks, and why it cannot be run.
>
> For Standards, cite the documented rule (file and rule) for each breach, and name each baseline smell with the hunk it applies to. Smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything the tooling list already enforces. Use the glossary's terms for domain concepts, and flag a new name for a concept the glossary already names.
>
> No findings is a valid result. Report under `## Breakage`, `## Spec`, and `## Standards`, under 600 words, not counting code blocks and command output.

## Smell baseline

Fowler's code smells (_Refactoring_, ch. 3), matched against the diff: Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, and Refused Bequest.

Each is a labelled judgement call, such as "possible Feature Envy", never a hard violation, and each finding names the fix. A documented repo standard wins: where it endorses what a smell would flag, drop the smell.
