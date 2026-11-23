### Feature

**More than one PR, or a decision still open. A planner settles the design with the user and puts it on the tracker. Then workers build from the tickets.**

1. **Spec.** Start a planner that runs **interview**, then **to-spec**, in one thread, so the spec and its tickets build on what the interview settled.
   - Point it at any decision that lives elsewhere: a map and its closed tickets, or a research note. A fact from outside the repo goes to **research**.
   - When the task arrived as a written spec or plan, it skips the interview and gives **to-spec** that reference, which then writes only the tickets.

   Done when the planner returns the spec's reference, with the breakdown approved by the user and every ticket published. If the breakdown is one ticket, re-route to `change` with that ticket as the contract.
2. **Build.** Run **implement** with the spec reference. Done when every PR has landed, or holds a passing verdict and waits on the merge list.
3. **Hand over.** When `implement` stops with a merge list, the next session starts with `/auto-mode <spec reference>` once the user has merged.

**Reply:** the spec and ticket links, each PR with its verdict and whether it landed or waits on the merge list, the follow-ups the verifiers reported, and the command that continues the work.
