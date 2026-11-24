# Agent briefs

An agent brief is the comment posted on an issue or PR when it moves to `ready-for-agent`. It is the contract the agent works from. The issue's body and discussion are context.

For an issue, the brief says what to build. For a PR, it says what is left to do to the existing diff: finish it, close gaps, answer review points.

## Principles

- **Durable.** The issue may wait for weeks while the code changes. Name interfaces, types, function signatures, and config shapes. Leave out file paths, line numbers, and anything that depends on today's structure.
- **Behavioral.** Say what the system should do. The agent explores the code fresh and chooses how. Write "the `SkillConfig` type accepts an optional `schedule` field of type `CronExpression`", not "add a schedule field on line 42 of the types file".
- **Testable.** Each acceptance criterion can be checked on its own. Write "`gh issue list --label needs-triage` returns issues that have been through initial classification", not "triage works correctly".
- **Bounded.** State what is out of scope, so the agent leaves adjacent features alone.

## Template

```markdown
## Agent Brief

**Category:** bug / enhancement
**Route:** bug / change / feature
**Summary:** one line on what needs to happen

**Current behavior:**
What happens now. For a bug, the broken behavior. For an enhancement,
the status quo the feature builds on. For a PR, the state of the diff.

**Desired behavior:**
What happens once the work is done, edge cases and error conditions included.

**Reproduction:**
For a bug: the exact steps or command that showed it during triage,
and the output. Write "not reproduced" when triage could not.
Omit for an enhancement.

**Key interfaces:**
- `TypeName`: what needs to change and why
- `functionName()` return type: what it returns now and what it should return
- Config shape: any new options

**Acceptance criteria:**
- [ ] Specific, testable criterion 1
- [ ] Specific, testable criterion 2

**Seams:**
- Where the tests for this go, when the interview settled it. Omit otherwise.

**Out of scope:**
- What this issue leaves unchanged
- An adjacent feature that looks related but is separate
```

## The route

**Route** names the size of the work, so the worker that picks the issue up starts on the right path:

- `bug`: something is broken and nobody has named the cause. The fix starts with diagnosis.
- `change`: one PR, with every decision settled in this brief.
- `feature`: more than one PR. The brief is the starting point for a spec, not the contract for a build.

Pick it from what triage learned in the code, not from the label: a bug whose cause triage already found is a `change`.

## Example: an issue

```markdown
## Agent Brief

**Category:** bug
**Route:** change
**Summary:** Skill description truncation drops mid-word, producing broken output

**Current behavior:**
When a skill description exceeds 1024 characters, it is truncated at exactly
1024 characters regardless of word boundaries. This produces descriptions
that end mid-word (e.g. "Use when the user wants to confi").

**Desired behavior:**
Truncation should break at the last word boundary before 1024 characters
and append "..." to indicate truncation.

**Reproduction:**
A SKILL.md whose description is 1,100 characters of repeated words.
Loading it and printing the stored description shows the last word
cut in half, with no "...".

**Key interfaces:**
- The `SkillMetadata` type's `description` field: no type change needed,
  but the logic that populates it needs to respect word boundaries
- Any function that reads SKILL.md frontmatter and extracts the description

**Acceptance criteria:**
- [ ] Descriptions under 1024 chars are unchanged
- [ ] Descriptions over 1024 chars are truncated at the last word boundary
      before 1024 chars
- [ ] Truncated descriptions end with "..."
- [ ] The total length including "..." does not exceed 1024 chars

**Out of scope:**
- Changing the 1024 char limit itself
- Multi-line description support
```

## Example: a PR

```markdown
## Agent Brief

**Category:** enhancement
**Route:** change
**Summary:** Finish the contributor's `--json` output flag for `triage list`

**Current behavior:**
The PR adds a `--json` flag that serializes the issue list to JSON. The happy
path works and the diff matches the project's command structure. Two gaps
remain: errors are still printed as human text (not JSON), and the new flag has
no test coverage.

**Desired behavior:**
With `--json`, all output (including errors) is well-formed JSON on stdout,
and the command's exit codes are unchanged. The existing human-readable output
is untouched when the flag is absent.

**Key interfaces:**
- The command's error path should emit `{ "error": string }` under `--json`
  instead of the plain-text error
- Reuse the serializer the PR already added

**Acceptance criteria:**
- [ ] `triage list --json` emits valid JSON for both success and error cases
- [ ] Exit codes match the non-JSON command
- [ ] A test covers the `--json` success output and one error case
- [ ] Default (non-JSON) output is byte-for-byte unchanged

**Out of scope:**
- Adding `--json` to any other command
- Changing the JSON shape of the success payload the PR already defined
```
