#!/usr/bin/env bash
#
# setup.sh — Bootstrap development environment
#
# Usage: setup.sh [--server | --slim | --full] [--hyprland] [--update]
#   --server  Install minimal remote server tooling (bash, tmux, vim)
#   --slim    Install common packages, dotfiles, shell (default)
#   --full    All of the above + mise-managed editor/CLI tools and Python utilities
#   --update  Run a full system package upgrade before installing (for first-time bootstrap)
#   --hyprland  Add the Arch desktop and opt into tty1 autostart

set -euo pipefail

# ─── Constants ────────────────────────────────────────────────────────────────

USER="${USER:-$(whoami)}"
PROFILE="slim"
DO_UPDATE=0
INSTALL_HYPRLAND=0
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZSH_AUTOSUGGESTIONS_VERSION="v0.7.1"
DOTFILES_LINK="$HOME/.dotfiles"
IS_WSL=0

# ─── Argument parsing ─────────────────────────────────────────────────────────

for arg in "$@"; do
  case $arg in
    --server) PROFILE="server" ;;
    --slim)   PROFILE="slim" ;;
    --full)   PROFILE="full" ;;
    --update) DO_UPDATE=1 ;;
    --hyprland) INSTALL_HYPRLAND=1 ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--server | --slim | --full] [--hyprland] [--update]"
      exit 1
      ;;
  esac
done

# ─── Helpers ──────────────────────────────────────────────────────────────────

info()    { echo "[setup] $*"; }
success() { echo "[setup] ✓ $*"; }
warning() { echo "[setup] ! $*"; }
die()     { echo "[setup] ERROR: $*" >&2; exit 1; }

get_login_shell() {
  local shell_path

  shell_path="$(getent passwd "$USER" 2>/dev/null | cut -d: -f7)"

  if [ -n "$shell_path" ]; then
    printf '%s\n' "$shell_path"
  else
    printf '%s\n' "${SHELL:-}"
  fi
}

step() {
  echo
  echo "──────────────────────────────────────────"
  echo "[setup] $*"
  echo "──────────────────────────────────────────"
}

# ─── Step 1: Detect OS ────────────────────────────────────────────────────────

step "1/12 — Detecting OS"

if [ ! -f /etc/os-release ]; then
  die "Cannot detect OS: /etc/os-release not found"
fi

. /etc/os-release

case "$ID" in
  fedora)
    PKG_MANAGER="dnf"
    PKG_INSTALL="sudo dnf install -y"
    PKG_SERVER="curl git make stow tmux vim"
    PKG_COMMON="curl gh git gcc libatomic make pipx python3-pip stow tmux unzip zsh"
    PKG_OPTIONAL="eza htop openssh-clients sqlite"
    info "Detected: Fedora $VERSION_ID"
    ;;
  ubuntu|debian)
    PKG_MANAGER="apt"
    PKG_INSTALL="sudo apt-get install -y"
    PKG_SERVER="curl git make stow tmux vim"
    PKG_COMMON="curl gh git gcc libatomic1 make pipx python3-pip stow tmux unzip zsh"
    PKG_OPTIONAL="eza htop openssh-client sqlite3"
    info "Detected: $PRETTY_NAME"
    ;;
  arch)
    PKG_MANAGER="pacman"
    PKG_INSTALL="sudo pacman -S --needed --noconfirm"
    PKG_SERVER="curl git less make man-db man-pages stow tmux vim which"
    PKG_COMMON="curl github-cli git gcc libatomic less make man-db man-pages openssh python-pipx python-pip stow tmux unzip which zsh"
    PKG_OPTIONAL="eza htop sqlite"
    info "Detected: $PRETTY_NAME"
    ;;
  *)
    die "Unsupported distro: $ID. Supported distros are Arch, Fedora, and Ubuntu/Debian."
    ;;
esac

# WSL detection
if grep -qi microsoft /proc/version 2>/dev/null; then
  IS_WSL=1
  info "Running under WSL2"
fi

if [ "$INSTALL_HYPRLAND" -eq 1 ]; then
  [ "$ID" = "arch" ] || die "--hyprland is supported only on Arch Linux"
  [ "$PROFILE" != "server" ] || die "--hyprland cannot be combined with --server"
  [ "$IS_WSL" -eq 0 ] || die "--hyprland requires native Arch Linux, not WSL"
fi

# ─── Step 2: Install common packages ─────────────────────────────────────────

