#!/usr/bin/env python3
"""Exercise periodic snapshots and abrupt restarts with real Neovim/Resession.

Usage: test-nvim-sessions.py /path/to/nvim /path/to/plugin-fixtures
Uses disposable HOME/XDG directories and a mocked tmux topology query.
"""
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
NVIM = shutil.which(sys.argv[1]) if len(sys.argv) > 1 else None
PLUGINS = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
PLUGIN = PLUGINS / "resession.nvim" if PLUGINS else None
if not NVIM or not PLUGIN or not (PLUGIN / "lua/resession/init.lua").is_file() or not (PLUGINS / "lazy.nvim").is_dir():
    sys.exit(__doc__)
sys.argv[1:3] = []


class Editor:
    def __init__(self, case, action, args=(), slot="0", pane="%1", headless=False, stdin=None, tmux=True):
        self.case = case
        serial = str(len(case.editors))
        self.marker = case.home / ("result-" + serial)
        script = case.home / ("action-" + serial + ".lua")
        script.write_text(action)
        self.output = bytearray()
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 100, 0, 0))
        env = {**case.env, "ACTION": str(script), "RESULT": str(self.marker),
               "TMUX": "/tmp/fixture/default,123,0", "TMUX_PANE": pane, "SLOT": slot}
        if not tmux:
            env.pop("TMUX")
            env.pop("TMUX_PANE")
        command = [NVIM, "-i", "NONE", "-u", str(case.init), *(["--headless"] if headless else []), *map(str, args)]
        self.process = subprocess.Popen(command, cwd=case.project, env=env,
                                        stdin=slave if stdin is None else subprocess.PIPE,
                                        stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        if stdin is not None:
            self.process.stdin.write(stdin)
            self.process.stdin.close()
        case.editors.append(self)

    def pump(self):
        if select.select([self.master], [], [], 0.05)[0]:
            try:
                data = os.read(self.master, 65536)
                self.output.extend(data)
                if b"\x1b]11;?" in data:
                    os.write(self.master, b"\x1b]11;rgb:2828/2828/2828\x1b\\")
                if b"\x1b[5n" in data:
                    os.write(self.master, b"\x1b[0n")
            except OSError as error:
                if error.errno != errno.EIO:
                    raise

    def wait(self, condition, timeout=12):
        deadline = time.monotonic() + timeout
        while not condition():
            self.pump()
            if time.monotonic() >= deadline:
                raise AssertionError("Editor timed out: " + self.output.decode(errors="replace"))

    def ready(self):
        self.wait(self.marker.exists)
        self.case.assertEqual(self.marker.read_text().strip(), "ok", self.output.decode(errors="replace")[-1500:])
        return self

    def crash(self):
        if self.process.poll() is None:
            # Some runners wrap subprocesses. Kill Neovim itself, not a launcher
            # that might gracefully terminate its child on exit.
            pidfile = Path(str(self.marker) + ".pid")
            target = int(pidfile.read_text()) if pidfile.exists() else self.process.pid
            try:
                os.kill(target, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=5)

    def close(self):
        self.crash()
        os.close(self.master)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nvim-session-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.project = self.home / "project å with spaces"
        self.project.mkdir()
        for name in ("a.txt", "b.txt", "c.txt"):
            (self.project / name).write_text("one\ntwo\nthree\nfour\n")
        self.editors = []
        self.addCleanup(lambda: [editor.close() for editor in self.editors])
        bindir = self.home / "bin"
        bindir.mkdir()
        tmux = bindir / "tmux"
        tmux.write_text('#!/bin/sh\nprintf "/tmp/fixture/default\\twork\\t1\\t%s\\n" "$SLOT"\n')
        tmux.chmod(0o755)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("NVIM", "VIM", "TMUX", "XDG_", "LUA_"))}
        self.env.update(HOME=str(self.home), PATH=str(bindir) + ":/usr/bin:/bin", TERM="xterm-256color",
                        NVIM_LOG_FILE=str(self.home / "nvim.log"),
                        XDG_CONFIG_HOME=str(self.home / ".config"), XDG_DATA_HOME=str(self.home / ".data"),
                        XDG_STATE_HOME=str(self.home / ".state"), XDG_CACHE_HOME=str(self.home / ".cache"))
        config = self.home / ".config/nvim"
        config.mkdir(parents=True)
        (config / "local.lua").write_text('return {features={session_recovery=true},session_save_interval=1}\n')
        self.snapshots = self.home / ".data/nvim/dotfiles/recovery"
        self.init = self.home / "init.lua"
        self.init.write_text('''
vim.opt.rtp:prepend(''' + json.dumps(str(ROOT / "packages/nvim/.config/nvim")) + ''')
vim.opt.rtp:prepend(''' + json.dumps(str(PLUGIN)) + ''')
vim.opt.swapfile = false
vim.fn.writefile({tostring(vim.fn.getpid())}, vim.env.RESULT .. ".pid")
vim.notify = function(msg) vim.fn.writefile({tostring(msg)}, vim.env.HOME .. "/messages", "a") end
local spec = require("plugins.sessions")
if spec.enabled then spec.config() end
vim.api.nvim_create_autocmd("VimEnter", {once=true, callback=function()
  vim.defer_fn(function()
    local ok, err = pcall(dofile, vim.env.ACTION)
    vim.fn.writefile({ok and "ok" or tostring(err)}, vim.env.RESULT)
  end, 300)
end})
''')

    def launch(self, action="", **kwargs):
        return Editor(self, action, **kwargs).ready()

    def files(self):
        return sorted(path for path in self.snapshots.glob("*.json") if ".pending-" not in path.name)

    def seed(self, slot="0"):
        editor = self.launch('''
vim.cmd.edit("a.txt")
vim.cmd.vsplit("b.txt")
vim.api.nvim_win_set_cursor(0, {3, 1})
vim.cmd.tabnew("c.txt")
vim.api.nvim_win_set_cursor(0, {2, 0})
''', slot=slot)
        editor.wait(lambda: len(self.files()) >= 1)
        self.assertIsNone(editor.process.poll(), editor.output.decode(errors="replace")[-1500:])
        return editor

    def test_periodic_save_survives_sigkill_and_changed_tmux_pane_id(self):
        editor = self.seed()
        saved = json.loads(self.files()[0].read_text())
        self.assertEqual(len(saved["tabs"]), 2)
        editor.crash()  # No VimLeavePre: only the timer could have produced this snapshot.
        restored = self.launch('''
assert(#vim.api.nvim_list_tabpages() == 2)
assert(#vim.api.nvim_tabpage_list_wins(vim.api.nvim_list_tabpages()[1]) == 2)
assert(vim.fn.expand("%:t") == "c.txt")
assert(vim.api.nvim_win_get_cursor(0)[1] == 2)
vim.cmd.tabfirst()
local found = false
for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
  if vim.fn.fnamemodify(vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(win)), ":t") == "b.txt" then
    assert(vim.api.nvim_win_get_cursor(win)[1] == 3)
    found = true
  end
end
assert(found)
''', pane="%99")
        self.assertEqual(len(self.files()), 1)
        restored.crash()

    def test_two_panes_in_same_directory_have_independent_snapshots(self):
        first = self.seed("0")
        second = self.launch('vim.cmd.edit("b.txt")', slot="1")
        second.wait(lambda: len(self.files()) == 2)
        first.crash()
        second.crash()
        self.launch('assert(#vim.api.nvim_list_tabpages() == 2)', slot="0")
        self.launch('assert(#vim.api.nvim_list_tabpages() == 1); assert(vim.fn.expand("%:t") == "b.txt")', slot="1")

    def test_full_profile_with_lazy_and_dashboard_recovers_after_sigkill(self):
        config = ROOT / "packages/nvim/.config/nvim"
        shutil.copytree(config, self.home / ".config/nvim", dirs_exist_ok=True)
        shutil.copytree(PLUGINS, self.home / ".data/nvim/lazy")
        text = self.init.read_text().replace(
            'local spec = require("plugins.sessions")\nif spec.enabled then spec.config() end',
            'dofile(' + json.dumps(str(config / "init.lua")) + ')')
        self.init.write_text(text)
        editor = self.launch('vim.cmd.vsplit("b.txt")', args=[self.project / "a.txt"])
        editor.wait(lambda: bool(self.files()))
        editor.crash()
        self.launch('''
assert(require("lazy.core.config").plugins["resession.nvim"]._.loaded)
assert(#vim.api.nvim_tabpage_list_wins(0) == 2)
local files = {}
for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
  files[vim.fn.fnamemodify(vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(win)), ":t")] = true
end
assert(files["a.txt"] and files["b.txt"])
assert(vim.bo.filetype ~= "snacks_dashboard")
''', pane="%99")

    def test_explicit_file_wins_and_manual_restore_refuses_dirty_buffers(self):
        self.seed().crash()
        self.launch('''
assert(vim.fn.expand("%:t") == "b.txt")
assert(#vim.api.nvim_list_tabpages() == 1)
vim.api.nvim_buf_set_lines(0, 0, 1, false, {"unsaved text"})
vim.cmd.SessionRestore()
assert(vim.api.nvim_get_current_line() == "unsaved text")
vim.bo.modified = false
vim.cmd.SessionRestore()
assert(#vim.api.nvim_list_tabpages() == 2)
vim.cmd.SessionStop()
''', args=[self.project / "b.txt"])

    def test_active_owner_lock_prevents_a_second_writer(self):
        self.seed()
        before = self.files()[0].read_bytes()
        self.launch('vim.cmd.edit("c.txt"); assert(not require("config.sessions").save())')
        self.assertEqual(self.files()[0].read_bytes(), before)
        self.assertIn("another editor owns", (self.home / "messages").read_text())
        self.assertEqual(len(list(self.snapshots.glob("*.lock"))), 1)

    def test_corrupt_snapshot_and_failed_write_preserve_previous_data(self):
        self.seed().crash()
        snapshot = self.files()[0]
        good = snapshot.read_bytes()
        trial = self.launch('''
require("resession").save = function(name, opts)
  vim.fn.writefile({"incomplete json"}, require("resession.util").get_session_file(name, opts.dir))
  error("simulated interrupted write")
end
vim.cmd.edit("b.txt")
assert(not require("config.sessions").save())
vim.cmd.SessionStop()
''', args=[self.project / "b.txt"])
        self.assertEqual(json.loads(snapshot.read_bytes()), json.loads(good), "changed before kill")
        trial.crash()
        self.assertEqual(json.loads(snapshot.read_bytes()), json.loads(good))
        snapshot.write_text("incomplete json")
        self.launch('''
vim.cmd.edit("c.txt")
assert(not require("config.sessions").save())
assert(vim.o.eventignore == "")
''').crash()
        self.assertEqual(snapshot.read_text(), "incomplete json")

    def test_previous_boot_lock_is_reclaimed_even_if_its_pid_is_alive(self):
        self.seed().crash()
        lock = next(self.snapshots.glob("*.lock"))
        lock.write_text(json.dumps({"pid": os.getpid(), "boot": "previous-boot"}))
        self.launch('assert(#vim.api.nvim_list_tabpages() == 2)')
        self.assertNotEqual(json.loads(lock.read_text())["pid"], os.getpid())

    def test_reused_pid_in_same_boot_does_not_block_recovery(self):
        self.seed().crash()
        lock = next(self.snapshots.glob("*.lock"))
        owner = json.loads(lock.read_text())
        owner.update(pid=os.getpid(), start="previous-process")
        lock.write_text(json.dumps(owner))
        self.launch('assert(#vim.api.nvim_list_tabpages() == 2)')
        self.assertNotEqual(json.loads(lock.read_text())["pid"], os.getpid())

    def test_outside_tmux_recovers_by_directory_and_stop_preserves_snapshot(self):
        editor = self.launch('vim.cmd.edit("a.txt")', tmux=False)
        editor.wait(lambda: bool(self.files()))
        editor.crash()
        snapshot = self.files()[0]
        self.assertTrue(snapshot.name.startswith("cwd-"))
        before = snapshot.read_bytes()
        stopped = self.launch('''
assert(vim.fn.expand("%:t") == "a.txt")
vim.cmd.SessionStop()
vim.cmd.edit("b.txt")
vim.schedule(function() vim.cmd("qa!") end)
''', tmux=False)
        stopped.wait(lambda: stopped.process.poll() is not None)
        self.assertEqual(snapshot.read_bytes(), before)

    def test_no_empty_save_and_clean_exit_releases_lock(self):
        editor = self.launch('assert(not require("config.sessions").save())')
        self.assertFalse(self.files())
        editor.crash()
        exiting = self.launch('vim.cmd.edit("a.txt"); vim.schedule(function() vim.cmd("qa!") end)')
        exiting.wait(lambda: exiting.process.poll() is not None)
        self.assertEqual(len(self.files()), 1)
        self.assertFalse(list(self.snapshots.glob("*.lock")))

    def test_disabled_headless_stdin_and_explicit_session_do_not_save(self):
        self.launch('vim.cmd.edit("a.txt"); assert(not require("config.sessions").save()); vim.schedule(function() vim.cmd("qa!") end)', headless=True)
        self.launch('assert(not require("config.sessions").save())', args=["-"], stdin=b"piped content\n")
        session = self.home / "explicit.vim"
        session.write_text("edit " + str(self.project / "a.txt").replace(" ", "\\ ") + "\n")
        self.launch('assert(not require("config.sessions").save())', args=["-S", session])
        (self.home / ".config/nvim/local.lua").unlink()
        self.launch('assert(not require("plugins.sessions").enabled); assert(vim.fn.exists(":SessionSave") == 0)')
        self.assertFalse(self.files())

    def test_invalid_interval_rejects_local_settings(self):
        local = self.home / ".config/nvim/local.lua"
        local.write_text('return {features={session_recovery=true},session_save_interval=0}\n')
        self.launch('''
assert(not require("config.settings").features.session_recovery)
assert(require("config.settings").session_save_interval == 60)
assert(vim.fn.exists(":SessionSave") == 0)
''')
        self.assertIn("between 1 and 3600", (self.home / "messages").read_text())


unittest.main()
