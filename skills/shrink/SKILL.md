---
name: shrink
description: "Shorten one or more skills in parallel and verify that they still teach the same behavior. Use when the user wants to shrink skills with the novelty method."
---

# Shrink skills

1. Resolve the requested skills. Use the current skill when the user points to it and every skill only when the user asks for all of them.
2. Dispatch one T3 child per skill using [the coordinator procedure](COORDINATOR.md). Score and rewrite in parallel across the laptop and desktop. Keep each skill on its assigned machine on later runs to reuse its cache.
3. Apply each verified shorter patch after checking the diff against its original. Keep the original when the rewrite loses taught behavior, fails repo checks, or produces no reduction.
4. Report characters saved per skill, taught claims retained, elapsed time, and any skill you could not shrink.
