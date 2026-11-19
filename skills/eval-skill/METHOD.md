# How the script runs the novelty method

The method follows Nikolai Petrov's talk on skill novelty. Split a skill into claims, ask each claim with and without the skill, grade each answer with a judge, and sort the claim by the two grades.

## Claims

The drafter splits the skill into at most 30 claims. Each claim has a question, the expected behavior, the verbatim span it tests, and its source file. A process claim's question is a concrete user task that would call for the behavior. A fact claim's question asks for the fact without stating it. The script rejects a draft whose question leaks the span, asks for an explanation, names the skill, or uses a semicolon or an em dash, and asks the drafter again with the reasons. A fact question may name its subject, so it leaks only when it repeats most of the span. After three rejected drafts, the script keeps the valid claims from the last one and reports how many it dropped. A skill with several files gets one draft call per file in parallel, with the claim budget split by size. Scoring starts as soon as a file's claims arrive.

## Arms and grades

Each claim goes to one answerer, assigned round robin. Both arms use that answerer. The with-skill arm gets the whole skill text in the user message. The without-skill arm gets the task alone. Neither prompt contains the expected behavior.

The judge sees the task, the expected behavior, and one answer, never the arm. Lenient grading checks the general idea. Strict grading checks exact names, values, and order. At each level a claim is:

| Without | With | Bucket |
|---|---|---|
| pass | pass | already known |
| pass | fail | hurts |
| fail | pass | teaches |
| fail | fail | fails both |

The pair of buckets gives each claim a decision: keep, cut, fix, or rewrite. A process claim that would be cut is kept, because a steering instruction can make an action repeatable even when the model already knows it.

## Isolation

Every answer call starts in a new empty temporary folder. The CLI's home directory points into that folder and holds only the sign-in and a generated configuration with no skills. Claude runs with `--safe-mode`, no tools, no slash commands, and no MCP servers. Codex runs with skill instructions off, every host skill disabled by path, the code mode host and shell tools off, and a read-only sandbox. An answer that used a tool is rejected. Grok runs with a temporary home, its bundled skills ignored, and its tools disallowed. No call gets the repo path.

Every run proves the isolation:

- Each run writes a new marker word into the skill text the with-skill arm receives.
- Each answerer gets a canary question asking for the marker, once with the skill and once without. The with-skill arm must return the marker, which proves the skill text arrives. The without-skill arm must not.
- Every without-skill answer the run uses, cached or new, is searched for every marker the skill has ever had and for references to the skill's name. A reference is the name in a skill path, a slash command, backticks, `<name> skill`, `Skill(<name>)`, or `name: <name>`. A hyphenated name also counts as a bare word. A single-word name like `research` is ordinary English, so the bare word does not count.

Any hit fails the run, and the report lists it.

## Cache and reruns

The state directory defaults to `~/.cache/eval-skill`. Without-skill answers are keyed by answerer, prompt, and question. With-skill answers are also keyed by the paragraphs the claim's span covers. Grades are keyed by judge and the full grading prompt. A rerun reuses the claims from unchanged paragraphs and drafts only new or changed ones, keeping a claim's question when the new draft points at the same span. Only claims in changed paragraphs reach a model again. If an edit changes how another paragraph reads, pass a fresh `--state` for a full evaluation.

## Retries, speed, and timing

Calls run in parallel up to `--parallel` per CLI (default 8). All skills, both arms, and the judges share those slots. A call that fails or passes `--timeout` is retried up to three times. A rejected reply is retried with the reason appended. A call that runs past twice the median for its kind and seat (`--hedge` before there is a median) gets one duplicate, and the first reply wins. When an answerer still fails, the claim moves to the next answerer and both arms rerun. When a judge fails, another family's seat grades. A claim still unscored after that fails the run.

The run directory holds `report.md`, `summary.json`, `calls.jsonl`, and one folder per skill. The report has the wall time, per-step start and end times, and per-call p50, p90, max, slot wait, and hedge counts.

## Rewrite gate

Without `--score-only`, the implementer rewrites each paragraph that has a cut, fix, or rewrite decision as soon as all of that paragraph's claims are scored. Kept spans must stay verbatim. The script proposes the result only when:

1. The rewritten skill is shorter.
2. The repo's em dash, semicolon, and Use when checks pass on it.
3. Every claim the original taught still passes with the rewritten skill on each scale where it taught, using the same question, answerer, and judge, with one retry.

A proposal then runs [task evals](EVALS.md) when `--tasks` has a file for the skill. A regression rejects it.
