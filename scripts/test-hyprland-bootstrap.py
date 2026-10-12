#!/usr/bin/env python3
"""Check bootstrap boundaries in disposable homes; never run host setup/Stow."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hyprland-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.log = self.home / "commands"
        self.env = {**os.environ, "HOME": str(self.home),
                    "PATH": f"{self.bin}:/usr/bin:/bin", "CHECK_LOG": str(self.log)}
        for key in ("SSH_CONNECTION", "WAYLAND_DISPLAY", "DISPLAY", "XDG_VTNR"):
            self.env.pop(key, None)
        self.mock("systemctl", 'printf "%s\\n" "$*" >> "$CHECK_LOG"\nexit "${SYSTEMCTL_RESULT:-0}"')
        self.mock("sudo", 'printf "%s\\n" "$*" >> "$CHECK_LOG"')

    def mock(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body + "\n")
        path.chmod(0o755)

    def run_shell(self, command, shell="bash", args=()):
        return subprocess.run([shell, "-c", command, "check", *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def configure(self):
        return subprocess.run(["bash", str(ROOT / "scripts/configure-hyprland.sh")],
                              env=self.env, text=True, capture_output=True, timeout=10)

    def test_entrypoint_repeat_and_local_preservation(self):
        config = self.home / ".config/hypr/hyprland.lua"
        marker = self.home / ".local/state/dotfiles/hyprland/autostart"
        result = self.configure()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_text(), 'require("dotfiles")\n')
        self.assertTrue(marker.is_file())
        config.write_text('require("dotfiles")\n-- custom GPU and monitor settings\n')
        previous = config.read_bytes()
        self.assertEqual(self.configure().returncode, 0)
        self.assertEqual(config.read_bytes(), previous)
        self.assertEqual(self.log.read_text().splitlines(),
                         ["--user daemon-reload", "--user daemon-reload"])

    def test_no_user_service_manager_is_nonfatal(self):
        self.env["SYSTEMCTL_RESULT"] = "1"
        result = self.configure()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("before your first Hyprland session", result.stdout)

    def setup_packages(self, distro, args, wsl=False):
        # Execute only argument/OS validation and the package phase. Replace
        # system metadata with fixtures; sudo is a logging mock, never real.
        source = (ROOT / "setup.sh").read_text().split(
            "# ─── Step 3: Install Fedora container tooling", 1)[0]
        release = self.home / "os-release"
        release.write_text(f'ID={distro}\nVERSION_ID=42\nPRETTY_NAME="Test Linux"\n')
        version = self.home / "version"
        version.write_text("Microsoft WSL2" if wsl else "Linux")
        source = source.replace("/etc/os-release", str(release))
        source = source.replace("/proc/version", str(version))
        fixture = self.home / "setup-fixture.sh"
        fixture.write_text(source)
        return subprocess.run(["bash", str(fixture), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def test_arch_desktop_packages(self):
        for profile in ("--slim", "--full"):
            with self.subTest(profile=profile):
                result = self.setup_packages("arch", (profile, "--hyprland"))
                self.assertEqual(result.returncode, 0, result.stderr)
                commands = self.log.read_text()
                self.assertIn("hyprland hypridle xdg-desktop-portal-hyprland", commands)
                self.assertIn("cliphist nautilus sushi playerctl", commands)
                self.assertNotIn("nvidia", commands)
                self.log.unlink()

    def test_general_setup_does_not_install_desktop(self):
        result = self.setup_packages("arch", ("--slim",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("hyprland", self.log.read_text())

    def test_invalid_combinations_stop_before_installation(self):
        cases = [("arch", ("--server", "--hyprland"), False),
                 ("fedora", ("--hyprland",), False),
                 ("ubuntu", ("--hyprland",), False),
                 ("arch", ("--hyprland",), True)]
        for distro, args, wsl in cases:
            with self.subTest(distro=distro, args=args, wsl=wsl):
                result = self.setup_packages(distro, args, wsl)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists(), "No privileged command should run")

    def test_stow_selection_and_bootstrap_boundary(self):
        # Exercise the actual setup phase, but replace make with a logger:
        # no Stow command or host symlink operation is executed.
        self.mock("make", 'printf "%s\\n" "$*" >> "$CHECK_LOG"\nexit "${MAKE_RESULT:-0}"')
        source = (ROOT / "setup.sh").read_text()
        phase = "# ─── Step 7:" + source.split("# ─── Step 7:", 1)[1]
        phase = phase.split("# ─── Step 8:", 1)[0]
        prelude = ('set -eu; REPO_DIR="$1"; PROFILE="$2"; INSTALL_HYPRLAND="$3"; '
                   'step() { :; }; success() { :; }; die() { exit 1; };\n')
        cases = [("server", "0", "stow-server"), ("slim", "0", "stow"),
                 ("slim", "1", "stow-hyprland"), ("full", "1", "stow-hyprland")]
        marker = self.home / ".local/state/dotfiles/hyprland/autostart"
        for profile, desktop, target in cases:
            with self.subTest(profile=profile, desktop=desktop):
                self.log.unlink(missing_ok=True)
                marker.unlink(missing_ok=True)
                result = self.run_shell(prelude + phase, args=(str(ROOT), profile, desktop))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.log.read_text().splitlines()[0], f"-C {ROOT} {target}")
                self.assertEqual(marker.exists(), desktop == "1")
        marker.unlink()
        self.env["MAKE_RESULT"] = "1"
        result = self.run_shell(prelude + phase, args=(str(ROOT), "slim", "1"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists(), "Failed Stow must not enable autostart")

    def test_tty1_autostart_guards(self):
        self.mock("start-hyprland", 'printf "started\\n" >> "$CHECK_LOG"')
        self.mock("grep", '[[ "$*" == *"/etc/os-release"* && "${CHECK_DISTRO:-arch}" == arch ]]')
        self.mock("nvim", "exit 0")
        source = (ROOT / "packages/zprofile/.zprofile").read_text()
        marker = self.home / ".local/state/dotfiles/hyprland/autostart"
        marker.parent.mkdir(parents=True)
        cases = [({}, False, False), ({}, True, True),
                 ({"SSH_CONNECTION": "ssh"}, True, False),
                 ({"WAYLAND_DISPLAY": "wayland-1"}, True, False),
                 ({"DISPLAY": ":0"}, True, False),
                 ({"XDG_VTNR": "2"}, True, False),
                 ({"CHECK_DISTRO": "fedora"}, True, False)]
        original = self.env.copy()
        for overrides, opted_in, expected in cases:
            with self.subTest(overrides=overrides, opted_in=opted_in):
                self.env = {**original, "XDG_VTNR": "1", **overrides}
                if opted_in:
                    marker.touch()
                else:
                    marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                result = self.run_shell(source, shell="zsh")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.log.exists(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
