# Agent briefs

An agent brief is the contract on an issue in `ready-for-agent`: what a worker builds from, and the bar its PR is held to. Every such issue carries one, written from the template below.

- **An issue a skill files**, such as a ticket of a spec or a bug that `debug` reproduced: the brief is the issue's body.
- **An issue that already exists**, which `triage` moves to `ready-for-agent`: the brief is a comment, and the issue's body and discussion are context.

For an issue, the brief says what to build. For a PR, it says what is left to do to the existing diff: finish it, close gaps, answer review points.

## Principles

- **Durable.** The issue may wait for weeks while the code changes. Name interfaces, types, function signatures, and config shapes. Leave out file paths, line numbers, and anything that depends on today's structure. A snippet belongs only when it states a decision more exactly than prose can, such as a state machine, a schema, or a type shape.
- **Behavioral.** Say what the system should do. The agent explores the code fresh and chooses how. Write "the `SkillConfig` type accepts an optional `schedule` field of type `CronExpression`", not "add a schedule field on line 42 of the types file".
- **Testable.** Each acceptance criterion can be checked on its own. Write "`gh issue list --label needs-triage` returns issues that have been through initial classification", not "triage works correctly".
- **Bounded.** State what is out of scope, so the agent leaves adjacent features alone.

## Template

```markdown
## Agent Brief

**Category:** bug / enhancement
**Route:** bug / change
**Summary:** one line on what needs to happen

**Current behavior:**
What happens now. For a bug, the broken behavior. For an enhancement,
the status quo the feature builds on. For a PR, the state of the diff.

**Desired behavior:**
What happens once the work is done, from the user's perspective,
edge cases and error conditions included.

**Reproduction:**
For a bug: the exact steps or command that showed it, and the output.
Write "not reproduced" when nobody could.
Omit for an enhancement.

**Key interfaces:**
- `TypeName`: what needs to change and why
- `functionName()` return type: what it returns now and what it should return
- Config shape: any new options

**Acceptance criteria:**
- [ ] Specific, testable criterion 1
- [ ] Specific, testable criterion 2

**Seams:**
- Where the tests for this go: from the spec's testing decisions,
  or as an interview settled it. Omit otherwise.

**Out of scope:**
- What this issue leaves unchanged
- An adjacent feature that looks related but is separate

## Parent

A reference to the spec, on a ticket of one. Omit the section otherwise.

## Blocked by

A reference to each blocking issue. Omit the section when there are none,
or when the blockers are native links.
```

## The route

**Route** tells the factory's worker how to start:

- `bug`: something is broken and nobody has named the cause. The fix starts with diagnosis.
- `change`: one PR, with every decision settled in this brief.

Work bigger than one PR gets no agent brief of its own: it becomes a spec, and each of its tickets gets one.

Pick it from what triage learned in the code, not from the label: a bug whose cause triage already found is a `change`.

## Example

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
