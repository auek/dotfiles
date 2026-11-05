#!/usr/bin/env python3
"""Exercise Zsh worktree workflows with real Git and disposable local remotes."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")
GIT = shutil.which("git")
FZF = shutil.which("fzf")
if not ZSH or not GIT or not FZF:
    sys.exit("requires Zsh, Git and fzf")


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worktree-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.container = self.home / "monorepo å; literal"
        self.container.mkdir()
        self.main = self.container / "main"
        self.remote = self.home / "origin.git"
        self.seed = self.home / "seed"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("GIT_", "MISE_", "__MISE_", "XDG_", "ZSH", "ZDOT", "FZF_"))}
        self.env.update(HOME=str(self.home), PATH=f"{self.bin}:/usr/bin:/bin",
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".data"),
                        XDG_STATE_HOME=str(self.home / ".state"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                        GIT_TERMINAL_PROMPT="0", SSH_AUTH_SOCK="fixture", TERM="xterm-256color")
        for key in ("ENV", "BASH_ENV", "CDPATH"):
            self.env.pop(key, None)
        (self.home / ".oh-my-zsh").mkdir()
        (self.home / ".oh-my-zsh/oh-my-zsh.sh").touch()
        # Only the interactive UI is mocked. Real Git performs every operation.
        self.fzf_log = self.home / "fzf.json"
        self.env["WORKTREE_FZF_LOG"] = str(self.fzf_log)
        (self.bin / "fzf").write_text(f"#!{sys.executable}\n" + '''
import json
import os
import sys
if sys.argv[1:] == ["--zsh"]:
    sys.exit(0)
records = sys.stdin.buffer.read().split(b"\\0")[:-1]
with open(os.environ["WORKTREE_FZF_LOG"], "w") as log:
    json.dump({"args": sys.argv[1:], "paths": [os.fsdecode(p) for p in records]}, log)
if os.environ.get("WORKTREE_FZF_CANCEL"):
    sys.exit(130)
target = os.fsencode(os.environ["WORKTREE_FZF_SELECT"])
if target not in records:
    sys.exit(1)
sys.stdout.buffer.write(target + b"\\0")
''')
        (self.bin / "fzf").chmod(0o755)
        self.git("init", "--bare", "--initial-branch=main", self.remote)
        self.git("init", "--initial-branch=main", self.seed)
        (self.seed / "app1").mkdir()
        (self.seed / "app1/file.txt").write_text("baseline\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Baseline")
        self.git("-C", self.seed, "remote", "add", "origin", self.remote)
        self.git("-C", self.seed, "push", "origin", "main")
        self.git("clone", self.remote, self.main)

    def git(self, *args, success=True):
        result = subprocess.run([GIT, *map(str, args)], env=self.env,
                                capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def shell(self, code, *args, cwd=None, success=True, **env):
        source = ROOT / "packages/zshrc/.zshrc"
        # Parse commands only after sourcing, so the real aliases expand too.
        result = subprocess.run([ZSH, "-f", "-c", 'source "$1"; shift; test_code=$1; shift; eval "$test_code"',
                                 "worktree-check", str(source), code, *map(str, args)],
                                cwd=cwd or self.main, env={**self.env, **env},
                                capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def add(self, name, branch=None):
        self.shell('gwa "$@"', name, *([branch] if branch else []))
        return self.container / name

    def branch(self, directory):
        return self.git("-C", directory, "branch", "--show-current").stdout.strip()

    def assert_cwd(self, result, directory):
        self.assertIn(f"CWD:{directory}\n", result.stdout)

    def test_status_and_list_aliases(self):
        self.add("theme1")
        result = self.shell('gst\ngwl')
        self.assertIn("## main...origin/main", result.stdout)
        self.assertIn("[theme1]", result.stdout)

    def test_new_branch_enters_sibling_without_tracking_main(self):
        result = self.shell('gwa theme1 && printf "CWD:%s\\n" "$PWD"', cwd=self.main / "app1")
        tree = self.container / "theme1"
        self.assert_cwd(result, tree)
        self.assertEqual(self.branch(tree), "theme1")
        self.assertEqual(self.git("-C", tree, "rev-parse", "HEAD").stdout,
                         self.git("-C", tree, "rev-parse", "origin/main").stdout)
        self.assertNotEqual(self.git("-C", tree, "rev-parse", "--verify", "@{upstream}",
                                     success=False).returncode, 0)
        self.shell("gpsup", cwd=tree)
        self.assertEqual(self.git("-C", tree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(),
                         "origin/theme1")

    def test_no_cd_and_distinct_branch_name(self):
        cwd = self.main / "app1"
        result = self.shell('gwa --no-cd "theme å; literal" feature/story && printf "CWD:%s\\n" "$PWD"', cwd=cwd)
        self.assert_cwd(result, cwd)
        self.assertEqual(self.branch(self.container / "theme å; literal"), "feature/story")

    def test_existing_local_branch_is_reused(self):
        self.git("-C", self.main, "branch", "local-feature")
        tree = self.add("theme1", "local-feature")
        self.assertEqual(self.branch(tree), "local-feature")

    def test_remote_branch_is_tracked_instead_of_main(self):
        self.git("-C", self.seed, "switch", "-c", "feature/remote")
        (self.seed / "remote.txt").write_text("remote feature\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Remote feature")
        self.git("-C", self.seed, "push", "origin", "feature/remote")
        self.git("-C", self.main, "fetch", "origin")
        tree = self.add("theme1", "feature/remote")
        self.assertTrue((tree / "remote.txt").is_file())
        self.assertEqual(self.git("-C", tree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(),
                         "origin/feature/remote")

    def test_custom_base_is_relative_to_original_not_current_worktree(self):
        for base in ("../worktrees", str(self.home / "absolute worktrees")):
            with self.subTest(base=base):
                self.git("-C", self.main, "config", "dotfiles.worktreeDir", base)
                expected = (self.main / base).resolve() if not base.startswith("/") else Path(base)
                name = "nested" if base.startswith("/") else "theme1"
                self.shell('gwa "$1"', name, cwd=self.main / "app1")
                self.assertTrue((expected / name / "app1").is_dir())
                self.shell('gwa second && printf "CWD:%s\\n" "$PWD"', cwd=expected / name / "app1")
                self.assertTrue((expected / "second" / "app1").is_dir())
                self.shell("gwr second", cwd=expected / name)
                # Drop the retained test branch before exercising the next layout.
                self.git("-C", self.main, "branch", "-d", "second")

    def test_add_failure_and_validation_leave_cwd_unchanged(self):
        self.add("theme1")
        cwd = self.main / "app1"
        for args in (("theme1",), ("bad/name",), ("..",), ("--force",), ("theme2", "bad branch")):
            with self.subTest(args=args):
                result = self.shell('gwa "$@"; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                                    *args, cwd=cwd, success=False)
                self.assert_cwd(result, cwd)
        self.assertFalse((self.container / "theme2").exists())

    def test_navigation_by_name_branch_and_path_from_any_subdirectory(self):
        tree = self.add("theme å; literal", "feature/story")
        for query in (tree.name, "feature/story", tree, "../../theme å; literal"):
            with self.subTest(query=query):
                result = self.shell('gwc "$1" && printf "CWD:%s\\n" "$PWD"', query, cwd=self.main / "app1")
                self.assert_cwd(result, tree)
        self.shell("gwc typo", cwd=tree, success=False)
        self.assertFalse((self.container / "typo").exists())

    def test_ambiguous_names_require_an_exact_path(self):
        tree = self.add("theme1", "branch-one")
        other = self.add("theme2", "theme1")
        result = self.shell("gwc theme1", success=False)
        self.assertIn("ambiguous", result.stderr)
        self.shell('gwc "$1"', tree)
        self.shell('gwc "$1"', other)

    def test_picker_preserves_paths_and_cancel_leaves_cwd_unchanged(self):
        tree = self.add("theme å; literal", "feature/story")
        result = self.shell('gwc && printf "CWD:%s\\n" "$PWD"', WORKTREE_FZF_SELECT=str(tree))
        self.assert_cwd(result, tree)
        listing = json.loads(self.fzf_log.read_text())
        self.assertEqual(listing["paths"], [str(self.main), str(tree)])
        self.assertIn("--read0", listing["args"])
        self.assertIn("--print0", listing["args"])
        result = self.shell('gwc; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                            WORKTREE_FZF_CANCEL="1", success=False)
        self.assert_cwd(result, self.main)

    def test_real_fzf_accepts_picker_flags_and_preserves_unusual_paths(self):
        tree = self.add("theme 'å;\n literal", "feature/story")
        (self.bin / "fzf").write_text(f'#!/bin/sh\nexec {shlex.quote(FZF)} "$@"\n')
        result = self.shell('FZF_DEFAULT_OPTS="--filter=theme" gwc && printf "CWD:%s\\n" "$PWD"')
        self.assert_cwd(result, tree)

    def test_completion_offers_directory_and_branch_names(self):
        self.add("theme1", "feature/story")
        # Exercise the candidate generation without needing an interactive ZLE.
        result = self.shell('compadd() { printf "%s\\n" "$@"; }; _gwt_complete')
        self.assertIn("theme1\n", result.stdout)
        self.assertIn("feature/story\n", result.stdout)

    def test_remove_from_inside_moves_to_main_and_keeps_branch(self):
        tree = self.add("theme1", "feature/story")
        result = self.shell('gwr theme1 && printf "CWD:%s\\n" "$PWD"', cwd=tree / "app1")
        self.assert_cwd(result, self.main)
        self.assertFalse(tree.exists())
        self.git("-C", self.main, "show-ref", "--verify", "refs/heads/feature/story")

    def test_remove_no_cd_refuses_inside_and_stays_put_outside(self):
        tree = self.add("theme1")
        result = self.shell('gwr --no-cd theme1; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                            cwd=tree / "app1", success=False)
        self.assert_cwd(result, tree / "app1")
        self.assertTrue(tree.exists())
        result = self.shell('gwr --no-cd theme1 && printf "CWD:%s\\n" "$PWD"', cwd=self.main / "app1")
        self.assert_cwd(result, self.main / "app1")
        self.assertFalse(tree.exists())

    def test_remove_refuses_main_locked_dirty_and_untracked_worktrees(self):
        self.shell("gwr main", success=False)
        tree = self.add("theme1")
        self.git("-C", self.main, "worktree", "lock", tree)
        self.shell("gwr theme1", success=False)
        self.git("-C", self.main, "worktree", "unlock", tree)
        for filename in ("app1/file.txt", "untracked.txt"):
            with self.subTest(filename=filename):
                (tree / filename).write_text("preserve me\n")
                result = self.shell('gwr theme1; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                                    cwd=tree / "app1", success=False)
                self.assert_cwd(result, tree / "app1")
                self.assertEqual((tree / filename).read_text(), "preserve me\n")
                if filename == "app1/file.txt":
                    self.git("-C", tree, "restore", filename)

    def test_gmm_fetches_and_merges_remote_main_not_stale_local_main(self):
        tree = self.add("theme1")
        old_main = self.git("-C", self.main, "rev-parse", "main").stdout
        (self.seed / "new-main.txt").write_text("latest main\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Advance main")
        self.git("-C", self.seed, "push", "origin", "main")
        result = self.shell('gmm && printf "CWD:%s\\n" "$PWD"', cwd=tree / "app1")
        self.assert_cwd(result, tree / "app1")
        self.assertTrue((tree / "new-main.txt").is_file())
        self.assertEqual(self.git("-C", self.main, "rev-parse", "main").stdout, old_main)
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "missing-remote")
        self.shell("gmm", cwd=tree, success=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
