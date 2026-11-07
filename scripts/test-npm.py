#!/usr/bin/env python3
"""Exercise the Zsh npm guard with real JSON parsing and a recording npm stub."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")
NODE = shutil.which("node")
GIT = shutil.which("git")
if not ZSH or not NODE or not GIT:
    sys.exit("requires Zsh, Node.js and Git")


class NpmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="npm-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.project = self.home / "project å; literal"
        self.project.mkdir()
        self.log = self.home / "commands.jsonl"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("MISE_", "__MISE_", "ZSH", "ZDOT", "XDG_", "NODE_", "GIT_"))}
        self.env.update(HOME=str(self.home), PATH=str(self.bin),
                        NPM_TEST_LOG=str(self.log), SSH_AUTH_SOCK="fixture",
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        (self.bin / "node").symlink_to(NODE)
        for tool in ("npm", "pnpm", "yarn", "bun"):
            stub = self.bin / tool
            stub.write_text(f"#!{sys.executable}\n" + '''
import json
import os
import sys
with open(os.environ["NPM_TEST_LOG"], "a") as log:
    log.write(json.dumps({"tool": os.path.basename(sys.argv[0]),
                          "args": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
print("tool stdout")
print("tool stderr", file=sys.stderr)
sys.exit(int(os.environ.get("NPM_TEST_STATUS", "0")))
''')
            stub.chmod(0o755)
        # Source the whole tracked configuration; real OMZ is tested separately.
        (self.home / ".oh-my-zsh").mkdir()
        (self.home / ".oh-my-zsh/oh-my-zsh.sh").touch()

    def manifest(self, directory, contents):
        manifest = directory / "package.json"
        manifest.write_text(json.dumps(contents))
        return manifest

    def shell(self, *args, code='npm "$@"', cwd=None, **env):
        return subprocess.run([ZSH, "-f", "-c", 'source "$1"; shift; ' + code,
                               "npm-check", str(ROOT / "packages/zshrc/.zshrc"), *args],
                              cwd=cwd or self.project, env={**self.env, **env},
                              capture_output=True, text=True, timeout=10)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def git(self, *args):
        result = subprocess.run([GIT, *map(str, args)], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_forwarded(self, args, cwd=None, **env):
        result = self.shell(*args, cwd=cwd, **env)
        self.assertEqual(result.returncode, int(env.get("NPM_TEST_STATUS", "0")), result.stderr)
        self.assertEqual(result.stdout, "tool stdout\n")
        self.assertEqual(result.stderr, "tool stderr\n")
        self.assertEqual(self.commands()[-1], {"tool": "npm", "args": list(args),
                                               "cwd": str(cwd or self.project)})

    def assert_blocked(self, manager, cwd=None):
        before = self.commands()
        result = self.shell("install", "some package", cwd=cwd)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(f"use {manager.split('@')[0]} instead", result.stderr)
        self.assertIn("command npm", result.stderr)
        self.assertEqual(self.commands(), before)

    def test_blocks_declared_alternatives_without_modifying_manifest(self):
        for manager in ("pnpm@10.0.0", "yarn@4.0.0+sha224.abc", "bun@1.2.0", "pnpm", "yarn", "bun"):
            with self.subTest(manager=manager):
                manifest = self.manifest(self.project, {"packageManager": manager})
                before = manifest.read_bytes()
                self.assert_blocked(manager)
                self.assertEqual(list(self.project.iterdir()), [manifest])
                self.assertEqual(manifest.read_bytes(), before)

    def test_workspace_and_subdirectories_inherit_parent_declaration(self):
        self.git("init", "--quiet", self.project)
        self.manifest(self.project, {"packageManager": "pnpm@10.0.0"})
        workspace = self.project / "packages/app"
        nested = workspace / "src/deep"
        nested.mkdir(parents=True)
        self.manifest(workspace, {"name": "app"})
        self.assert_blocked("pnpm", cwd=workspace)
        self.assert_blocked("pnpm", cwd=nested)

    def test_git_root_does_not_inherit_declarations_from_outside_repository(self):
        self.git("init", "--quiet", self.project)
        self.manifest(self.home, {"packageManager": "pnpm@10.0.0"})
        nested = self.project / "packages/app/src"
        nested.mkdir(parents=True)
        for manifest in (None, {}, {"name": "app"}):
            with self.subTest(manifest=manifest):
                if manifest is not None:
                    self.manifest(self.project, manifest)
                self.assert_forwarded(("install",), cwd=self.project)
                self.assert_forwarded(("install",), cwd=nested)

    def test_nested_repository_has_its_own_boundary(self):
        self.git("init", "--quiet", self.project)
        self.manifest(self.project, {"packageManager": "pnpm@10.0.0"})
        nested = self.project / "nested"
        self.git("init", "--quiet", nested)
        self.assert_forwarded(("install",), cwd=nested)
        self.manifest(nested, {"packageManager": "bun@1.2.0"})
        self.assert_blocked("bun", cwd=nested)

    def test_linked_worktree_git_file_is_a_boundary(self):
        self.git("init", "--quiet", self.project)
        self.git("-C", self.project, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "--allow-empty", "--no-gpg-sign", "-m", "Fixture")
        worktree = self.home / "worktree å"
        self.git("-C", self.project, "worktree", "add", "--quiet", "--detach", worktree, "HEAD")
        self.assertTrue((worktree / ".git").is_file())
        self.manifest(self.home, {"packageManager": "pnpm@10.0.0"})
        nested = worktree / "src/deep"
        nested.mkdir(parents=True)
        self.assert_forwarded(("install",), cwd=nested)
        self.manifest(worktree, {"packageManager": "yarn@4.0.0"})
        self.assert_blocked("yarn", cwd=nested)

    def test_nearest_declaration_wins_including_npm(self):
        self.manifest(self.project, {"packageManager": "pnpm@10.0.0"})
        nested = self.project / "nested"
        nested.mkdir()
        self.manifest(nested, {"packageManager": "yarn@4.0.0"})
        self.assert_blocked("yarn", cwd=nested)
        self.manifest(nested, {"packageManager": "npm@11.0.0"})
        self.assert_forwarded(("install",), cwd=nested)

    def test_normal_npm_forwards_exact_arguments_streams_and_status(self):
        args = ("run", "test", "--", "space å", "", "*.js", "$(literal)", "line\nbreak")
        self.assert_forwarded(args)
        self.assert_forwarded((), NPM_TEST_STATUS="37")
        for manifest in ({}, {"packageManager": "npm@11.0.0"}, {"packageManager": "custom@1"},
                         {"packageManager": "pnpm-other@1"}, {"config": {"packageManager": "pnpm@10"}}):
            with self.subTest(manifest=manifest):
                self.manifest(self.project, manifest)
                self.assert_forwarded(args)

    def test_invalid_manifests_do_not_break_npm_or_hide_parent(self):
        manifest = self.project / "package.json"
        for contents in ("{broken", "null", "[]", '{"packageManager": 42}'):
            with self.subTest(contents=contents):
                manifest.write_text(contents)
                self.assert_forwarded(("--version",))
                self.manifest(self.home, {"packageManager": "bun@1.2.0"})
                self.assert_blocked("bun")
                (self.home / "package.json").unlink()

    def test_explicit_bypass_and_other_tools_are_unchanged(self):
        self.manifest(self.project, {"packageManager": "pnpm@10.0.0"})
        args = ("install", "space å", "", "--global")
        for tool in ("npm", "pnpm", "yarn", "bun"):
            with self.subTest(tool=tool):
                code = 'command npm "$@"' if tool == "npm" else f'{tool} "$@"'
                result = self.shell(*args, code=code, NPM_TEST_STATUS="19")
                self.assertEqual(result.returncode, 19, result.stderr)
                self.assertEqual(result.stderr, "tool stderr\n")
                self.assertEqual(self.commands()[-1], {"tool": tool, "args": list(args),
                                                       "cwd": str(self.project)})


if __name__ == "__main__":
    unittest.main()
