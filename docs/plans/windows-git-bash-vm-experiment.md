# Implementation Plan: Windows Git Bash VM experiment

Status: later. Retained without a current experiment commitment; no native
Windows support or Windows VM test has been implemented yet.

## Goal

Create a disposable Windows 11 virtual machine on the Arch Linux host and use it to
determine which dotfiles can reliably support a native-Windows, non-WSL Git
Bash environment:

```text
Windows 11
├── Windows Terminal
├── psmux (preferred native multiplexer candidate)
│   └── Git Bash login shells
└── Git for Windows
    ├── Mintty (current-workflow comparison)
    ├── Git Bash and its MSYS runtime
    └── optional tmux and libevent binaries borrowed from MSYS2
```

The experiment should answer:

- Which Bash and tmux settings work in Git Bash without weakening Linux support?
- Can the selected psmux setup from the physical work PC be reproduced with the
  dotfiles while keeping Git Bash as the interactive shell?
- Does transparent NVM lazy loading work in fresh Git Bash login shells and
  psmux panes?
- Can the MSYS2 tmux overlay be installed reproducibly without modifying the
  Git for Windows installation?
- Which commands need Windows-specific guards or replacements?
- Is the result stable across a Git for Windows upgrade?
- Is a dedicated Git Bash Stow/package profile worth maintaining?

## Current state

The repository officially supports native Fedora/Ubuntu and WSL2, not native
Windows. The existing `setup.sh` must not be run from Git Bash.

The Arch Linux host was checked on 2026-09-05 and has the hardware capacity for
the experiment, but its VM stack has not yet been installed:

| Resource | Available |
|---|---|
| Host | Arch Linux (rolling) |
| CPU | Ryzen 5 7600X, 6 cores / 12 threads |
| Virtualization | AMD-V and `/dev/kvm` available |
| Memory | 30 GiB total |
| Home storage | 290 GiB free |
| VM stack | Not installed; QEMU/KVM, libvirt, OVMF, and `swtpm` are available from Arch Extra |
| VM manager | Not installed; use `virt-manager` |

The current Git Bash tmux approach obtains tmux by extracting `tmux.exe` from the MSYS2
`tmux` package and `msys-event-*.dll` from the MSYS2 `libevent` package, then
placing them in Git for Windows' `usr/bin` directory. This works because Git for
Windows already supplies additional dependencies, including its MSYS runtime
and ncurses. It is an overlay, not a standalone two-file installation.

## Approach

Use a full Windows VM rather than a Windows container. Windows containers need
a Windows host and do not reproduce the interactive Mintty desktop environment.

### VM manager

Use `virt-manager` with the system libvirt connection (`qemu:///system`). It
provides the required control and inspection of firmware, TPM, storage
controllers, networking, and snapshots. GNOME Boxes is not needed for this
experiment.

### Arch host preparation

Install the host stack from the official repositories:

```bash
sudo pacman -S --needed qemu-desktop libvirt edk2-ovmf swtpm virt-manager dnsmasq
```

Start the libvirt and logging daemons, then verify the system connection and
the default NAT network before creating the guest:

```bash
sudo systemctl enable --now libvirtd.service
sudo systemctl start virtlogd.service
virsh -c qemu:///system list --all
sudo virsh net-list --all
sudo virsh net-start default
sudo virsh net-autostart default
```

Use standard polkit authentication for the system connection in `virt-manager`;
confirm a graphical polkit agent is active if authentication cannot be
completed. Do not weaken libvirt socket permissions or add a passwordless
authorization rule solely for this disposable experiment.

Suggested guest allocation:

| Resource | Allocation |
|---|---|
| vCPUs | 4 |
| Memory | 8 GiB |
| Disk | 80 GiB, dynamically allocated |
| Firmware | UEFI |
| TPM | emulated TPM 2.0 |
| Network | default NAT |
| Display | SPICE |

### Windows media and licensing

Use Microsoft's official Windows 11 Enterprise 90-day evaluation ISO for the
initial experiment. It requires no product key and avoids moving or conflicting
with the license used by the physical dual-boot Windows installation.

