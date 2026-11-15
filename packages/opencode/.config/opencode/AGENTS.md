# Global OpenCode Rules

For normal coding work, prefer short-lived feature branches over long-lived shared branches. Treat `main` and `master` as protected branches for agent-authored commits.

## Git workflow

- When a coherent implementation milestone is complete, the agent may create a git commit without asking first.
- A milestone commit must only happen after the agent has finished the scoped change, reviewed the diff, and run the relevant verification step for the repo (tests, lint, build, or `pre-commit` when appropriate).
- Prefer a new commit over history rewriting. Do not use `git commit --amend`, force pushes, destructive resets, or branch deletion unless the user explicitly requests them.
- Never create agent-authored commits on `main` or `master`. Commits on `develop` are allowed when appropriate.

## Markdown preferences

- Default to portable Markdown that renders on GitHub and `markdown-preview.nvim`.
- Prefer GFM, Mermaid, and LaTeX math.
- Avoid preview-only diagram syntaxes unless explicitly requested.

## Browser (Playwright MCP)

- Use `playwright` (headless) by default for browsing and search. If a site returns 403 or a bot challenge, retry once with `playwright-headed`. Both share one profile, so do not run them at the same time.
- The browser profile is dedicated and must stay anonymous: never log in to any account, never enter personal or payment details, and never complete purchases, sign-ups, or subscriptions.
