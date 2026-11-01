#!/usr/bin/env python3
"""Run the same named checks locally and in CI; missing prerequisites are errors."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("static", "shell", "editor", "toolchain", "runtime"))
    parser.add_argument("--fixtures", type=Path, help="prepared by scripts/prepare-test-fixtures.py")
    args = parser.parse_args()
    env = os.environ.copy()
    commands = []
    required = {"static": ["bash", "zsh"], "shell": ["zsh", "tmux"],
                "editor": ["stow", "rg", "shellcheck"], "toolchain": ["zsh", "stow"]}
    suites = ["shell", "editor", "toolchain"] if args.suite == "runtime" else [args.suite]
    if args.suite != "static":
        if not args.fixtures or not (args.fixtures / "ready.json").is_file():
            parser.error("prepare fixtures first; pass their directory with --fixtures")
        fixtures = args.fixtures.resolve()
        inputs = [ROOT / "scripts/test-fixtures.json", ROOT / "scripts/prepare-test-fixtures.py",
                  ROOT / "packages/nvim/.config/nvim/lazy-lock.json", ROOT / "packages/mise/.config/mise/config.toml"]
        identity = hashlib.sha256(b"".join(path.read_bytes() for path in inputs)).hexdigest()
        if json.loads((fixtures / "ready.json").read_text())["identity"] != identity:
            parser.error("fixtures are stale; prepare a fresh directory with the current pins")
        env["PATH"] = str(fixtures / "bin") + os.pathsep + env["PATH"]
        env["DOTFILES_TEST_FIXTURES"] = str(fixtures)
    missing = sorted({tool for suite in suites for tool in required[suite]
                      if not shutil.which(tool, path=env["PATH"])})
    if missing:
        parser.error("missing required tools: " + ", ".join(missing))

    def script(name, *arguments):
        commands.append([sys.executable, str(ROOT / "scripts" / name), *map(str, arguments)])

    if "static" in suites:
        for path in (ROOT / "scripts").glob("*.py"):
            ast.parse(path.read_text(), filename=str(path))
        bash_files = [ROOT / "setup.sh", *sorted((ROOT / "scripts").glob("*.sh")),
                      *sorted((ROOT / "docker").glob("*.sh")),
                      *sorted((ROOT / "packages/themes/.local/bin").iterdir())]
        commands.extend([["bash", "-n", str(path)] for path in bash_files])
        commands.extend([["zsh", "-n", str(ROOT / path)] for path in
                         ("packages/zshrc/.zshrc", "packages/zprofile/.zprofile")])
        script("generate-themes.py", "check")
    if "shell" in suites:
        for name in ("test-runtime.py", "test-tmx.py", "test-br.py", "test-hyprland-bootstrap.py"):
            script(name)
    if "editor" in suites:
        script("test-nvim.py", fixtures / "bin/nvim", fixtures / "plugins", fixtures / "mason", fixtures / "parsers")
        script("test-nvim-project-tools.py", fixtures / "bin/nvim", fixtures / "plugins/lazy.nvim",
               fixtures / "plugins/conform.nvim", fixtures / "plugins/nvim-lint",
               *(fixtures / name for name in ("prettier-2", "prettier-3", "eslint-8", "eslint-9")))
    if "toolchain" in suites:
        script("test-mise.py", fixtures / "bin/mise", fixtures / "node", fixtures / "other-node",
               fixtures / "mise-data/installs/aqua-neovim-neovim")
    failures = []
    for command in commands:
        print("\n>>> " + " ".join(command), flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, timeout=600)
            if result.returncode:
                failures.append(" ".join(command))
        except subprocess.TimeoutExpired:
            failures.append("TIMEOUT: " + " ".join(command))
    print(f"\n{args.suite}: {len(commands) - len(failures)}/{len(commands)} commands passed", flush=True)
    for failure in failures:
        print("FAILED: " + failure, file=sys.stderr)
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
