#!/usr/bin/env python3
"""Merge the repo's Claude Code settings baseline into ~/.claude/settings.json.

Claude Code rewrites that file whenever a setting changes (theme, tui, ...), so
it must be a real, machine-local file, not a link into the repo. Keys in
packages/claude/settings.base.json win; other keys are kept. Safe to re-run.
"""

import json
import os
from pathlib import Path
import tempfile

BASE = Path(__file__).resolve().parents[1] / "packages/claude/settings.base.json"
DEST = Path(os.environ.get("CLAUDE_SETTINGS") or Path.home() / ".claude/settings.json")


def merge(local, base):
    result = dict(local)
    for key, value in base.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    # A dangling link (the repo file moved) simply starts from the baseline.
    current = json.loads(DEST.read_text()) if DEST.is_file() else {}
    text = json.dumps(merge(current, json.loads(BASE.read_text())), indent=2) + "\n"
    # Replacing the path (not writing through it) also retires an old Stow link.
    if DEST.is_symlink() or not DEST.is_file() or DEST.read_text() != text:
        fd, tmp = tempfile.mkstemp(prefix=DEST.name + ".", dir=DEST.parent, text=True)
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, DEST)


if __name__ == "__main__":
    main()
