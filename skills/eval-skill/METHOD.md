# How the script runs the novelty method

Split a skill into claims, ask each claim with and without the skill on every answerer, grade each answer with a judge, and sort the claim by the two grades.

## Claims

The drafter splits the skill into at most 30 claims. Each claim has a question, the expected behavior, the verbatim span it tests, and its source file. A process claim's question is a concrete user task that would call for the behavior. A fact claim's question asks for the fact without stating it. The script rejects a draft whose question leaks the span, asks for an explanation, names the skill, or uses a semicolon or an em dash, and asks the drafter again with the reasons. A fact question may name its subject, so it leaks only when it repeats most of the span. After three rejected drafts, the script keeps the valid claims from the last one and reports how many it dropped. A skill with several files gets one draft call per file in parallel, with the claim budget split by size.

A reviewer from another model family than the drafter then reads each new claim with the skill text. It checks that the question does not give away the expected behavior and that the skill supports the expected behavior at the span. A flagged claim goes back to the drafter once with the reviewer's reason. A claim still flagged after that is dropped, and the report lists it. A claim whose review call fails is kept and listed as unreviewed. Each claim starts scoring as soon as its own review passes.

## Arms and grades

Every answerer answers both arms of every claim, so each model's results cover the same claims. The with-skill arm gets the whole skill text in the user message. The without-skill arm gets the task alone. Neither prompt contains the expected behavior.

One judge grades each answer. It sees the task, the expected behavior, and one answer, never the arm. Lenient grading checks the general idea. Strict grading checks exact names, values, and order.

Each arm takes up to `--samples` samples (default 3), each a separate answer and grade. The majority decides. The first two samples run in parallel, and the third runs only when they disagree on either grade. A cell whose samples disagreed is marked unstable in the report.

For one answerer, at each grading level, a claim is:

| Without | With | Bucket |
|---|---|---|
| pass | pass | already known |
| pass | fail | hurts |
| fail | pass | teaches |
| fail | fail | fails both |

The claim's overall bucket is the most severe one across answerers, in the order hurts, teaches, fails both, already known. A claim is already known only when every answerer already knows it. The overall pair of buckets gives each claim a decision: keep, cut, fix, or rewrite. A process claim that would be cut is kept, because a steering instruction can make an action repeatable even when the model already knows it.

## Isolation

Every answer call starts in a new empty temporary folder. The CLI's home directory points into that folder and holds only the sign-in and a generated configuration with no skills. No call gets the repo path. Each CLI has an adapter in `scripts/novelty/clis/`:

- Claude Code runs with `--safe-mode`, no tools, no slash commands, and no MCP servers.
- Codex runs with skill instructions off, every host skill disabled by path, the code mode host and shell tools off, and a read-only sandbox. An answer that used a tool is rejected.
- Grok Build runs with its bundled skills ignored and its tools disallowed.
- opencode runs standalone with its config, data, cache, and state folders inside the temporary home, a custom agent whose prompt is the system prompt, every tool and permission denied, and the Claude Code compatibility layer off. The work folder is an empty git repository, so opencode does not search parent folders. An answer that used a tool is rejected. A subscription sign-in is imported into each call's home, and a free `opencode/` model gets none.

`run.py panel --check` asks every seat to list its skills and fails when any installed skill name comes back. Run it after changing a CLI or its version.

Every run proves the isolation:

- Each run writes a new marker word into the skill text the with-skill arm receives.
- Each answerer gets a canary question asking for the marker, once with the skill and once without. The with-skill arm must return the marker, which proves the skill text arrives. The without-skill arm must not.
- Every without-skill answer the run uses, cached or new, is searched for every marker the skill has ever had and for references to the skill's name. A reference is the name in a skill path, a slash command, backticks, `<name> skill`, `Skill(<name>)`, or `name: <name>`. A hyphenated name also counts as a bare word. A single-word name like `research` is ordinary English, so the bare word does not count.

Any hit fails the run, and the report lists it.

## Cache and reruns

The state directory defaults to `~/.cache/eval-skill`. At the start of every run, each seat answers one tiny probe, and the script records which model actually answered. Every cache key uses that model, so when an alias like `sonnet` moves to a newer model, the old answers stop matching and the claims are asked again. The report lists the model behind each seat.

Without-skill answers are keyed by model, prompt, question, and sample number. With-skill answers are also keyed by the paragraphs the claim's span covers. Grades are keyed by the judge's model and the full grading prompt. Reviews are keyed by the reviewer's model and the claim. A rerun reuses the claims from unchanged paragraphs and drafts only new or changed ones, keeping a claim's question when the new draft points at the same span. Only claims in changed paragraphs reach a model again. If an edit changes how another paragraph reads, pass a fresh `--state` for a full evaluation.

## Retries, speed, and timing

Calls run in parallel up to each CLI's `limits` entry (default 8). All skills, arms, samples, and judges share those slots. Raising the limit does not always help, because a subscription can slow every call when more run at once. The default panel keeps judging off the slowest CLI. A call that fails or passes `--timeout` is retried up to three times. A rejected reply is retried with the reason appended. A call that runs past twice the median for its kind and seat (`--hedge` before there is a median) gets one duplicate, and the first reply wins. When a judge fails, a seat from another model family grades. A seat's family comes from its model, so an opencode seat running a Claude model counts as the claude family. When an answerer still fails on a claim, that cell is missing and the report lists it. A claim no answerer scored fails the run.

The run directory holds `report.md`, `summary.json`, `calls.jsonl`, and one folder per skill. The report has the wall time, per-step start and end times, and per-call p50, p90, max, slot wait, and hedge counts.

## Rewrite gate

Without `--score-only`, the implementer rewrites each paragraph that has a cut, fix, or rewrite decision as soon as all of that paragraph's claims are scored. Kept spans must stay verbatim. The script proposes the result only when:

1. The rewritten skill is shorter.
2. The repo's em dash, semicolon, and Use when checks pass on it.
3. Every claim the original taught still passes with the rewritten skill, for every answerer and on every scale where it taught, using the same question and judge and a fresh majority vote.

A proposal then runs [task evals](EVALS.md) when `--tasks` has a file for the skill. A regression rejects it.
