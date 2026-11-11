#!/usr/bin/env python3
"""Daily Stow/shell/tmux/theme workflows using tracked configs and real Oh My Zsh."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from test_support import stop_tmux

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(os.environ["DOTFILES_TEST_FIXTURES"])
TMUX = shutil.which("tmux")


class MakeStowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-restow-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo, self.home = base / "repo", base / "home"
        shutil.copytree(ROOT / "packages", self.repo / "packages")
        shutil.copy2(ROOT / "Makefile", self.repo / "Makefile")
        self.home.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("XDG_", "MAKE", "MFLAGS", "STOW_"))}
        for key in ("INPUTRC", "BASH_ENV", "ENV"):
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), PATH="/usr/bin:/bin")
        self.current = self.home / ".local/state/dotfiles/theme/current"
        self.current.parent.mkdir(parents=True)
        self.selection = self.repo / "packages/themes/.local/share/dotfiles/themes/gruvbox"
        self.current.symlink_to(self.selection, target_is_directory=True)
        # Existing selections must not be reinitialized. Poison the copied
        # command so even a regression cannot contact host reload services.
        (self.repo / "packages/themes/.local/bin/theme-set").write_text("#!/bin/sh\nexit 99\n")

    def make(self, target, success=True):
        result = subprocess.run(["make", target], cwd=self.repo, env=self.env,
                                capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_bash_clear_shortcut_in_workstation_profile(self):
        self.make("stow")
        self.assertTrue((self.home / ".inputrc").is_symlink())
        result = subprocess.run(["bash", "--noprofile", "--norc", "-ic", "bind -q clear-screen"],
                                cwd=self.home, env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"\\ek"', result.stdout)

    def test_repeat_restow_refreshes_links_and_preserves_local_state(self):
        local_files = {
            ".config/nvim/local.lua": "return {servers={cssls=false}}\n",
            ".config/mise/config.local.toml": '[tools]\nnode = "lts"\n',
            ".config/hypr/hyprland.lua": '-- local desktop preferences\n',
            ".config/tmx/init.zsh": "# local session hook\n",
            ".zshrc.private": "# local shell preferences\n",
            ".tmux.conf.local": "# local tmux preferences\n",
        }
        for name, contents in local_files.items():
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        foot = self.home / ".config/foot/foot.ini"
        foot.parent.mkdir()
        foot_source = self.repo / "packages/foot/.config/foot/foot.ini"
        foot.symlink_to(foot_source)
        source = self.repo / "packages/nvim/.config/nvim/lua/config"
        old, removed = source / "old.lua", source / "removed.lua"
        old.write_text("-- renamed after pull\n")
        removed.write_text("-- deleted after pull\n")
        self.make("stow")
        recovery = self.home / ".config/tmux/dotfiles-recovery.conf"
        self.assertTrue(recovery.is_symlink())
        self.assertEqual(recovery.resolve(), self.repo / "packages/tmux/.config/tmux/dotfiles-recovery.conf")
        old.rename(source / "new.lua")
        removed.unlink()
        (source / "added.lua").write_text("-- added after pull\n")
        for _ in range(2):
            self.make("restow")
            config = self.home / ".config/nvim/lua/config"
            for name in ("old.lua", "removed.lua"):
                self.assertFalse(os.path.lexists(config / name), name)
            for name in ("new.lua", "added.lua"):
                self.assertTrue((config / name).is_symlink())
                self.assertEqual((config / name).resolve(), source / name)
            for name, contents in local_files.items():
                self.assertFalse((self.home / name).is_symlink(), name)
                self.assertEqual((self.home / name).read_text(), contents)
            self.assertEqual(self.current.readlink(), self.selection)
            self.assertEqual(foot.readlink(), foot_source)
            for name in ("waybar", "wofi", "mako"):
                self.assertFalse((self.home / ".config" / name).exists(), name)
            self.assertFalse((self.home / ".config/hypr/dotfiles.lua").exists())
        # A newly tracked path must not overwrite a machine-local file.
        conflict = self.home / ".config/nvim/lua/config/conflict.lua"
        conflict.write_text("-- preserve local file\n")
        (source / "conflict.lua").write_text("-- shared file\n")
        self.make("restow", success=False)
        self.assertFalse(conflict.is_symlink())
        self.assertEqual(conflict.read_text(), "-- preserve local file\n")
        self.assertEqual((source / "conflict.lua").read_text(), "-- shared file\n")

    def test_optional_includes_default_and_xdg_local_preferences(self):
        optional = {
            "opencode": ".config/opencode/opencode.jsonc",
            "claude": ".claude/settings.json",
            "espanso": ".config/espanso/config/default.yml",
        }
        for target in ("stow", "restow"):
            self.make(target)
            for name in optional.values():
                self.assertFalse(os.path.lexists(self.home / name), name)
        config = self.home / ".config/dotfiles/local.mk"
        config.parent.mkdir()
        contents = "STOW_INCLUDE = opencode claude espanso\n"
        config.write_text(contents)
        for target in ("stow", "restow"):
            self.make(target)
            for package, name in optional.items():
                self.assertTrue((self.home / name).is_symlink(), name)
                self.assertEqual((self.home / name).resolve(), self.repo / "packages" / package / name)
        # The local preference stays ordinary and follows XDG_CONFIG_HOME.
        xdg = self.home / "custom-config"
        self.env["XDG_CONFIG_HOME"] = str(xdg)
        moved = xdg / "dotfiles/local.mk"
        moved.parent.mkdir(parents=True)
        config.rename(moved)
        self.make("unstow")
        for name in optional.values():
            self.assertFalse(os.path.lexists(self.home / name), name)
        self.make("restow")
        moved.write_text("STOW_INCLUDE =\n")
        self.make("restow")
        for name in optional.values():
            self.assertTrue((self.home / name).is_symlink(), "Dropping an include removed " + name)
        moved.write_text(contents)
        self.make("unstow")
        self.assertFalse(moved.is_symlink())
        self.assertEqual(moved.read_text(), contents)
        self.assertFalse(os.path.lexists(self.home / ".config/nvim/init.lua"))
        for name in optional.values():
            self.assertFalse(os.path.lexists(self.home / name), name)


class RuntimeHome(unittest.TestCase):
    home_prefix = "dotfiles runtime "

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=self.home_prefix)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("MISE_", "__MISE_", "TMUX", "XDG_", "ZSH", "ZDOT", "SSH_"))}
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".data"), XDG_STATE_HOME=str(self.home / ".state"),
                        XDG_CACHE_HOME=str(self.home / ".cache"), TERM="xterm-256color",
                        PATH=f"{self.bin}:{FIXTURES / 'bin'}:/usr/bin:/bin")
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_VTNR", "ENV", "BASH_ENV"):
            self.env.pop(key, None)
        for package, filename in (("zshrc", ".zshrc"), ("zprofile", ".zprofile"), ("tmux", ".tmux.conf")):
            shutil.copy2(ROOT / "packages" / package / filename, self.home / filename)
        shutil.copytree(ROOT / "packages/zshrc/.config/zsh", self.home / ".config/zsh")
        recovery = self.home / ".config/tmux/dotfiles-recovery.conf"
        recovery.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "packages/tmux/.config/tmux/dotfiles-recovery.conf", recovery)
        (self.home / ".oh-my-zsh").symlink_to(FIXTURES / "ohmyzsh", target_is_directory=True)
        (self.home / ".ssh").mkdir()
        (self.home / ".zshenv").write_text("zstyle ':omz:update' mode disabled\n"
                                           "zstyle :omz:plugins:ssh-agent quiet yes\n")
        (self.home / ".zshrc.private").write_text("export DOTFILES_LOCAL=loaded\n")
        # Agent/device/desktop access is an external boundary; no host services.
        self.mock("ssh-agent", '''printf "SSH_AUTH_SOCK='%s/mock-agent'; export SSH_AUTH_SOCK;\\n" "$HOME"''')
        self.mock("ssh-add", "exit 0")
        self.mock("ddcutil", 'echo unexpected-monitor-access >> "$HOME/unexpected"; exit 1')
        themes = self.home / ".local/share/dotfiles/themes"
        shutil.copytree(ROOT / "packages/themes/.local/share/dotfiles/themes", themes)
        self.current = self.home / ".local/state/dotfiles/theme/current"
        self.current.parent.mkdir(parents=True)
        self.current.symlink_to(themes / "everforest", target_is_directory=True)
        self.socket = self.home / "tmux.sock"
        self.addCleanup(self.stop_server)

    def stop_server(self):
        stop_tmux(TMUX, self.socket, self.env)

    def mock(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_checked(self, *args):
        result = subprocess.run(args, cwd=self.home, env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.stdout.strip()

    def tmux(self, *args):
        return self.run_checked(TMUX, "-S", str(self.socket), "-f", str(self.home / ".tmux.conf"), *args)

    def mock_theme_services(self):
        # Route theme-set to this private server, never host services.
        self.mock("tmux", 'if [ "$1" = info ]; then exit 0; fi\n'
                  f'exec {shlex.quote(TMUX)} -S {shlex.quote(str(self.socket))} "$@"')
        for name in ("pgrep", "hyprctl", "systemctl"):
            self.mock(name, "exit 1")
        for name in ("pkill", "makoctl", "foot-reload"):
            self.mock(name, "exit 0")


class RuntimeTests(RuntimeHome):
    def test_shell_startup_completion_and_local_override(self):
        (self.bin / "fzf").symlink_to(shutil.which("fzf"))
        for flags in ("-lc", "-ic", "-lic"):
            with self.subTest(flags=flags):
                code = 'node --version && nvim --version >/dev/null || exit; '
                if "i" in flags:
                    code += ('[[ "$DOTFILES_LOCAL" == loaded ]] || exit 1; '
                             '(( $+functions[compdef] && $+functions[_zsh_autosuggest_start] )) || exit 2; '
                             '[[ $(bindkey "\\ek") == *clear-screen ]] || exit 3; '
                             'for name in npm open br tmx gcb gcm gmm gwc gwa gwr gsuggest gbf; do '
                             '(( $+functions[$name] )) || { print -u2 "Missing shell function: $name"; exit 4; }; done; '
                             '[[ $(bindkey "[D") != *backward-word && $(bindkey "[C") != *forward-word ]] || exit 5; '
                             '[[ $(bindkey "\\e\\e[D") == *backward-word && $(bindkey "\\e\\e[C") == *forward-word ]] || exit 6; '
                             'tmx --help || exit; ')
                code += 'print startup-ok'
                self.assertIn("startup-ok", self.run_checked("zsh", flags, code))
        self.assertFalse((self.home / "unexpected").exists())

    def test_linked_entrypoint_loads_modules_before_restow_and_private_overrides_last(self):
        package = self.home / "checkout with spaces/zshrc"
        (package / ".config").mkdir(parents=True)
        (self.home / ".zshrc").rename(package / ".zshrc")
        (self.home / ".config/zsh").rename(package / ".config/zsh")
        (self.home / ".zshrc").symlink_to(package / ".zshrc")
        with (self.home / ".zshrc.private").open("a") as stream:
            stream.write('tmx() { print local-tmx; }\n')
        # Neither a changed XDG root nor the cwd may redirect shared modules.
        self.env["XDG_CONFIG_HOME"] = str(self.home / "custom-config")
        self.assertEqual(self.run_checked("zsh", "-ic",
                         'source ~/.zshrc; (( $+functions[gsuggest] && $+functions[gwc] )) || exit 1; '
                         '(( ! $+parameters[_dotfiles_zsh_dir] )) || exit 2; tmx'), "local-tmx")

    def test_agent_startup_is_owned_by_oh_my_zsh(self):
        self.mock("ssh-agent", 'echo start >> "$HOME/agent-calls"\n'
                  'printf "SSH_AUTH_SOCK=; export SSH_AUTH_SOCK;\\n"')
        self.run_checked("zsh", "-ic", '[[ -z "$SSH_AUTH_SOCK" ]]')
        # An empty socket used to trigger a second manual agent startup.
        self.assertEqual((self.home / "agent-calls").read_text().splitlines(), ["start"])

    def test_gsuggest_copy_failure_and_staged_or_unstaged_accept(self):
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        for tool in ("cat", "git"):
            (self.bin / tool).symlink_to(shutil.which(tool))
        self.mock("llm", 'printf "%s\\n" "$@" > "$HOME/llm-args"\n'
                  'printf "fix: update fixture å\\n"')
        # Terminal display is unchanged; isolate /dev/tty for this noninteractive test.
        self.mock("tee", "cat")

        for staged in (True, False):
            with self.subTest(staged=staged):
                project = self.home / ("staged" if staged else "unstaged")
                self.run_checked("git", "init", "--initial-branch=main", str(project))
                source = project / "example.txt"
                source.write_text("before\n")
                self.run_checked("git", "-C", str(project), "add", ".")
                self.run_checked("git", "-C", str(project), "commit", "-m", "Baseline")
                source.write_text("after\n")
                if staged:
                    self.run_checked("git", "-C", str(project), "add", ".")

                def suggest(*flags):
                    return subprocess.run([shutil.which("zsh"), "-f", "-c", 'source "$1"; shift; gsuggest "$@"',
                                           "gsuggest-check", str(self.home / ".config/zsh/gsuggest.zsh"), *flags],
                                          cwd=project, env={**self.env, "PATH": str(self.bin)},
                                          capture_output=True, text=True, timeout=10)

                # No host clipboard tools are reachable in the restricted PATH.
                result = suggest()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("message was not copied", result.stderr)
                self.assertEqual(self.run_checked("git", "-C", str(project), "log", "-1", "--format=%s"), "Baseline")
                self.mock("wl-copy", 'cat > "$HOME/clipboard"')
                result = suggest("-l")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual((self.home / "clipboard").read_text(), "fix: update fixture å\n")
                self.assertIn("body: 3-5 sentences", (self.home / "llm-args").read_text())
                (self.bin / "wl-copy").unlink()

                result = suggest("-a")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.run_checked("git", "-C", str(project), "log", "-1", "--format=%s"),
                                 "fix: update fixture å")
                self.assertEqual(self.run_checked("git", "-C", str(project), "status", "--porcelain"), "")

    def test_actual_tmux_config_and_directory_bindings(self):
        # The private hook signals after the real interactive shell has started.
        with (self.home / ".zshrc.private").open("a") as stream:
            stream.write('[[ -n "$TMUX" ]] && tmux wait-for -S shell-ready\n')
        project = self.home / "project with spaces"
        project.mkdir()
        self.tmux("new-session", "-d", "-s", "runtime", "-c", str(project), "-x", "120", "-y", "40")
        self.tmux("wait-for", "shell-ready")
        self.assertEqual(self.tmux("display-message", "-p", "#{window_index}"), "1")
        # Explicit sourcing surfaces errors that initial detached startup can hide.
        self.tmux("bind-key", "-n", "M-n", "next-window")
        self.tmux("bind-key", "-n", "M-p", "previous-window")
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        self.assertNotRegex(self.tmux("list-keys", "-T", "root"), r"\sM-[np]\s")
        for key in ('"', "%", "c"):
            with self.subTest(key=key):
                binding = shlex.split(self.tmux("list-keys", "-T", "prefix", key))
                command = binding[binding.index(key) + 1:]
                self.tmux(*command)
                self.tmux("wait-for", "shell-ready")
                self.assertEqual(self.tmux("display-message", "-p", "#{pane_current_path}"), str(project))
        self.assertEqual(self.tmux("display-message", "-p", "#{session_windows}"), "2")
        for index in range(3, 11):
            self.tmux("new-window", "-d", "-t", f":{index}", "sleep 60")
        for index in range(1, 11):
            key = f"M-{index % 10}"
            with self.subTest(key=key):
                binding = shlex.split(self.tmux("list-keys", "-T", "root", key))
                self.tmux(*binding[binding.index(key) + 1:])
                self.assertEqual(self.tmux("display-message", "-p", "#{window_index}"), str(index))

    def test_optional_tmux_local_config_survives_theme_changes(self):
        self.tmux("new-session", "-d", "-s", "local", "sleep 120")
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        self.assertNotIn("LOCAL", self.tmux("show-options", "-gv", "status-right"))
        self.mock_theme_services()
        command = ROOT / "packages/themes/.local/bin/theme-set"
        self.run_checked("bash", str(command), "gruvbox")
        local = self.home / ".tmux.conf.local"
        contents = 'set -ag status-right " LOCAL"\nset -g @local-tmux loaded\n'
        local.write_text(contents)
        for theme in ("everforest", "gruvbox", "everforest"):
            self.tmux("source-file", str(self.home / ".tmux.conf"))
            self.tmux("set-option", "-gu", "@local-tmux")
            self.run_checked("bash", str(command), theme)
            status = self.tmux("show-options", "-gv", "status-right")
            self.assertEqual(status.count("LOCAL"), 1, status)
            self.assertEqual(self.tmux("show-options", "-gv", "@local-tmux"), "loaded")
            self.assertIn("send-prefix", self.tmux("list-keys", "-T", "prefix", "C-s"))
            self.assertEqual(local.read_text(), contents)
        # Bad local settings are reported while the chosen theme stays active.
        local.write_text("not-a-tmux-command\n")
        result = subprocess.run(["bash", str(command), "gruvbox"], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning: could not reload local tmux config", result.stderr)
        self.assertEqual(self.current.resolve().name, "gruvbox")

    def test_theme_switch_rejection_and_reload_failure(self):
        # Make every reload observable and harmless, including process signals.
        for name in ("tmux", "pgrep", "pkill", "makoctl", "hyprctl", "systemctl", "foot-reload"):
            self.mock(name, 'echo "$0 $*" >> "$HOME/reloads"; exit 1')
        command = ROOT / "packages/themes/.local/bin/theme-set"
        result = subprocess.run(["bash", str(command), "gruvbox"], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.current.resolve().name, "gruvbox")
        self.assertIn("warning:", result.stderr)
        self.assertEqual(self.run_checked("bash", str(command)), "gruvbox")
        (self.home / ".local/share/dotfiles/themes/everforest/tmux.conf").unlink()
        before = (self.home / "reloads").read_bytes()
        for theme in ("everforest", "missing", "../gruvbox"):
            result = subprocess.run(["bash", str(command), theme], env=self.env,
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.current.resolve().name, "gruvbox")
        self.assertEqual((self.home / "reloads").read_bytes(), before)


class RecoveryTests(RuntimeHome):
    home_prefix = "dotfiles-recovery-"

    def setUp(self):
        super().setUp()
        self.plugins = self.home / ".local/share/tmux/plugins"
        self.state = self.home / ".local/state/tmux/resurrect"
        self.installer = ROOT / "scripts/install-tmux-plugins.sh"
        # Real Git against local, pinned remotes; installation tests stay offline.
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(self.home / "gitconfig"))
        for name in ("tmux-resurrect", "tmux-continuum"):
            source = FIXTURES / "home/.local/share/tmux/plugins" / name
            self.assertTrue((source / ".git").is_dir(), f"Missing fixture: {source}")
            self.run_checked("git", "config", "--global", f"url.{source.as_uri()}.insteadOf",
                             f"https://github.com/tmux-plugins/{name}.git")
        # Continuum's process discovery must not see unrelated host tmux servers.
        self.mock("ps", 'if [ "$1" = -u ]; then exit 0; fi\nexec /usr/bin/ps "$@"')

    def install_plugins(self):
        result = subprocess.run(["bash", str(self.installer)], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_binding(self, key):
        binding = shlex.split(self.tmux("list-keys", "-T", "prefix", key))
        self.tmux(*binding[binding.index(key) + 1:])

    def test_install_preserves_existing_checkouts_and_snapshots(self):
        self.install_plugins()
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        plugin = self.plugins / "tmux-resurrect"
        self.run_checked("git", "-C", str(plugin), "switch", "-qc", "machine-local")
        self.run_checked("git", "-C", str(plugin), "-c", "user.name=Fixture", "-c",
                         "user.email=fixture@example.invalid", "commit", "-q", "--allow-empty", "-m", "Local fixture")
        head = self.run_checked("git", "-C", str(plugin), "rev-parse", "HEAD")
        entrypoint = plugin / "resurrect.tmux"
        original = entrypoint.read_text() + "\n# local modification\n"
        entrypoint.write_text(original)
        snapshot = self.state / "existing.txt"
        snapshot.write_text("existing session snapshot\n")
        (self.state / "last").symlink_to(snapshot.name)
        for _ in range(2):
            self.install_plugins()
            self.assertEqual(self.run_checked("git", "-C", str(plugin), "rev-parse", "HEAD"), head)
            self.assertEqual(entrypoint.read_text(), original)
            self.assertEqual((self.state / "last").readlink(), Path(snapshot.name))
            self.assertEqual(snapshot.read_text(), "existing session snapshot\n")

    def test_failed_download_leaves_no_partial_installation(self):
        self.mock("git", 'if [ "$3" = fetch ]; then exit 42; fi\nexec /usr/bin/git "$@"')
        result = subprocess.run(["bash", str(self.installer)], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.plugins.iterdir()), [])
        # A later invocation can install normally; no partial directory blocks it.
        (self.bin / "git").unlink()
        self.install_plugins()

    def test_legacy_local_block_cleanup_and_theme_reload(self):
        self.install_plugins()
        local = self.home / ".tmux.conf.local"
        overrides = 'set -g @continuum-save-interval 9\nset -ag status-right " LOCAL"\n'
        legacy = ('set -g @resurrect-dir "$HOME/.local/state/tmux/resurrect"\n'
                  'set -g @resurrect-save F5\nset -g @resurrect-restore F6\n'
                  'set -g @resurrect-capture-pane-contents off\n'
                  'set -g @continuum-save-interval 5\nset -g @continuum-restore off\n'
                  'set -g @continuum-boot off\n'
                  'run-shell \'"$HOME/.local/share/tmux/plugins/tmux-resurrect/resurrect.tmux"\'\n'
                  'run-shell \'"$HOME/.local/share/tmux/plugins/tmux-continuum/continuum.tmux"\'\n')
        snapshot = self.state / "existing.txt"
        snapshot.write_text("untouched prior snapshot\n")
        (self.state / "last").symlink_to(snapshot.name)
        # Pull before restow: the old block works without the new fragment link.
        fragment = self.home / ".config/tmux/dotfiles-recovery.conf"
        fragment.unlink()
        local.write_text(legacy + overrides)
        self.tmux("new-session", "-d", "-s", "legacy", "sleep 120")
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        shutil.copy2(ROOT / "packages/tmux/.config/tmux/dotfiles-recovery.conf", fragment)
        self.mock_theme_services()
        command = ROOT / "packages/themes/.local/bin/theme-set"
        for contents in (legacy + overrides, overrides):
            local.write_text(contents)
            for theme in ("gruvbox", "everforest", "gruvbox"):
                self.tmux("source-file", str(self.home / ".tmux.conf"))
                self.run_checked("bash", str(command), theme)
                status = self.tmux("show-options", "-gv", "status-right")
                self.assertEqual(status.count("/scripts/continuum_save.sh)"), 1, status)
                self.assertEqual(status.count("LOCAL"), 1, status)
                self.assertEqual(self.tmux("show-options", "-gv", "@continuum-save-interval"), "9")
                bindings = self.tmux("list-keys", "-T", "prefix")
                if contents.startswith(legacy):
                    self.assertIn("/tmux-resurrect/scripts/save.sh", bindings)
                else:
                    self.assertNotIn("/tmux-resurrect/scripts/save.sh", bindings)
                    self.assertNotRegex(bindings, r"\sF5\s")
                self.assertIn("/tmux-resurrect/scripts/restore.sh", self.tmux("list-keys", "-T", "prefix", "F6"))
                self.assertIn("send-prefix", self.tmux("list-keys", "-T", "prefix", "C-s"))
                self.assertEqual(snapshot.read_text(), "untouched prior snapshot\n")
                self.assertEqual((self.state / "last").readlink(), Path(snapshot.name))
                self.assertEqual(local.read_text(), contents)
                self.assertEqual(self.tmux("list-sessions", "-F", "#{session_name}"), "legacy")

    def test_autosave_without_save_shortcut_and_manual_restore(self):
        self.install_plugins()
        project = self.home / "project with spaces"
        project.mkdir()
        self.tmux("new-session", "-d", "-s", "recover", "-c", str(project), "sleep 120")
        self.tmux("split-window", "-h", "-t", "recover:1", "-c", str(project), "sleep 120")
        self.tmux("new-window", "-d", "-t", "recover:2", "-c", str(project), "sleep 120")
        self.tmux("bind-key", "F5", "run-shell", '"$HOME/.local/share/tmux/plugins/tmux-resurrect/scripts/save.sh"')
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        bindings = self.tmux("list-keys", "-T", "prefix")
        self.assertNotRegex(bindings, r"\sF5\s")
        self.assertNotIn("/tmux-resurrect/scripts/save.sh", bindings)
        self.assertIn("send-prefix", self.tmux("list-keys", "-T", "prefix", "C-s"))
        self.assertEqual(self.tmux("show-options", "-gv", "@continuum-save-interval"), "5")
        self.assertEqual(self.tmux("show-options", "-gv", "@continuum-restore"), "off")
        self.assertEqual(self.tmux("show-options", "-gv", "@continuum-boot"), "off")
        self.assertEqual(self.tmux("show-options", "-gv", "@resurrect-capture-pane-contents"), "off")
        self.tmux("set-option", "-g", "@resurrect-hook-post-save-all", "tmux wait-for -S saved")
        # Exercise the actual status-line save job without a five-minute delay.
        self.tmux("set-option", "-g", "@continuum-save-last-timestamp", "0")
        status = self.tmux("show-options", "-gv", "status-right")
        job = status[status.index("#(") + 2:status.index(")")]
        self.assertIn("continuum_save.sh", job)
        self.tmux("run-shell", job)
        self.tmux("wait-for", "saved")
        last = self.state / "last"
        self.assertTrue(last.is_symlink())
        self.assertTrue(last.is_file(), f"Dangling snapshot: {last.readlink()}")
        self.assertIn("pane\trecover\t", last.read_text())
        self.assertFalse((self.state / "pane_contents.tar.gz").exists())
        self.assertGreater(int(self.tmux("show-options", "-gv", "@continuum-save-last-timestamp")), 0)
        self.tmux("new-session", "-d", "-s", "holding", "sleep 120")
        self.tmux("kill-session", "-t", "recover")
        self.tmux("set-option", "-g", "@resurrect-hook-post-restore-all", "tmux wait-for -S restored")
        self.run_binding("F6")
        self.tmux("wait-for", "restored")
        self.assertEqual(self.tmux("display-message", "-p", "-t", "recover", "#{session_windows}"), "2")
        self.assertEqual(self.tmux("display-message", "-p", "-t", "recover:1", "#{window_panes}"), "2")
        paths = self.tmux("list-panes", "-s", "-t", "recover", "-F", "#{pane_current_path}").splitlines()
        self.assertEqual(paths, [str(project)] * 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
