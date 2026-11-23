### Resume

**The work already exists. Find where it stands and continue from there.**

1. **Read.** Fetch the reference in full: body, author, comments, labels, child issues, blockers, linked PRs, and the commits on its branch. Done when you can say what the last finished step was and show the evidence for it.

2. **Match** the first row that fits.

   | What you found | Continue with |
   | --- | --- |
   | Merged or closed work | Say so and stop |
   | A map with an open ticket, or with anything left under Not yet specified | **wayfinder** with the map, to work its next decision or turn that fog into tickets |
   | A map with nothing left open | `feature` from **Spec**, after reading the map and each closed ticket's resolution into this conversation |
   | A spec with no child tickets | `feature` from **Spec**, giving `to-spec` the spec's reference so it writes only the tickets |
   | A spec with child tickets | `feature` from **Build** |
   | An open PR, or a branch with commits the default branch lacks | `change` from **Build**. Give `implement` the PR and branch to recover from, its review comments included, with the PR's issue or description as the contract. A PR the user wants merged takes this row too: `implement` verifies it as it stands, then lands it |
   | An issue in `ready-for-human` | Say why it is marked for a human, and build it only on the user's go |
   | An issue in `needs-triage` or `needs-info`, or one with no triage state that someone other than the user opened | **triage** on that issue, since nobody has checked its claim yet. Build it as it stands only when the user says to |
   | A ticket or `ready-for-agent` issue with an open blocker | Name the blocker and stop |
   | A ticket or `ready-for-agent` issue with every blocker closed | The playbook its agent brief's **Route** names, with the brief or acceptance criteria as the contract. See the routes below |
   | Any other open issue | Treat its body as the task and pick from the table in `SKILL.md` |

   A spec is an issue labelled `spec`, or one written from the `to-spec` template.

   Routes for a ticket or `ready-for-agent` issue:

   | Route | Continue with |
   | --- | --- |
   | `bug` | `bug`, with the issue as its single task |
   | `change` | `change` |
   | `feature` | `feature` from **Spec**, after reading the brief into this conversation |
   | None named | `bug` when it reports something broken whose cause nobody has named. Otherwise `change` |

3. **Say** what you found and the step you continue from. Then copy that playbook's remaining steps into the todo list and run them.

**Reply:** where the work stood, then the reply of the playbook you continued.
