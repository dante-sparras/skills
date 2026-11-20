---
name: eval-skill
description: "Measure what a skill teaches models, find its instructions that hurt, and propose a rewrite that keeps what it teaches. Use when asked to evaluate, benchmark, or trim a skill, to find which instructions models already know or are hurt by, or to test a rewrite of a skill."
---

# Evaluate skills

[`scripts/run.py`](scripts/run.py) runs the whole novelty method in one process by calling the Claude Code, Codex, Grok Build, and opencode CLIs directly. The novelty method asks models each instruction with and without the skill, to see what the skill adds. Run claim probes and task evals only through this script, never through subagents, which see the installed skills. Run every command below from the repo root.

1. Resolve the requested skills to directory names under `skills/`. Pass `--all` instead only when the user asks for every skill.
2. Settle the [panel](#panel). Run `python skills/eval-skill/scripts/run.py panel --check` before every run, since it also proves that no seat sees installed skills. Show the user the resolved seats and where each came from, and ask them to confirm that paid extra usage is off for each subscription the panel uses, because the script cannot see that setting. When they want changes, show the choices from `panel --list`, apply them with the role flags, and check again. Offer `--save` for the user file or `--save --project` for this repo, so later runs skip the questions about seats.
3. Run every requested skill in one command and wait for it to exit. When the shell's foreground limit is too short, start it as a background command and wait for its exit notification.

   ```sh
   python skills/eval-skill/scripts/run.py run --skill <name> --skill <name>
   ```

   Add the same role flags used in step 2 when they were not saved. Add `--score-only` when the user asks only for scores. Task evals load from `.skills/evals/<skill>.json`, and `--tasks <dir>` points elsewhere. Add `--write skills` when the user wants proposals written into this repo. The script then overwrites `skills/<name>` with each proposal whose task evals passed, and leaves every other candidate in the run directory.
4. A nonzero exit means a claim stayed unscored, the isolation check failed, or a skill crashed. Report the problems and the `report.md` path. Never report scores from a run whose isolation check failed.
5. Read `report.md` from the run directory the script prints. For each skill, report what it teaches, which instructions hurt, which fail both ways, and the isolation result. Name the dependencies both arms got, since every score is relative to them. Compare answerers where they differ, since every answerer answers every claim. Call out claims marked unstable, claims rejected by review, missing cells, failed rewrites, and fixes that still hurt. Say so when the panel used one model for every role.
6. A proposal with status `proposed` changes at least one paragraph, and every claim that passed with the original still passes with it. It may be longer than the original, so report both sizes. Offer it only when its task evals passed. When they did not run, write tasks per [EVALS.md](EVALS.md) and rerun with the same `--state`, which reuses every cached answer. Review the patch for intact headings, links, and instructions no claim covered. When the report says the proposal was written, show the user the diff under `skills/<name>`. Otherwise ask the user before applying it, then run `git apply --check -p2 <patch>` and `git apply -p2 <patch>`. Either way, run `python scripts/no-em-dashes.py skills`, `python scripts/no-semicolons.py skills`, and `python scripts/use-when-descriptions.py skills`.

[METHOD.md](METHOD.md) explains the claims, buckets, isolation proof, cache, and rewrite gate. Read it before changing the script or explaining a result.

## Panel

A seat is `<cli>:<model>:<effort>`. The CLI is `claude`, `codex`, `grok`, or `opencode`. An opencode model is `provider/model`, and its effort is a model variant or `default`.

The roles are the answerers, one judge per answerer model family, the drafter that splits a skill into claims, and the implementer that rewrites paragraphs. Every answerer answers both arms of every claim, and one judge grades each answer. The judge for the drafter's family reviews new claims, so the panel needs a judge for that family too.

The script resolves the panel from these layers, and later layers win:

1. The built-in default, which favors speed.
2. The user file `~/.config/skills/eval-skill.json`.
3. The project file `.skills/eval-skill.json`.
4. A file passed with `--panel`.
5. Flags: `--answerer` (repeat for more, replaces the answerers), `--judge <family>=<seat>`, `--drafter`, `--implementer`, `--parallel` for every CLI, or `--model` for one seat in every role.

A panel file holds `answerers`, `judges`, `drafter`, `implementer`, and `limits`, and `panel --save` writes one. `judges` is keyed by model family: `claude`, `gpt`, `grok`, or the family of an opencode model. The script refuses a judge from the answerer's own family unless every role uses one seat. `limits` sets concurrent calls per CLI.

The script accepts only subscription sign-ins and free models: Claude Code signed in with Claude Max (it refuses Claude Pro), Codex signed in with ChatGPT, Grok Build signed in with grok.com, and opencode with its free `opencode/` models or a provider signed in with a subscription. It removes every API key variable from the CLIs it starts.
