---
description: Push the current branch and open a GitHub PR with a commit-derived title and body
agent: build
---

Open a pull request for the current branch against its GitHub remote.

1. Verify this is a git worktree with a GitHub remote (`gh repo view`).
   Abort with a clear message otherwise.
2. Resolve the base branch (remote default via
   `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`, falling
   back to main/master).
3. Refuse to run on a protected/base branch. If HEAD is main/master with
   uncommitted work, abort and suggest `git switch -c <feature>`.
4. Inspect `git status --short` and `git diff`. Commit uncommitted work that
   clearly belongs to this change: split logically, follow the repo's commit
   style (check AGENTS.md and recent `git log --oneline`), never amend or
   rewrite history.
5. Run the repo's verification before opening the PR (tests/lint/build).
   Find the canonical command in AGENTS.md, README, Makefile, or package.json.
   Docs-only/trivial changes may skip it. If verification fails, stop and
   report; do not open the PR.
6. Compare `git log --oneline <base>..HEAD`. If there are no new commits,
   abort (nothing to PR).
7. Push: `git push -u origin HEAD`.
8. Create with `gh pr create`, title from the branch's commits (or the user's
   $ARGUMENTS), body as a concise per-commit bullet summary. If a PR already
   exists for the branch, update it with `gh pr edit` instead.
9. Report the PR URL.

User-provided context/overrides: $ARGUMENTS