Do not enter the existing dual-boot key into the VM. A VM has a separate virtual
hardware identity, and an ordinary OEM or retail license should not be assumed
to cover both installations. If the VM becomes permanent, decide on a separate
license before the evaluation expires.

Snapshots are for configuration rollback, not for bypassing the evaluation
period.

## Scope

### Included

- Windows 11 VM creation and snapshots
- Git for Windows, Git Bash, and Mintty
- Windows Terminal and psmux with Git Bash login shells
- the current MSYS2-derived tmux arrangement
- a safer user-local tmux overlay experiment
- Bash startup and NVM lazy-loading behavior
- tmux startup, terminal capabilities, keybindings, and process environment
- portable aliases and shell helper functions
- selected Vim/Neovim configuration if the shell baseline succeeds
- behavior before and after upgrading Git for Windows
- findings needed to design a native-Windows dotfile profile

### Excluded

- adding native Windows branches to `setup.sh`
- claiming general MSYS2 or Cygwin support
- WSL behavior, which already has a separate policy
- Windows containers
- GPU passthrough or gaming performance
- production use of an expired or improperly licensed Windows installation
- desktop packages such as Hyprland, Waybar, Wofi, Foot, and Mako

## Experiment

### 1. Prepare the host

1. Install and verify the Arch host stack above.
2. Confirm `virsh -c qemu:///system list --all` succeeds and the `default` NAT
   network is active.
3. Open `virt-manager` and connect to `QEMU/KVM - system`.

### 2. Create the baseline VM

1. Download and verify the official Windows 11 Enterprise evaluation x64 ISO.
2. Create the VM with the resource allocation above.
3. Confirm UEFI, Secure Boot compatibility, and TPM 2.0 before installation.
4. Complete Windows setup and Windows Update.
5. Install SPICE guest tools if needed for display resizing and clipboard use.
6. Take a `windows-clean` snapshot.

Clone the dotfiles repository inside the guest. Do not mount the Linux checkout
as the primary working tree; a native clone is needed to expose Windows path,
line-ending, executable, and symlink behavior.

### 3. Reproduce Git Bash

Install a pinned Git for Windows release, including Mintty. Record:

```bash
git --version
bash --version
uname -a
printf 'MSYSTEM=%s\nSHELL=%s\n' "$MSYSTEM" "$SHELL"
type -a bash mintty git
```

Take a `git-bash-clean` snapshot before adding a multiplexer or dotfiles.

### 4. Reproduce the selected psmux setup

Validate psmux viability on the physical work PC before starting this VM work.
The VM does not need to establish whether psmux is a viable multiplexer; it
reproduces the selected work setup so dotfile changes can be tested safely.

Install the selected psmux release and use Windows Terminal to launch it.
Configure Git Bash as psmux's default login shell in `~/.psmux.conf`:

```tmux
set -g default-shell "C:/Program Files/Git/bin/bash.exe" --login
```

Record the psmux and Git for Windows versions from the work trial. Verify that
newly created panes and windows start Git Bash in the requested project
directory, then test the dotfile integration:

- Bash login startup and PATH initialization
- pane/window navigation and tmux-compatible bindings
- clipboard, mouse, colors, Unicode, and `$TERM`
- Git for Windows SSH and interactive terminal tools
- Node/NVM and Neovim behavior

Treat the existing `.tmux.conf` as a compatibility input, not an assumed
drop-in configuration. Record unsupported directives or behavior rather than
weakening Linux tmux settings.

### 5. Reproduce and harden the tmux overlay

First reproduce the baseline installation using pinned package versions. Record
the package filenames and SHA-256 checksums.

The MSYS2 package metadata currently declares:

```text
tmux -> libevent, ncurses
libevent -> openssl
```

After confirming the existing approach, test a user-managed overlay instead of
writing into `C:\Program Files\Git\usr\bin`:

```text
~/.local/bin/tmux.exe
~/.local/bin/msys-event-2-1-7.dll
```

Add `~/.local/bin` to `PATH` and verify that tmux finds Git for Windows' MSYS
runtime and ncurses DLLs. Pin versions and checksums; do not implement a
"download latest" installer.

Run:

