# Handing work to the factory

The [factory](factory.md) ships every issue labelled `ready-for-agent`, with nobody to start it. Follow this file whenever you file such an issue, or move one to that label. [tracker.md](tracker.md) has the tracker's commands.

1. **Check the factory**, once per conversation. Neither check stops you: tell the user what you found, and go on.
   - **Installed?** `t3 workflow store list skills-factory/projects/<owner>/<repo>` prints the factory's settings for the repo. With none, nothing builds the issue until `/factory` installs it.
   - **Stale?** `git diff --no-index --quiet <this folder>/factory.ts <T3 home>/workflows/skills-factory.ts` exits 1 when the installed factory differs from the one beside this file. T3 home is `~/.t3` by default. `/factory` copies the new one.
2. **File nothing twice.** Search the open issues first. Add to the one that already covers the work, and leave an issue that is already in `ready-for-agent` as it is.
3. **Write for a reader with nothing else.** A worker sees the issue, and none of this conversation. The issue carries an agent brief, per [agent-brief.md](agent-brief.md), and an agent can build it in one PR from that alone. Work bigger than one PR becomes a spec and its tickets, through `spec` and `ticket`.
4. **Follow Trust and The AI marker** in [rules.md](rules.md).
5. **Tell the user** each issue you filed or labelled. The factory starts each one within ten minutes of its last blocker closing, and everything it needs from the user waits in T3 Code's Workflows page.
