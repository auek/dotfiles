#!/usr/bin/env python3
"""Exercise worktree and Bash/Zsh trunk workflows with real Git and local remotes."""

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
BASH = shutil.which("bash")
GIT = shutil.which("git")
FZF = shutil.which("fzf")
if not BASH or not ZSH or not GIT or not FZF:
    sys.exit("requires Bash, Zsh, Git and fzf")


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
                    if not key.startswith(("GIT_", "MISE_", "__MISE_", "XDG_", "ZSH", "ZDOT", "FZF_", "BASH_FUNC_"))}
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

    def shell(self, code, *args, cwd=None, success=True, shell="zsh", legacy_gcm=False, legacy_gcb=False, **env):
        source = ROOT / ("packages/zshrc/.config/zsh" if shell == "zsh" else "packages/bashrc-server/.bashrc")
        runner = [ZSH, "-f", "-c"] if shell == "zsh" else [BASH, "--noprofile", "--norc", "-c"]
        load = 'source "$1/git.zsh"; source "$1/worktrees.zsh"' if shell == "zsh" else 'source "$1"'
        loader = load + '; shift; test_code=$1; shift; eval "$test_code"'
        if legacy_gcb:
            loader = 'alias gcb="git checkout -b"; ' + loader
        if legacy_gcm:
            loader = 'alias gcm="git checkout main || git checkout master"; ' + loader
            if shell == "bash":
                loader = "shopt -s expand_aliases; " + loader
        # Parse commands only after sourcing, so the real aliases expand too.
        result = subprocess.run([*runner, loader,
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

    def publish_master(self):
        self.git("-C", self.seed, "switch", "-c", "master")
        (self.seed / "master-only.txt").write_text("master trunk\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Advance master")
        self.git("-C", self.seed, "push", "origin", "master")
        self.git("-C", self.main, "fetch", "origin")

    def feature_checkout(self, name):
        checkout = self.container / name
        self.git("clone", self.remote, checkout)
        self.git("-C", checkout, "switch", "-c", "feature/topic")
        return checkout

    def branch(self, directory):
        return self.git("-C", directory, "branch", "--show-current").stdout.strip()

    def assert_cwd(self, result, directory):
        self.assertIn(f"CWD:{directory}\n", result.stdout)

    def test_status_and_list_aliases(self):
        self.add("theme1")
        result = self.shell('gst\ngwl')
        self.assertIn("## main...origin/main", result.stdout)
        self.assertIn("[theme1]", result.stdout)

    def test_add_help_is_readable_and_available_outside_a_repository(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                result = self.shell('gwa "$1"', flag, cwd=self.home)
                for section in ("Branch selection:", "Options:", "Examples:", "Location:"):
                    self.assertIn(f"\n\n{section}\n", result.stdout)
                self.assertIn("    git config --local dotfiles.worktreeDir ../worktrees\n", result.stdout)
                self.assertTrue(all(len(line) <= 80 for line in result.stdout.splitlines()))

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

    def test_new_branch_uses_master_with_valid_missing_or_dangling_head(self):
        self.publish_master()
        self.git("--git-dir", self.remote, "symbolic-ref", "HEAD", "refs/heads/master")
        self.git("-C", self.seed, "push", "origin", "--delete", "main")
        self.git("-C", self.main, "fetch", "--prune", "origin")
        expected = self.git("-C", self.main, "rev-parse", "origin/master").stdout
        # Creation from fetched refs must keep working without remote access.
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "offline-remote")
        for hint in ("master", None, "main"):
            with self.subTest(hint=hint):
                if hint is None:
                    self.git("-C", self.main, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
                else:
                    self.git("-C", self.main, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{hint}")
                name = "topic-" + (hint or "no-head")
                result = self.shell('gwa "$1" && printf "CWD:%s\\n" "$PWD"', name, cwd=self.main / "app1")
                tree = self.container / name
                self.assert_cwd(result, tree)
                self.assertEqual(self.branch(tree), name)
                self.assertEqual(self.git("-C", tree, "rev-parse", "HEAD").stdout, expected)
                self.assertTrue((tree / "master-only.txt").exists())
                self.assertNotEqual(self.git("-C", tree, "rev-parse", "--verify", "@{upstream}", success=False).returncode, 0)

    def test_new_branch_uses_cached_default_when_both_trunk_names_exist(self):
        self.publish_master()
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "offline-remote")
        for trunk in ("main", "master"):
            with self.subTest(trunk=trunk):
                self.git("-C", self.main, "remote", "set-head", "origin", trunk)
                tree = self.add("from-" + trunk)
                self.assertEqual(self.git("-C", tree, "rev-parse", "HEAD").stdout,
                                 self.git("-C", self.main, "rev-parse", "origin/" + trunk).stdout)
                self.assertEqual((tree / "master-only.txt").exists(), trunk == "master")

    def test_new_branch_ambiguous_or_missing_trunk_has_no_side_effects(self):
        self.publish_master()
        self.git("-C", self.main, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "offline-remote")
        for name, message in (("ambiguous", "both main and master"), ("missing", "no fetched origin/main or origin/master")):
            with self.subTest(name=name):
                if name == "missing":
                    for trunk in ("main", "master"):
                        self.git("-C", self.main, "update-ref", "-d", "refs/remotes/origin/" + trunk)
                cwd = self.main / "app1"
                result = self.shell('gwa "$1"; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                                    name, cwd=cwd, success=False)
                self.assertIn(message, result.stderr)
                self.assert_cwd(result, cwd)
                self.assertFalse((self.container / name).exists())
                self.assertNotEqual(self.git("-C", self.main, "show-ref", "--verify", "--quiet", "refs/heads/" + name,
                                             success=False).returncode, 0)

    def test_existing_branch_selection_works_without_trunk_or_remote_access(self):
        self.git("-C", self.main, "branch", "local-feature")
        self.git("-C", self.seed, "branch", "feature/remote")
        self.git("-C", self.seed, "push", "origin", "feature/remote")
        self.git("-C", self.main, "fetch", "origin")
        self.git("-C", self.main, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        self.git("-C", self.main, "update-ref", "-d", "refs/remotes/origin/main")
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "offline-remote")
        local_tree = self.add("local-tree", "local-feature")
        remote_tree = self.add("remote-tree", "feature/remote")
        self.assertEqual(self.branch(local_tree), "local-feature")
        self.assertEqual(self.branch(remote_tree), "feature/remote")
        self.assertEqual(self.git("-C", remote_tree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(),
                         "origin/feature/remote")

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

    def test_branch_picker_switches_and_cancel_keeps_current_branch(self):
        self.git("-C", self.main, "branch", "feature/story")
        # Real fzf filtering exercises the branch picker's tab-delimited input.
        (self.bin / "fzf").write_text(f'#!/bin/sh\nexec {shlex.quote(FZF)} "$@"\n')
        result = self.shell('FZF_DEFAULT_OPTS="--filter=feature/story" gbf && git branch --show-current')
        self.assertEqual(result.stdout.strip(), "feature/story")
        result = self.shell('FZF_DEFAULT_OPTS="--filter=missing-branch" gbf', success=False)
        self.assertEqual(self.git("-C", self.main, "branch", "--show-current").stdout.strip(), "feature/story")

    def test_branch_descriptions_are_searchable_and_stay_on_one_row(self):
        branch = "feature/JIRA-123"
        self.git("-C", self.main, "branch", branch)
        # A matching tag must not change the branch name used for config lookup.
        self.git("-C", self.main, "tag", branch)
        description = "Configure\tauthentication timeouts å\r\nHidden second line"
        self.git("-C", self.main, "config", f"branch.{branch}.description", description)
        original = self.git("-C", self.main, "config", "--get", f"branch.{branch}.description").stdout
        (self.bin / "fzf").write_text(
            f'#!/bin/sh\ntee "$HOME/branch-picker.tsv" | {shlex.quote(FZF)} "$@"\n')
        result = self.shell('FZF_DEFAULT_OPTS="--filter=authentication" gbf && git branch --show-current')
        self.assertEqual(result.stdout.strip(), branch)
        rows = [row.split("\t") for row in (self.home / "branch-picker.tsv").read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(row) == 3 and row[1] for row in rows))
        descriptions = {row[0]: row[2] for row in rows}
        self.assertEqual(descriptions[branch], "Configure authentication timeouts å ")
        self.assertEqual(descriptions["main"], "")
        self.assertEqual(self.git("-C", self.main, "config", "--get", f"branch.{branch}.description").stdout,
                         original)
        self.shell('FZF_DEFAULT_OPTS="--filter=Hidden" gbf', success=False)
        self.assertEqual(self.branch(self.main), branch)

    def test_description_helper_edits_current_or_named_branch_without_switching(self):
        branch = "feature/JIRA-323"
        self.git("-C", self.main, "branch", branch)
        editor = self.bin / "description-editor"
        editor.write_text('#!/bin/sh\nprintf "%s\\n" "$BRANCH_HINT" > "$1"\n')
        editor.chmod(0o755)
        code = ('alias gbd="git branch --delete"; source "$1/git.zsh"; '
                '[[ ${aliases[gbd]} == "git branch --delete" ]] || exit 99; '
                'shift; gbdesc "$@"')
        source = ROOT / "packages/zshrc/.config/zsh"
        for args, target, hint in (((), "main", "Current branch hint"),
                                   ((branch,), branch, "Add export button")):
            with self.subTest(branch=target):
                self.shell(code, source, *args, GIT_EDITOR=str(editor), BRANCH_HINT=hint)
                self.assertEqual(self.git("-C", self.main, "config", "--get", f"branch.{target}.description").stdout.strip(),
                                 hint)
                self.assertEqual(self.branch(self.main), "main")
        self.git("-C", self.main, "switch", "--detach")
        self.shell("gbdesc", GIT_EDITOR=str(editor), BRANCH_HINT="Do not store", success=False)

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

    def test_move_keeps_branch_edits_and_installed_dependencies(self):
        tree = self.add("old-name", "feature/story")
        source = tree / "app1/file.txt"
        source.write_text("staged change\n")
        self.git("-C", tree, "add", "app1/file.txt")
        source.write_text("unstaged change\n")
        (tree / "notes.txt").write_text("untracked notes\n")
        with (self.main / ".git/info/exclude").open("a") as stream:
            stream.write("/node_modules/\n")
        dependency = tree / "node_modules/example/index.js"
        dependency.parent.mkdir(parents=True)
        dependency.write_text("installed dependency\n")
        link = tree / "node_modules/tool"
        link.symlink_to("example/index.js")
        inode = dependency.stat().st_ino
        before = self.git("-C", tree, "status", "--porcelain").stdout
        refs = self.git("-C", tree, "show-ref", "--heads").stdout
        staged = self.git("-C", tree, "diff", "--cached").stdout
        unstaged = self.git("-C", tree, "diff").stdout
        cwd = self.main / "app1"
        result = self.shell('gwm feature/story new-name && printf "CWD:%s\\n" "$PWD"', cwd=cwd)
        renamed = self.container / "new-name"
        self.assert_cwd(result, cwd)
        self.assertFalse(tree.exists())
        self.assertEqual(self.branch(renamed), "feature/story")
        self.assertEqual(self.git("-C", renamed, "show-ref", "--heads").stdout, refs)
        self.assertEqual(self.git("-C", renamed, "status", "--porcelain").stdout, before)
        self.assertEqual(self.git("-C", renamed, "diff", "--cached").stdout, staged)
        self.assertEqual(self.git("-C", renamed, "diff").stdout, unstaged)
        self.assertEqual((renamed / "notes.txt").read_text(), "untracked notes\n")
        self.assertEqual((renamed / "node_modules/example/index.js").stat().st_ino, inode)
        self.assertEqual((renamed / "node_modules/tool").read_text(), "installed dependency\n")
        listing = self.git("-C", renamed, "worktree", "list", "--porcelain").stdout
        self.assertIn(f"worktree {renamed}\n", listing)
        self.assertNotIn(f"worktree {tree}\n", listing)
        self.assert_cwd(self.shell('gwc feature/story && printf "CWD:%s\\n" "$PWD"'), renamed)

    def test_move_follows_current_root_or_subdirectory_with_unusual_names(self):
        for index, subdirectory in enumerate(("", "app1")):
            with self.subTest(subdirectory=subdirectory):
                tree = self.add(f"old [å];\n{index}", f"feature/topic-{index}")
                name = f"new [å];\n{index}"
                result = self.shell('gwm "$1" "$2" && printf "CWD:%s\\n" "$PWD"; git status --short',
                                    tree.name, name, cwd=tree / subdirectory)
                renamed = self.container / name
                self.assert_cwd(result, renamed / subdirectory)
                self.assertEqual(self.branch(renamed), f"feature/topic-{index}")
                self.assertFalse(tree.exists())

    def test_move_bare_name_uses_source_parent_and_paths_use_original_cwd(self):
        self.git("-C", self.main, "config", "dotfiles.worktreeDir", "../worktrees")
        self.shell("gwa old-name")
        tree = self.container / "worktrees/old-name"
        # A later creation preference must not relocate existing trees implicitly.
        self.git("-C", self.main, "config", "dotfiles.worktreeDir", "../other-trees")
        self.shell("gwm old-name renamed", cwd=self.main / "app1")
        renamed = tree.parent / "renamed"
        self.assertTrue(renamed.is_dir())
        destination = self.container / "moves/relative-name"
        destination.parent.mkdir()
        cwd = self.main / "app1"
        result = self.shell('gwm "$1" ../../moves/relative-name && printf "CWD:%s\\n" "$PWD"', renamed, cwd=cwd)
        self.assert_cwd(result, cwd)
        self.assertTrue(destination.is_dir())
        absolute = self.home / "absolute parent/new-name"
        absolute.parent.mkdir()
        self.shell('gwm old-name "$1"', absolute, cwd=cwd)
        self.assertEqual(self.branch(absolute), "old-name")
        self.assertFalse(destination.exists())

    def test_move_no_cd_refuses_inside_and_stays_put_outside(self):
        tree = self.add("old-name")
        code = 'gwm --no-cd old-name new-name; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"'
        result = self.shell(code, cwd=tree / "app1", success=False)
        self.assert_cwd(result, tree / "app1")
        self.assertTrue(tree.is_dir())
        self.assertFalse((self.container / "new-name").exists())
        result = self.shell(code, cwd=self.main / "app1")
        self.assert_cwd(result, self.main / "app1")
        self.assertEqual(self.branch(self.container / "new-name"), "old-name")

    def test_move_refuses_existing_destinations_including_symlinks(self):
        tree = self.add("old-name")
        directory = self.container / "existing directory"
        directory.mkdir()
        file = self.container / "existing file"
        file.write_text("keep me\n")
        link = self.container / "existing link"
        link.symlink_to(directory, target_is_directory=True)
        broken = self.container / "broken link"
        broken.symlink_to(self.container / "absent")
        for destination in (directory, file, link, broken, str(broken) + "/", tree, tree / "nested"):
            with self.subTest(destination=destination):
                result = self.shell('gwm old-name "$1"; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                                    destination, cwd=tree / "app1", success=False)
                self.assert_cwd(result, tree / "app1")
                self.assertTrue(tree.is_dir())
        self.assertEqual(list(directory.iterdir()), [])
        self.assertEqual(file.read_text(), "keep me\n")
        self.assertTrue(link.is_symlink())
        self.assertTrue(broken.is_symlink())
        self.assertFalse((self.container / "absent").exists())

    def test_move_validation_and_git_failure_restore_cwd(self):
        for flag in ("-h", "--help"):
            self.assertIn("Usage: gwm", self.shell('gwm "$1"', flag, cwd=self.home).stdout)
        tree = self.add("old-name", "feature/story")
        for args in ((), ("old-name",), ("old-name", "new", "extra"), ("missing", "new"),
                     ("main", "new"), ("--force", "new"), ("old-name", ""),
                     ("old-name", "--force"), ("old-name", "."), ("old-name", "..")):
            with self.subTest(args=args):
                result = self.shell('gwm "$@"; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                                    *args, cwd=tree / "app1", success=False)
                self.assert_cwd(result, tree / "app1")
                self.assertTrue(tree.is_dir())
                self.assertFalse((self.container / "new").exists())
        self.git("-C", self.main, "worktree", "lock", tree)
        result = self.shell('gwm old-name new; result=$?; printf "CWD:%s\\n" "$PWD"; exit "$result"',
                            cwd=tree / "app1", success=False)
        self.assert_cwd(result, tree / "app1")
        self.assertTrue(tree.is_dir())
        self.assertFalse((self.container / "new").exists())
        self.git("-C", self.main, "worktree", "unlock", tree)
        self.add("second-tree", "old-name")
        self.assertIn("ambiguous", self.shell("gwm old-name new", success=False).stderr)

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

    def test_gcb_uses_cached_trunk_instead_of_current_branch_without_tracking(self):
        self.publish_master()
        self.git("-C", self.main, "config", "branch.autoSetupMerge", "always")
        self.git("-C", self.main, "switch", "-c", "unrelated-feature")
        (self.main / "feature-only.txt").write_text("do not inherit\n")
        self.git("-C", self.main, "add", ".")
        self.git("-C", self.main, "commit", "-m", "Unrelated work")
        self.git("-C", self.main, "remote", "set-url", "origin", self.home / "offline-remote")
        for trunk in ("main", "master"):
            with self.subTest(trunk=trunk):
                self.git("-C", self.main, "remote", "set-head", "origin", trunk)
                branch = "feature/from-" + trunk
                self.shell('if alias gcb >/dev/null 2>&1; then exit 99; fi; gcb "$1"',
                           branch, cwd=self.main / "app1", legacy_gcb=True)
                self.assertEqual(self.branch(self.main), branch)
                self.assertEqual(self.git("-C", self.main, "rev-parse", "HEAD").stdout,
                                 self.git("-C", self.main, "rev-parse", "origin/" + trunk).stdout)
                self.assertFalse((self.main / "feature-only.txt").exists())
                self.assertNotEqual(self.git("-C", self.main, "rev-parse", "@{upstream}", success=False).returncode, 0)

    def test_gcb_falls_back_to_sole_fetched_master_with_missing_or_stale_head(self):
        self.publish_master()
        self.git("-C", self.main, "update-ref", "-d", "refs/remotes/origin/main")
        for hint in (None, "main"):
            with self.subTest(hint=hint):
                if hint is None:
                    self.git("-C", self.main, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
                else:
                    self.git("-C", self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
                self.shell('gcb "$1"', "from-master-" + str(hint))
                self.assertEqual(self.git("-C", self.main, "rev-parse", "HEAD").stdout,
                                 self.git("-C", self.main, "rev-parse", "origin/master").stdout)

    def test_gcb_refuses_ambiguous_missing_existing_and_invalid_branches(self):
        for args in ((), ("main",), ("bad name",), ("--force",), ("one", "two"), ("@{-1}",)):
            with self.subTest(args=args):
                before = self.git("-C", self.main, "show-ref", "--heads").stdout
                self.shell('gcb "$@"', *args, success=False)
                self.assertEqual(self.branch(self.main), "main")
                self.assertEqual(self.git("-C", self.main, "show-ref", "--heads").stdout, before)
        self.publish_master()
        self.git("-C", self.main, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        for scenario in ("ambiguous", "missing"):
            if scenario == "missing":
                for trunk in ("main", "master"):
                    self.git("-C", self.main, "update-ref", "-d", "refs/remotes/origin/" + trunk)
            before = self.git("-C", self.main, "show-ref", "--heads").stdout
            result = self.shell("gcb new-topic", success=False)
            self.assertIn("both main and master" if scenario == "ambiguous" else "run git fetch origin first", result.stderr)
            self.assertEqual(self.git("-C", self.main, "show-ref", "--heads").stdout, before)

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
        before = self.git("-C", tree, "rev-parse", "HEAD").stdout
        self.shell("gmm", cwd=tree, success=False)
        self.assertEqual(self.git("-C", tree, "rev-parse", "HEAD").stdout, before)

    def test_gcm_checks_out_local_main_or_master_without_origin(self):
        for shell in ("zsh", "bash"):
            for trunk in ("main", "master"):
                with self.subTest(shell=shell, trunk=trunk):
                    checkout = self.container / f"local-{shell}-{trunk}"
                    self.git("init", "-b", trunk, checkout)
                    (checkout / "file.txt").write_text("local repository\n")
                    self.git("-C", checkout, "add", ".")
                    self.git("-C", checkout, "commit", "-m", "Baseline")
                    self.git("-C", checkout, "switch", "-c", "feature/topic")
                    self.shell("gcm --quiet", shell=shell, cwd=checkout)
                    self.assertEqual(self.branch(checkout), trunk)

    def test_gcm_uses_cached_default_and_tracks_origin_when_needed(self):
        self.publish_master()
        for shell in ("zsh", "bash"):
            for trunk in ("main", "master"):
                with self.subTest(shell=shell, trunk=trunk):
                    checkout = self.feature_checkout(f"default-{shell}-{trunk}")
                    self.git("-C", checkout, "remote", "set-head", "origin", trunk)
                    self.git("-C", checkout, "remote", "set-url", "origin", self.home / "offline-remote")
                    self.shell("gcm", shell=shell, cwd=checkout / "app1")
                    self.assertEqual(self.branch(checkout), trunk)
                    self.assertEqual(self.git("-C", checkout, "rev-parse", "HEAD").stdout,
                                     self.git("-C", checkout, "rev-parse", "origin/" + trunk).stdout)
                    self.assertEqual(self.git("-C", checkout, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(),
                                     "origin/" + trunk)

    def test_gcm_refuses_ambiguous_or_missing_trunks_without_changing_branches(self):
        self.publish_master()
        for shell in ("zsh", "bash"):
            for scenario in ("ambiguous", "missing"):
                with self.subTest(shell=shell, scenario=scenario):
                    checkout = self.feature_checkout(f"{scenario}-{shell}")
                    self.git("-C", checkout, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
                    if scenario == "missing":
                        self.git("-C", checkout, "branch", "-d", "main")
                        for trunk in ("main", "master"):
                            self.git("-C", checkout, "update-ref", "-d", "refs/remotes/origin/" + trunk)
                    self.git("-C", checkout, "remote", "set-url", "origin", self.home / "offline-remote")
                    before = self.git("-C", checkout, "show-ref", "--heads").stdout
                    result = self.shell("gcm", shell=shell, cwd=checkout, success=False)
                    self.assertIn("both main and master" if scenario == "ambiguous" else "no main or master", result.stderr)
                    self.assertEqual(self.branch(checkout), "feature/topic")
                    self.assertEqual(self.git("-C", checkout, "show-ref", "--heads").stdout, before)

    def test_gcm_checkout_failure_does_not_try_the_other_branch(self):
        for shell in ("zsh", "bash"):
            with self.subTest(shell=shell):
                checkout = self.feature_checkout("conflict-" + shell)
                self.git("-C", checkout, "branch", "master")
                self.git("-C", checkout, "switch", "main")
                file = checkout / "app1/file.txt"
                file.write_text("main branch change\n")
                self.git("-C", checkout, "add", ".")
                self.git("-C", checkout, "commit", "-m", "Advance local main")
                self.git("-C", checkout, "switch", "feature/topic")
                file.write_text("preserve unsaved feature edits\n")
                self.shell("gcm", shell=shell, cwd=checkout, success=False)
                self.assertEqual(self.branch(checkout), "feature/topic")
                self.assertEqual(file.read_text(), "preserve unsaved feature edits\n")

    def test_gcm_replaces_legacy_alias_when_sourcing(self):
        for shell in ("zsh", "bash"):
            with self.subTest(shell=shell):
                checkout = self.feature_checkout("reload-" + shell)
                self.shell('if alias gcm >/dev/null 2>&1; then exit 99; fi; gcm',
                           shell=shell, legacy_gcm=True, cwd=checkout)
                self.assertEqual(self.branch(checkout), "main")

    def test_gmm_merges_fresh_master_in_a_master_only_repository(self):
        self.git("-C", self.seed, "branch", "-m", "main", "master")
        self.git("-C", self.seed, "push", "origin", "master")
        self.git("--git-dir", self.remote, "symbolic-ref", "HEAD", "refs/heads/master")
        self.git("-C", self.seed, "push", "origin", "--delete", "main")
        checkout = self.container / "master clone"
        self.git("clone", self.remote, checkout)
        self.git("-C", checkout, "switch", "-c", "feature/topic")
        old_master = self.git("-C", checkout, "rev-parse", "master").stdout
        (self.seed / "new-master.txt").write_text("latest master\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Advance master")
        self.git("-C", self.seed, "push", "origin", "master")
        result = self.shell('gmm && printf "CWD:%s\\n" "$PWD"', cwd=checkout / "app1")
        self.assert_cwd(result, checkout / "app1")
        self.assertTrue((checkout / "new-master.txt").is_file())
        self.assertEqual(self.branch(checkout), "feature/topic")
        self.assertEqual(self.git("-C", checkout, "rev-parse", "master").stdout, old_master)

    def test_gmm_refreshes_stale_head_and_prefers_default_master_when_both_exist(self):
        tree = self.add("theme1")
        self.assertEqual(self.git("-C", tree, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").stdout.strip(),
                         "origin/main")
        self.git("-C", self.seed, "switch", "-c", "master")
        (self.seed / "master-default.txt").write_text("default is master\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Advance default master")
        self.git("-C", self.seed, "push", "origin", "master")
        self.git("--git-dir", self.remote, "symbolic-ref", "HEAD", "refs/heads/master")
        self.shell("gmm", cwd=tree)
        self.assertTrue((tree / "master-default.txt").is_file())
        self.assertEqual(self.git("-C", tree, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").stdout.strip(),
                         "origin/master")
        self.assertEqual(self.git("-C", tree, "rev-parse", "HEAD").stdout,
                         self.git("-C", self.seed, "rev-parse", "master").stdout)

    def test_gmm_stops_when_remote_head_cannot_be_determined(self):
        before = self.git("-C", self.main, "rev-parse", "HEAD").stdout
        self.git("--git-dir", self.remote, "symbolic-ref", "HEAD", "refs/heads/missing")
        self.shell("gmm", success=False)
        self.assertEqual(self.git("-C", self.main, "rev-parse", "HEAD").stdout, before)

    def test_gmm_rejects_a_default_branch_other_than_main_or_master(self):
        self.git("-C", self.seed, "switch", "-c", "develop")
        (self.seed / "develop-only.txt").write_text("do not merge this branch\n")
        self.git("-C", self.seed, "add", ".")
        self.git("-C", self.seed, "commit", "-m", "Advance develop")
        self.git("-C", self.seed, "push", "origin", "develop")
        self.git("--git-dir", self.remote, "symbolic-ref", "HEAD", "refs/heads/develop")
        before = self.git("-C", self.main, "rev-parse", "HEAD").stdout
        result = self.shell("gmm", success=False)
        self.assertIn("expected main or master", result.stderr)
        self.assertEqual(self.git("-C", self.main, "rev-parse", "HEAD").stdout, before)
        self.assertFalse((self.main / "develop-only.txt").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