```bash
command -v tmux
cygpath -w "$(command -v tmux)"
tmux -V
infocmp tmux-256color
```

If `tmux-256color` is unavailable, test `xterm-256color` as the Git Bash-specific
fallback. Do not change the Linux tmux profile solely for this environment.

### 6. Test NVM lazy loading

Use `nvm-sh`, not NVM for Windows, to test shell-local NVM behavior. The Bash
loader should use `unset -f`, not Zsh's `unfunction`, and should wrap at least
`nvm`, `node`, `npm`, and `npx`.

Test each command as the first Node-related command in a genuinely fresh shell:

```bash
node --version
npm --version
npx --version
nvm --help
```

For each case, record:

```bash
type -a nvm node npm npx
node -p 'process.execPath'
printf 'NVM_DIR=%s\nNVM_BIN=%s\n' "$NVM_DIR" "$NVM_BIN"
```

Repeat the tests in:

- a fresh psmux session with no existing session state
- the first pane of a new psmux session
- additional psmux panes created before and after NVM loads
- a new Windows Terminal process attached to an existing psmux session
- a shell with a system or Windows Node installation already on `PATH`

If the MSYS2 tmux overlay is installed for comparison, repeat the equivalent
cases there.

The tests must prove that direct `node`, `npm`, and `npx` calls cannot silently
fall back to an unintended Node installation.

### 7. Test multiplexer behavior

Run the NVM and terminal checks in fresh psmux sessions and panes. If the
MSYS2 tmux overlay is also installed, repeat the equivalent checks there for a
direct comparison.

Start with a new psmux session rather than reusing state:

```bash
psmux new-session -s dotfiles-test
```

Verify:

- Bash starts without a seven-second NVM delay in every pane
- the expected Node version is selected on first use in every pane
- pane and window navigation bindings work in psmux
- colors and `$TERM` are correct inside and outside psmux
- clipboard behavior either works or fails with a clear platform guard
- Git for Windows `ssh` works without an unnecessary `winpty` wrapper
- native Windows CLI programs that require `winpty` are identified individually
- killing and recreating the psmux session does not expose inherited `PATH` state

### 8. Test upgrade resilience

Take a snapshot, upgrade Git for Windows and psmux, and repeat the Bash,
multiplexer, terminfo, and NVM test matrix.

The experiment fails the user-local overlay approach if a routine Git upgrade
silently changes the Node selection, breaks DLL loading, or requires copying
untracked files back into the Git installation directory.

The psmux path fails if a routine Git for Windows or psmux upgrade breaks Git
Bash startup, project-directory pane creation, or the tested terminal workflow.

## Expected repository design

Do not implement these changes until the experiment establishes the required
guards and file layout. Likely follow-up work includes:

- a dedicated `bashrc-git-bash` package or shared portable Bash fragment
- a Git-Bash psmux configuration, or a dedicated `tmux-git-bash` package
  derived from `tmux-server` only if psmux is not viable
- a repo-only Git Bash bootstrap script separate from `setup.sh`
- pinned MSYS2 tmux/libevent package versions and checksums
- static Bash syntax tests and optional Windows GitHub Actions coverage
- README, `AGENTS.md`, and supported-environment updates only after validation

GNU Stow availability and Windows symlink semantics must be evaluated before
choosing how files are installed. A small `.bashrc` that sources files from the
clone may be more reliable than pretending the Linux Stow workflow is portable.

## Completion criteria

The experiment is complete when:

1. A clean VM can reproduce the target non-WSL Git Bash and selected
   multiplexer environment.
2. The work trial has selected psmux or the MSYS2 tmux overlay, and the VM
   reproduces that multiplexer with Git Bash login shells.
3. Fresh shells and fresh psmux sessions pass the NVM first-command matrix.
4. Terminal capabilities, keybindings, and project-directory pane creation
   work without weakening Linux configs.
5. A Git for Windows or psmux upgrade does not break the selected environment.
6. The portable dotfile subset and required platform guards are documented.
7. A follow-up implementation scope can be stated without guessing.

After implementation, move this plan to `docs/plans/archive/` and record the
validated native-Windows support boundary in the repository documentation.
