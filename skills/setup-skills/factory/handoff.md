# Handing work to the factory

The [factory](factory.md) ships every issue labelled `ready-for-agent`, with nobody to start it. Follow this file whenever you file such an issue, or move one to that label.

1. **Check the setup**, once per conversation.
   - Stop and say so when `/setup-skills` has not landed in this repo: main lacks `docs/agents/issue-tracker.md` or `docs/agents/triage-labels.md`, which `git cat-file -e origin/<default branch>:<path>` tells you.
   - `t3 workflow store get skills-factory/projects/<owner>/<repo>` prints the factory's settings for the repo. With none, go on, and tell the user that nothing builds the issue until `/setup-skills` installs the factory.
2. **File nothing twice.** Search the open issues first. Add to the one that already covers the work, and leave an issue that is already in `ready-for-agent` as it is.
3. **Write for a reader with nothing else.** A worker sees the issue, and none of this conversation. The issue carries an agent brief, per [agent-brief.md](../../triage/agent-brief.md), or it is a ticket of a spec, and an agent can build it in one PR from that alone. Work bigger than one PR goes through `plan`.
4. **Follow Trust and The AI marker** in [rules.md](rules.md).
5. **Tell the user** each issue you filed or labelled. The factory starts each one within ten minutes of its last blocker closing, and everything it needs from the user waits in T3 Code's Workflows page.
