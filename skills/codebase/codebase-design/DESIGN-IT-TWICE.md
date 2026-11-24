# Design it twice

Explore alternative interfaces for one deepening candidate with parallel agents. Uses the vocabulary in [SKILL.md](SKILL.md).

1. **Frame the problem** for the user, with `send_to_user` in T3, then go straight to step 2 so they read while the agents work:
   - the constraints any new interface must satisfy
   - the dependencies it relies on, and each one's category from [DEEPENING.md](DEEPENING.md)
   - a rough code sketch that makes the constraints concrete. It is an illustration, not a proposal

2. **Start the agents.** Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role) for the `implementer`. Start at least three in parallel, each with a fresh context and its own technical brief: file paths, coupling details, the dependency categories, what sits behind the seam, and the vocabulary from [SKILL.md](SKILL.md) and `GLOSSARY.md`. Give each a different constraint:
   - "Minimise the interface: one to three entry points, with the most leverage per entry point."
   - "Maximise flexibility: support many use cases and extension."
   - "Optimise for the most common caller: make the default case trivial."
   - "Design around ports and adapters", when dependencies cross the seam.

   Each agent returns:
   1. The interface: types, methods, and params, plus invariants, ordering, and error modes
   2. A usage example from a caller's side
   3. What the implementation hides behind the seam
   4. The dependency strategy and its adapters
   5. The trade-offs: where leverage is high and where it is thin

3. **Present and compare.** Show the designs one at a time, then compare them in prose by **depth**, **locality**, and **seam placement**. End with your own recommendation, or a hybrid when parts of different designs combine well. The user wants a strong read, not a menu.
