The coordinator is stuck, and the brief says on what.

Call the Skill tool with "diagnosing-bugs" and follow it up to the root cause, in a scratch copy of the integration branch that you delete afterwards. The worktree stays as it is: the fix goes back as a plan.

- **Repeat a failed attempt** only if you can say why it would work now.
- **A fix that is the owner's decision** (scope, API shape, product behavior): give the options and your recommendation.

Report in about 15 lines:

```
Root cause:   with path:line
Red command:  the command that goes red on it
Fix plan:     steps an implementer can follow alone
Uncertain:    what is still open
```
