---
description: Append a polished journal entry to personal scratchpad
---
Take the user input in `$ARGUMENTS` and append it to `~/docs/scratch.md` as a short journal entry.

Rules:
- Never create or modify any `scratch.md` in the current repository.
- Do not use bash, python, date, git, or other shell helpers for this command.
- Use the current date from session context.
- Read and edit `~/docs/scratch.md` directly with the normal file tools.
- Rewrite the input into a concise, polished journal note while preserving the user's intent.
- Keep the entry brief, usually one short paragraph.
- Do not invent details that are not implied by the user.
- Include the current timestamp in `YYYY-MM-DD` format.
- If the note is clearly about the current git repository and the repo name is already available from context, include it in the heading as `## YYYY-MM-DD (repo-name)`.
- Otherwise use `## YYYY-MM-DD`.

Output format:
`## YYYY-MM-DD`
or
`## YYYY-MM-DD (repo-name)`

Follow the heading with a short polished paragraph.

Before writing, mention that you are appending to `~/docs/scratch.md`.
