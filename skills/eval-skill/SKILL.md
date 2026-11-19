---
name: eval-skill
description: "Measure what skills teach, find instructions that hurt performance, and validate candidate fixes. Use when the user wants to evaluate or improve skills with the novelty method."
---

# Evaluate skills

1. Resolve the requested skills. Use the current skill when the user points to it and every skill only when the user asks for all of them.
2. Ask which models and effort levels to use, then dispatch one local T3 child per skill using [the coordinator procedure](COORDINATOR.md). Score and rewrite in parallel on the same computer.
3. Run [task evals](EVALS.md) on the original and each shorter candidate. Apply the patch only when the candidate preserves taught claims, passes repo checks, and keeps every task check the original passed.
4. Report what each skill teaches, which instructions hurt performance, and what changed. Include task results and explain why any candidate was left unapplied.