step "2/12 — Installing packages"

case "$PKG_MANAGER" in
  dnf)
    if [ "$DO_UPDATE" -eq 1 ]; then
      sudo dnf update -y
    fi
    if [ "$PROFILE" = "server" ]; then
      info "Profile: server — installing minimal server packages"
      $PKG_INSTALL $PKG_SERVER
    else
      $PKG_INSTALL $PKG_COMMON
    fi
    ;;
  apt)
    sudo apt-get update -y
    if [ "$PROFILE" = "server" ]; then
      info "Profile: server — installing minimal server packages"
      $PKG_INSTALL $PKG_SERVER
    else
      $PKG_INSTALL $PKG_COMMON
    fi
    ;;
  pacman)
    if [ "$DO_UPDATE" -eq 1 ]; then
      sudo pacman -Syu --noconfirm
    fi
    if [ "$PROFILE" = "server" ]; then
      info "Profile: server — installing minimal server packages"
      $PKG_INSTALL $PKG_SERVER
    else
      $PKG_INSTALL $PKG_COMMON
    fi
    ;;
esac

success "Packages installed"

if [ "$INSTALL_HYPRLAND" -eq 1 ]; then
  info "Installing the Arch Hyprland desktop (hardware setup remains user-managed)"
  $PKG_INSTALL hyprland hypridle xdg-desktop-portal-hyprland \
    foot mako lxqt-policykit waybar wofi swaybg \
    grim slurp wl-clipboard cliphist nautilus sushi playerctl
fi

# ─── Step 3: Install Fedora container tooling ────────────────────────────────

step "3/12 — Installing Fedora container tooling"

if [ "$PKG_MANAGER" = "dnf" ]; then
  if [ "$PROFILE" != "full" ]; then
    info "Profile: $PROFILE — skipping Fedora container tooling"
  elif [ "$IS_WSL" -eq 1 ]; then
    info "WSL2 detected — skipping Fedora container tooling in setup.sh"
    info "See docs/setup_wsl.md for the WSL-specific Podman setup"
  else
    info "Installing Podman with Docker-compatible CLI on Fedora"
    sudo dnf install -y podman podman-docker docker-compose
    success "Fedora container tooling installed"
  fi
else
  info "Skipping Fedora container tooling on non-Fedora host"
fi

# ─── Step 4: Install optional packages (full only) ───────────────────────────

step "4/12 — Installing optional packages"

if [ "$PROFILE" = "full" ]; then
  info "Profile: full — installing optional packages"

  for pkg in $PKG_OPTIONAL; do
    $PKG_INSTALL "$pkg" || warning "Optional package '$pkg' failed to install — skipping"
  done
  success "Optional packages done"
else
  info "Profile: $PROFILE — skipping optional packages"
fi

# ─── Step 5: Set zsh as default shell ─────────────────────────────────────────

step "5/12 — Setting default shell"

if [ "$PROFILE" = "server" ]; then
  info "Profile: server — keeping current shell"
else

  ZSH_PATH="$(command -v zsh)"
  CURRENT_LOGIN_SHELL="$(get_login_shell)"

  if [ -n "$CURRENT_LOGIN_SHELL" ] && [ "$(readlink -f "$CURRENT_LOGIN_SHELL")" = "$(readlink -f "$ZSH_PATH")" ]; then
    info "zsh is already the default shell"
  else
    if grep -qF "$ZSH_PATH" /etc/shells; then
      sudo chsh -s "$ZSH_PATH" "$USER"
      success "Default shell set to $ZSH_PATH"
    else
      warning "zsh not found in /etc/shells — adding it"
      echo "$ZSH_PATH" | sudo tee -a /etc/shells
      sudo chsh -s "$ZSH_PATH" "$USER"
      success "Default shell set to $ZSH_PATH"
    fi
  fi
fi

# ─── Step 6: Symlink repo to ~/.dotfiles ──────────────────────────────────────

step "6/12 — Symlinking repo to ~/.dotfiles"

# Ensure required directories exist
mkdir -p "$HOME/.ssh" "$HOME/.config"

if [ "$DOTFILES_LINK" -ef "$REPO_DIR" ]; then
  info "~/.dotfiles already points to $REPO_DIR"
elif [ -e "$DOTFILES_LINK" ]; then
  die "~/.dotfiles already exists and is not a symlink to $REPO_DIR — remove it manually"
