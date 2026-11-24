---
name: improve-codebase-architecture
description: "Scan a codebase for deepening opportunities, present them as a visual HTML report, then interview the person about the one they pick. Use when a person wants architectural friction found in a codebase or subsystem and refactor candidates to choose from before planning one."
disable-model-invocation: true
---

# Improve codebase architecture

Find architectural friction and propose **deepening opportunities**: refactors that turn shallow modules into deep ones, for testability and for agents finding their way.

Two vocabularies, used exactly:

- **Architecture**: call the Skill tool with "codebase-design" for its terms and principles. Say module, interface, seam, and adapter, where others say component, API, or boundary.
- **Domain**: read `GLOSSARY.md`. If it defines "Order", write "the Order intake module", not "the FooBarHandler" or "the Order service".

## Steps

1. **Scope.** Deepening pays off when the module changes again, so look where change happens.
   - Take the direction the user named: a module, a subsystem, a pain point.
   - Otherwise walk back through `git log --oneline` for the hot spots, the files and areas that keep coming up. If changes are scattered, widen the net.

2. **Explore.** Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) and start a fresh `explorer` to walk the code for friction:
   - Understanding one concept means bouncing between many small modules.
   - A module is **shallow**: its interface is nearly as complex as its implementation.
   - Pure functions were extracted for testability, and the real bugs hide in how they are called.
   - Tightly coupled modules leak across their seams.
   - Code is untested, or hard to test through its current interface.

   Apply the **deletion test** to each suspect: a module whose deletion would spread complexity across its callers is worth keeping, and one whose deletion makes complexity vanish is a candidate.

3. **Report.** Write the candidates as one HTML page, per [HTML-REPORT.md](HTML-REPORT.md), to `<tmpdir>/architecture-review-<timestamp>.html`, so nothing lands in the repo. The temp dir is `$TMPDIR`, else `/tmp`, or `%TEMP%` on Windows. Show it in the thread with `html_preview`, then `html_render`.

   Propose no interfaces yet. Ask: "Which of these would you like to explore?"

4. **Interview.** Once the user picks, call the Skill tool with "interview" and walk the decision tree: constraints, dependencies, the shape of the deepened module, what sits behind the seam, which tests survive. As decisions settle:
   - A term is new or sharpened: call the Skill tool with "domain-modeling" so it lands in `GLOSSARY.md`.
   - The user wants to compare interfaces: follow [Design It Twice](../codebase-design/DESIGN-IT-TWICE.md).

   Done when the user has a design they want built. Say in one line the task that would build it.
