# Implementation Plan: Windows Git Bash VM experiment

Status: later. Retained without a current experiment commitment; no native
Windows support or Windows VM test has been implemented yet.

## Goal

Create a disposable Windows 11 virtual machine on the Fedora host and use it to
determine which dotfiles can reliably support a native-Windows, non-WSL Git
Bash environment:

```text
Windows 11
└── Git for Windows
    ├── Mintty
    ├── Git Bash
    ├── Git for Windows' MSYS runtime
    └── tmux and libevent binaries borrowed from MSYS2
```

The experiment should answer:

- Which Bash and tmux settings work in Git Bash without weakening Linux support?
- Does transparent NVM lazy loading work in fresh Mintty shells and tmux panes?
- Can the MSYS2 tmux overlay be installed reproducibly without modifying the
  Git for Windows installation?
- Which commands need Windows-specific guards or replacements?
- Is the result stable across a Git for Windows upgrade?
- Is a dedicated Git Bash Stow/package profile worth maintaining?

## Current state

The repository officially supports native Fedora/Ubuntu and WSL2, not native
Windows. The existing `setup.sh` must not be run from Git Bash.

The Fedora host was checked on 2026-08-30 and is already capable of hosting the
experiment:

| Resource | Available |
|---|---|
| Host | Fedora 44 |
| CPU | Ryzen 5 7600X, 6 cores / 12 threads |
| Virtualization | AMD-V and `/dev/kvm` available |
| Memory | 30 GiB total |
| Home storage | 249 GiB free |
| VM stack | QEMU/KVM, GNOME Boxes, OVMF, and `swtpm` installed |
| Optional UI | `virt-manager` not installed |

The target environment obtains tmux by extracting `tmux.exe` from the MSYS2
`tmux` package and `msys-event-*.dll` from the MSYS2 `libevent` package, then
placing them in Git for Windows' `usr/bin` directory. This works because Git for
Windows already supplies additional dependencies, including its MSYS runtime
and ncurses. It is an overlay, not a standalone two-file installation.

## Approach

Use a full Windows VM rather than a Windows container. Windows containers need
a Windows host and do not reproduce the interactive Mintty desktop environment.

### VM manager

Start with GNOME Boxes because it is already installed. Use `virt-manager`
instead if the experiment should include explicit control and inspection of
firmware, TPM, storage controllers, networking, and snapshots.

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

### 1. Create the baseline VM

1. Download and verify the official Windows 11 Enterprise evaluation x64 ISO.
2. Create the VM with the resource allocation above.
3. Confirm UEFI, Secure Boot compatibility, and TPM 2.0 before installation.
4. Complete Windows setup and Windows Update.
5. Install SPICE guest tools if needed for display resizing and clipboard use.
6. Take a `windows-clean` snapshot.

Clone the dotfiles repository inside the guest. Do not mount the Linux checkout
as the primary working tree; a native clone is needed to expose Windows path,
line-ending, executable, and symlink behavior.

### 2. Reproduce Git Bash

Install a pinned Git for Windows release, including Mintty. Record:

```bash
git --version
bash --version
uname -a
printf 'MSYSTEM=%s\nSHELL=%s\n' "$MSYSTEM" "$SHELL"
type -a bash mintty git
```

Take a `git-bash-clean` snapshot before adding tmux or dotfiles.

### 3. Reproduce and harden the tmux overlay

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

### 4. Test NVM lazy loading

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

- a new Mintty window with no tmux server
- the first pane of a new tmux server
- additional panes created before and after NVM loads
- a new Mintty process attached to an existing tmux server
- a shell with a system or Windows Node installation already on `PATH`

The tests must prove that direct `node`, `npm`, and `npx` calls cannot silently
fall back to an unintended Node installation.

### 5. Test tmux behavior

Start with a new server rather than reusing state:

```bash
tmux -L dotfiles-test -f ~/.tmux.conf new-session
```

Verify:

- Bash starts without a seven-second NVM delay in every pane
- the expected Node version is selected on first use in every pane
- pane and window navigation bindings work in Mintty
- colors and `$TERM` are correct inside and outside tmux
- clipboard behavior either works or fails with a clear platform guard
- Git for Windows `ssh` works without an unnecessary `winpty` wrapper
- native Windows CLI programs that require `winpty` are identified individually
- killing and recreating the tmux server does not expose inherited `PATH` state

### 6. Test upgrade resilience

Take a snapshot, upgrade Git for Windows, and repeat the Bash, tmux, terminfo,
and NVM test matrix.

The experiment fails the user-local overlay approach if a routine Git upgrade
silently changes the Node selection, breaks DLL loading, or requires copying
untracked files back into the Git installation directory.

## Expected repository design

Do not implement these changes until the experiment establishes the required
guards and file layout. Likely follow-up work includes:

- a dedicated `bashrc-git-bash` package or shared portable Bash fragment
- a dedicated `tmux-git-bash` package derived from `tmux-server`
- a repo-only Git Bash bootstrap script separate from `setup.sh`
- pinned MSYS2 tmux/libevent package versions and checksums
- static Bash syntax tests and optional Windows GitHub Actions coverage
- README, `AGENTS.md`, and supported-environment updates only after validation

GNU Stow availability and Windows symlink semantics must be evaluated before
choosing how files are installed. A small `.bashrc` that sources files from the
clone may be more reliable than pretending the Linux Stow workflow is portable.

## Completion criteria

The experiment is complete when:

1. A clean VM can reproduce the target non-WSL Git Bash and tmux environment.
2. tmux is installed from pinned, verified artifacts outside the Git install.
3. Fresh shells and fresh tmux servers pass the NVM first-command matrix.
4. Terminal capabilities and keybindings work without weakening Linux configs.
5. A Git for Windows upgrade does not break the tested environment.
6. The portable dotfile subset and required platform guards are documented.
7. A follow-up implementation scope can be stated without guessing.

After implementation, move this plan to `docs/plans/archive/` and record the
validated native-Windows support boundary in the repository documentation.
