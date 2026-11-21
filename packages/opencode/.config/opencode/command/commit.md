---
description: Run the repo's checks, then commit the current changes (no push, no PR)
agent: build
---

Commit the current changes in this repository. This is the light version of
`/pr`: verify and commit, nothing else. Never push, amend, rewrite history,
open a PR, or bypass hooks (`--no-verify`).

1. Verify this is a git worktree. Abort with a clear message otherwise.
2. Inspect `git status --short`, `git diff --stat`, and the relevant diffs.
   If something is staged, commit only the staged changes. If nothing is
   staged, commit all tracked changes plus untracked files that clearly belong
   to this change. Leave out secrets, build output, and unrelated files, and
   say what you left out. If there is nothing to commit, say so and stop.
3. Run the repo's verification (tests/lint/build) before committing. Find the
   canonical command in AGENTS.md, README, Makefile, package.json, or
   equivalent. Docs-only or trivial changes may skip it. If verification
   fails, stop and report; do not commit.
4. Write the message in the repo's own style. Read AGENTS.md and
   `git log --format=%s -n 20` first.
   - Default to conventional commits (`type(scope?): subject`) with types
     feat, fix, docs, refactor, test, chore, perf, build, ci, style.
   - If recent subjects clearly follow another convention (for example a
     ticket ID prefix like `PROJ-123: ...`), follow that instead.
   - Scope is the module, package, or area touched. Reuse scopes seen in the
     history; omit it when unsure.
   - Subject: imperative mood, lowercase unless a proper noun needs otherwise,
     no trailing period, 72 characters or fewer, concrete rather than generic.
   - Title only by default. If $ARGUMENTS contains `long`, add a body of 1-4
     sentences wrapped at 72 columns that explains what changed and why.
   - No quotes, code fences, or commentary in the message.
5. Split into several commits only when the changes are clearly unrelated, or
   when $ARGUMENTS contains `split`. Otherwise make one commit.
6. Commit with `git commit`, passing the message via `-m`/`-F`. If a hook
   fails, fix the cause and make a new commit; do not skip the hook.
7. Report `git log --oneline` for the new commit(s), and the branch name.

User-provided context/overrides: $ARGUMENTS
