---
description: Append a cleaned-up note to personal scratchpad
---
Take the user input in `$ARGUMENTS` and append it to `~/docs/scratch.md` as a single-line scratchpad note.

Rules:
- Never create or modify any `scratch.md` in the current repository.
- Do not use bash, python, date, or other shell helpers for this command.
- Use the current date from session context.
- Read and edit `~/docs/scratch.md` directly with the normal file tools.
- Rewrite the input for clarity and concision while preserving the user's intent.
- Keep the note short and scannable.
- Do not invent details that are not implied by the user.
- Keep technical names, tools, repos, and decisions intact.
- Include the current date in `YYYY-MM-DD` format.
- Use exactly this format: `- YYYY-MM-DD: note text`.

Before writing, mention that you are appending to `~/docs/scratch.md`.
