# Global OpenCode Rules

For normal coding work, prefer short-lived feature branches over long-lived shared branches. Treat `main` and `master` as protected branches for agent-authored commits.

## Git workflow

- When a coherent implementation milestone is complete, the agent may create a git commit without asking first.
- A milestone commit must only happen after the agent has finished the scoped change, reviewed the diff, and run the relevant verification step for the repo (tests, lint, build, or `pre-commit` when appropriate).
- Prefer a new commit over history rewriting. Do not use `git commit --amend`, force pushes, destructive resets, or branch deletion unless the user explicitly requests them.
- Never create agent-authored commits on `main` or `master`. Commits on `develop` are allowed when appropriate.
- The global safe-push plugin permits simple, non-force pushes to branches other than `main` and `master`, including `git push -u origin <branch>`. It blocks pushes to protected branches and all force, tag, bulk, shell-composed, or otherwise ambiguous push commands.

## Markdown preferences

- Default to portable Markdown that renders on GitHub and `markdown-preview.nvim`.
- Prefer GFM, Mermaid, and LaTeX math.
- Avoid preview-only diagram syntaxes unless explicitly requested.
