# Handing work to the factory

The factory ships every issue labelled `ready-for-agent`, with nobody to start it. Follow this file whenever you file such an issue, or move one to that label. [tracker.md](tracker.md) has the tracker's commands.

1. **Check the factory**, once per conversation. Neither check stops you: tell the user what you found, and go on.
   - **Installed?** `t3 workflow store list skills-factory/projects/<owner>/<repo>` prints the factory's settings for the repo. With none, nothing builds the issue until `/factory` installs it.
   - **Stale?** `git diff --no-index --quiet <this folder>/factory.ts <T3 home>/workflows/skills-factory.ts` exits 1 when the installed factory differs from the one beside this file. T3 home is `~/.t3` by default. `/factory` copies the new one.
2. **File nothing twice.** Search the open issues first. Add to the one that already covers the work, and leave an issue that is already in `ready-for-agent` as it is.
3. **Write for a reader with nothing else.** A worker sees the issue, and none of this conversation. The issue carries an agent brief, per [agent-brief.md](agent-brief.md), and an agent can build it in one PR from that alone. Work bigger than one PR becomes a spec and its tickets, through `spec` and `ticket`.
4. **Follow Trust and The AI marker** in [rules.md](rules.md).
5. **Start a pass**, so the factory takes the issue now and not at its next ten-minute pass. Skip this when the factory is not installed.

   ```sh
   t3 workflow start skills-factory-dispatch --key pass/<now> --input '{"scheduledAt":"<now, as ISO 8601>","repository":"<owner>/<repo>","issues":["<number>","<number>"]}'
   ```

   Name every issue you filed or labelled. GitHub's label lists trail a new issue by some seconds, and the pass reads the issues you name by their numbers. In PowerShell, `t3` is a `.cmd` file, so write each `"` inside a JSON argument as `\"`.
6. **Tell the user** each issue you filed or labelled. The factory starts one at once when nothing blocks it, and otherwise as its last blocker merges. Everything it needs from the user waits in the ticket's thread in T3 Code, and `/factory` lists it.
