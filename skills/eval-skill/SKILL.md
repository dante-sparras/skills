---
name: eval-skill
description: "Measure what skills teach, find instructions that hurt performance, and validate candidate fixes. Use when the user wants to evaluate or improve skills with the novelty method."
---

# Evaluate skills

[`scripts/run.py`](scripts/run.py) runs the whole novelty method in one process by calling the Claude Code, Codex, Grok Build, and opencode CLIs directly. Run claim probes and task evals only through this script, never through subagents, which see the installed skills. Run every command below from the repo root.

1. Resolve the requested skills. Use the current skill when the user points to it and every skill only when the user asks for all of them.
2. Settle the [panel](#panel). Run `python skills/eval-skill/scripts/run.py panel --check`. Show the user the resolved seats and where each came from. When they want changes, show the choices from `panel --list`, apply them with the role flags, and check again. Offer `--save` for the user file or `--save --project` for this repo. A saved panel makes later runs skip this step unless the user asks for a change.
3. Run every requested skill in one command and wait for it to exit. When the shell's foreground limit is too short, start it as a background command and wait for its exit notification. Do not poll it.

   ```sh
   python skills/eval-skill/scripts/run.py run --skill <name> --skill <name> --tasks <task-dir>
   ```

   Add the same role flags used in step 2 when they were not saved. Add `--score-only` when the user asks only for scores. `--samples` sets the most samples per arm (default 3). Leave out `--tasks` when no task evals exist yet.
4. A nonzero exit means a claim stayed unscored, the isolation check failed, or a skill crashed. Report the problems and the `report.md` path. Never report scores from a run whose isolation check failed.
5. Read `report.md` from the run directory the script prints. For each skill, report what it teaches, which instructions hurt, which fail both ways, and the isolation result. Compare answerers where they differ, since every answerer answers every claim. Call out claims marked unstable, claims rejected by review, and missing cells. Say so when the panel used one model for every role.
6. A proposal with status `proposed` is shorter and keeps every taught claim. Apply it only when its task evals passed. When they did not run, write tasks per [EVALS.md](EVALS.md) and rerun, which reuses every cached answer. Review the patch for intact headings, links, and instructions no claim covered. Then run `git apply --check -p2 <patch>` and `git apply -p2 <patch>`, followed by the repo's punctuation and Use when checks.

[METHOD.md](METHOD.md) explains the claims, buckets, isolation proof, cache, and rewrite gate. Read it before changing the script or explaining a result.

## Panel

A seat is `<cli>:<model>:<effort>`. The CLI is `claude`, `codex`, `grok`, or `opencode`. An opencode model is `provider/model`, and its effort is a model variant or `default`.

The roles are the answerers, one judge per answerer model family, the drafter that splits a skill into claims, and the implementer that rewrites paragraphs. Every answerer answers both arms of every claim, and one judge grades each answer. The reviewer that checks new claims is the judge for the drafter's family.

The script resolves the panel from these layers, and later layers win:

1. The built-in default, which favors speed.
2. The user file `~/.config/skills/eval-skill.json`.
3. The project file `.skills/eval-skill.json`.
4. A file passed with `--panel`.
5. Flags: `--answerer` (repeat for more, replaces the answerers), `--judge <family>=<seat>`, `--drafter`, `--implementer`, `--parallel` for every CLI, or `--model` for one seat in every role.

```json
{
  "answerers": ["claude:sonnet:low", "codex:gpt-6.2-sol:low", "grok:grok-4.7-build-fast:low"],
  "judges": {"claude": "codex:gpt-6.2-sol:low", "gpt": "claude:sonnet:low", "grok": "codex:gpt-6.2-sol:low"},
  "drafter": "claude:sonnet:low",
  "implementer": "claude:sonnet:low",
  "limits": {"claude": {"parallel": 8}, "codex": {"parallel": 8}, "grok": {"parallel": 8}, "opencode": {"parallel": 8}}
}
```

`judges` is keyed by model family: `claude`, `gpt`, `grok`, or the family of an opencode model. The script refuses a judge from the answerer's own family unless every role uses one seat. `limits` sets concurrent calls per CLI.

The script accepts only subscription sign-ins and free models: Claude Code signed in with Claude Max (it refuses Claude Pro), Codex signed in with ChatGPT, Grok Build signed in with grok.com, and opencode with its free `opencode/` models or a provider signed in with a subscription. It removes every API key variable from the CLIs it starts. Ask the user to confirm that paid extra usage is off for each subscription, because the script cannot see that setting.
