---
name: shrink
description: "Shorten one or more skills in parallel and check that they still teach the same behavior and pass task evals. Use when the user wants to shrink skills with the novelty method."
---

# Shrink skills

1. Resolve the requested skills. Use the current skill when the user points to it and every skill only when the user asks for all of them.
2. Ask which models and effort levels to use, then dispatch one local T3 child per skill using [the coordinator procedure](COORDINATOR.md). Score and rewrite in parallel on the same computer.
3. Run [task evals](EVALS.md) on the original and each shorter candidate. Apply the patch only when the candidate preserves taught claims, passes repo checks, and keeps every task check the original passed.
4. Report characters saved, taught claims retained, task results, elapsed time, and any candidate left unapplied.
