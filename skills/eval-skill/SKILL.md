---
name: eval-skill
description: "Measure what skills teach, find instructions that hurt performance, and validate candidate fixes. Use when the user wants to evaluate or improve skills with the novelty method."
---

# Evaluate skills

[`scripts/run.py`](scripts/run.py) runs the whole novelty method in one process. It calls the Claude, Codex, and Grok subscription CLIs directly, outside T3 Code. A T3 delegate always sees the installed skills, so its without-skill answer cannot be trusted. Never run claim probes or task evals through T3 delegates.

1. Resolve the requested skills. Use the current skill when the user points to it and every skill only when the user asks for all of them.
2. Ask the user which model and effort each role uses, and suggest the [default panel](#panel). Save the answer as a panel file. When the user picks one model for every role, pass it as `--model <cli>:<model>:<effort>` instead.
3. From the repo root, run every requested skill in one command and wait for it to exit. When the shell's foreground limit is too short, start it as a background command and wait for its exit notification. Do not poll it.

   ```sh
   python skills/eval-skill/scripts/run.py --skill <name> --skill <name> --panel <panel.json> --tasks <task-dir>
   ```

   Add `--score-only` when the user asks only for scores. Leave out `--tasks` when no task evals exist yet.
4. A nonzero exit means a claim stayed unscored, the isolation check failed, or a skill crashed. Report the problems and the `report.md` path. Never report scores from a run whose isolation check failed.
5. Read `report.md` from the run directory the script prints. For each skill, report what it teaches, which instructions hurt, which fail both ways, and the isolation result. Give counts by answerer, since each claim runs on one answerer. Say so when the panel used one model for every role.
6. A proposal with status `proposed` is shorter and keeps every taught claim. Apply it only when its task evals passed. When they did not run, write tasks per [EVALS.md](EVALS.md) and rerun, which reuses every cached answer. Review the patch for intact headings, links, and instructions no claim covered. Then run `git apply --check -p2 <patch>` and `git apply -p2 <patch>` from the repo root, followed by the repo's punctuation and Use when checks.

[METHOD.md](METHOD.md) explains the claims, buckets, isolation proof, cache, and rewrite gate. Read it before changing the script or explaining a result.

## Panel

A seat is `<cli>:<model>:<effort>`, where the CLI is `claude`, `codex`, or `grok`. The default panel favors speed:

```json
{
  "answerers": ["claude:sonnet:low", "codex:gpt-6.2-sol:low", "grok:grok-4.7-build-fast:low"],
  "judges": {
    "claude": "codex:gpt-6.2-sol:low",
    "codex": "grok:grok-4.7-build-fast:low",
    "grok": "claude:sonnet:low"
  },
  "drafter": "claude:sonnet:low",
  "implementer": "claude:sonnet:low"
}
```

- Use at most one answerer per CLI. Each claim goes to one answerer, and both arms of that claim use it.
- `judges` maps each answerer's CLI to the seat that grades its answers. The script refuses a judge from the answerer's own family unless every role uses one seat.
- The drafter splits the skill into claims. The implementer rewrites paragraphs. Both default to the first answerer.

The script accepts only subscription sign-ins: Claude Max (it refuses Claude Pro), Codex signed in with ChatGPT, and Grok signed in with grok.com. It removes every API key variable from the CLIs it starts. Ask the user to confirm that paid extra usage is off for each subscription, because the script cannot see that setting.