else
  ln -s "$REPO_DIR" "$DOTFILES_LINK"
  success "Created ~/.dotfiles -> $REPO_DIR"
fi

# ─── Step 7: Stow dotfiles ────────────────────────────────────────────────────

step "7/12 — Stowing dotfiles"

if [ "$PROFILE" = "server" ]; then
  STOW_TARGET_NAME="stow-server"
elif [ "$INSTALL_HYPRLAND" -eq 1 ]; then
  STOW_TARGET_NAME="stow-hyprland"
else
  STOW_TARGET_NAME="stow"
fi

if make -C "$REPO_DIR" "$STOW_TARGET_NAME"; then
  success "Dotfiles stowed"
else
  die "Stow failed. Resolve any conflicting files in $HOME, then rerun setup.sh. Use 'make -C $REPO_DIR unstow' only for links managed by this repo."
fi

# Keep machine-specific configuration outside the Stow package and worktree.
if [ "$INSTALL_HYPRLAND" -eq 1 ]; then
  bash "$REPO_DIR/scripts/configure-hyprland.sh"
fi

# ─── Step 8: Configure GNOME keybindings ─────────────────────────────────────

step "8/12 — Configuring GNOME keybindings"

if [ "$PROFILE" = "server" ]; then
  info "Profile: server — skipping GNOME keybindings"
elif "$REPO_DIR/scripts/configure-gnome-keybindings.sh"; then
  success "GNOME keybindings applied when supported"
else
  warning "GNOME keybindings setup failed — continuing"
fi

# ─── Step 9: Install Oh My Zsh ────────────────────────────────────────────────

step "9/12 — Installing Oh My Zsh"

if [ "$PROFILE" = "server" ]; then
  info "Profile: server — skipping Oh My Zsh"
elif [ -d "$HOME/.oh-my-zsh" ]; then
  info "Oh My Zsh already installed"
else
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    "" --unattended --keep-zshrc
  success "Oh My Zsh installed"
fi

# ─── Step 10: Install zsh-autosuggestions ─────────────────────────────────────

step "10/12 — Installing zsh-autosuggestions"

ZSH_AUTOSUGGEST_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions"

if [ "$PROFILE" = "server" ]; then
  info "Profile: server — skipping zsh-autosuggestions"
elif [ -d "$ZSH_AUTOSUGGEST_DIR" ]; then
  info "zsh-autosuggestions already installed"
else
  git clone --branch "$ZSH_AUTOSUGGESTIONS_VERSION" --depth 1 \
    https://github.com/zsh-users/zsh-autosuggestions \
    "$ZSH_AUTOSUGGEST_DIR"
  success "zsh-autosuggestions $ZSH_AUTOSUGGESTIONS_VERSION installed"
fi

# ─── Step 11: Install dev tools (full only) ───────────────────────────────────

step "11/12 — Installing dev tools"

if [ "$PROFILE" = "full" ]; then

  # Keep existing nvm, Bob, and system installations available for rollback.
  export PATH="$HOME/.local/bin:$PATH"
  if command -v mise &>/dev/null; then
    info "mise already installed"
  else
    info "Installing mise"
    curl -fsSL https://mise.run | sh
    success "mise installed"
  fi

  # Install from the stowed declarative config without rewriting it.
  (cd "$HOME" && mise install)
  mise reshim
  success "Configured development tools installed via mise"

  # uv
  if command -v uv &>/dev/null; then
    info "uv already installed"
  else
    info "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh || warning "uv install failed"
    success "uv installed"
  fi

  # llm
  if command -v llm &>/dev/null; then
    info "llm already installed"
  else
    pipx install llm
    success "llm installed"
  fi

else
  info "Profile: $PROFILE — skipping dev tools"
fi

# ─── Step 12: Done ────────────────────────────────────────────────────────────

step "12/12 — Done"

echo
echo "  Setup complete (profile: $PROFILE)"
if [ "$INSTALL_HYPRLAND" -eq 1 ]; then
  echo "  Hyprland is configured to start on your next local Arch tty1 login."
  echo "  Ensure graphics drivers are configured before starting Hyprland."
  echo "  Local overrides: ~/.config/hypr/hyprland.lua"
  echo "  Disable tty1 autostart: remove ~/.local/state/dotfiles/hyprland/autostart"
fi
echo "  Restart your shell to apply all changes:"
echo
if [ "$PROFILE" = "server" ]; then
  echo "    exec bash -l"
else
  echo "    exec zsh -l"
fi
echo
