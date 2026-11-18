# When the queue pauses

A paused queue lands nothing until `land.py resume`. `land` and `status` print the reason. Act on the reason's first words:

- `trunk no longer contains the last landed commit`: someone rewound or replaced trunk. This is the user's call. Report both commits from the message as a decision. Run `resume` only after the user confirms trunk is right.
- `could not check that trunk contains the last landed commit`: `git merge-base --is-ancestor` failed for another reason. It does not say trunk was rewound. Check that `git cat-file -e <sha>` reads the commit in the checkout, then run `resume`.
- `push rejected`: the remote refused a `push` mode landing although trunk had not moved, often because of branch protection. Let the remote accept the push, or switch to `human` with `land.py init --mode human` once the queue is empty, then run `resume`.
- `push failed` or `gh pr create failed`: `human` mode could not publish `landing/e<n>` or open its PR. Fix the remote or `gh auth status`, then run `resume` and `land`.
- `cherry-pick failed`: git stopped for a reason other than a conflict. Read the quoted output, fix the cause in the repository, then run `resume`.

A pause moves every entry it was landing back to `queued`, so after `resume` the next `land` tries them again.

A command that refuses with `a check changed tracked files in the integration worktree` is not a pause. Fix the check so it leaves tracked files alone, then run `land` again.
