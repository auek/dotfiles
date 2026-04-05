# Global OpenCode Rules

Use `~/docs` as personal context when relevant.

For normal coding work, prefer short-lived feature branches over long-lived shared branches. Treat `main`, `master`, and `develop` as protected branches for agent-authored commits.

Treat `~/docs/projects.md` and `~/docs/notes.md` as read-only context unless the user explicitly asks you to update them.

Use `~/docs/scratch.md` for quick capture when the user mentions an idea, follow-up, or note that is worth saving but is outside the active repository.

Prefer the custom commands `/note` for one-line notes and `/journal` for richer timestamped entries when the user is explicitly capturing something.

For `/note` and `/journal`, prefer direct file read/edit tools for `~/docs/scratch.md` and avoid shell helpers like `bash`, `python`, `date`, or `git` unless the user explicitly asks for them.

Never create or modify any `scratch.md` inside the current repository unless the user explicitly asks for that exact file.

When adding to `~/docs/scratch.md`:
- Append rather than rewrite existing notes.
- Include the date in `YYYY-MM-DD` format for each new entry.
- Keep entries short and scannable.
- Prefer a format like `- 2026-03-23: note text` unless the user asks for something more structured.

## Git workflow

- When a coherent implementation milestone is complete, the agent may create a git commit without asking first.
- A milestone commit must only happen after the agent has finished the scoped change, reviewed the diff, and run the relevant verification step for the repo (tests, lint, build, or `pre-commit` when appropriate).
- Prefer a new commit over history rewriting. Do not use `git commit --amend`, force pushes, destructive resets, or branch deletion unless the user explicitly requests them.
- Never create agent-authored commits on `main` or `master`. Commits on `develop` are allowed when appropriate.
- Never push automatically. Human review and push remain explicit handoff steps.

## Markdown preferences

- Default to portable Markdown that renders on GitHub and `markdown-preview.nvim`.
- Prefer GFM, Mermaid, and LaTeX math.
- Avoid preview-only diagram syntaxes unless explicitly requested.
