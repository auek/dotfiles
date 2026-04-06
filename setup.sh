#!/usr/bin/env bash
#
# setup.sh — Bootstrap development environment
#
# Usage: setup.sh [--slim | --full]
#   --slim  Install common packages, dotfiles, shell (default)
#   --full  All of the above + dev tools (nvim, nvm, node, tldr, llm)

set -euo pipefail

# ─── Constants ────────────────────────────────────────────────────────────────

USER="${USER:-$(whoami)}"
PROFILE="slim"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZSH_AUTOSUGGESTIONS_VERSION="v0.7.1"
NVM_VERSION="v0.40.1"
KITTY_VERSION="0.46.2"
KITTY_ARCHIVE_URL="https://github.com/kovidgoyal/kitty/releases/download/v${KITTY_VERSION}/kitty-${KITTY_VERSION}-x86_64.txz"
DOTFILES_LINK="$HOME/.dotfiles"
IS_WSL=0

# ─── Argument parsing ─────────────────────────────────────────────────────────

for arg in "$@"; do
  case $arg in
    --slim) PROFILE="slim" ;;
    --full) PROFILE="full" ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--slim | --full]"
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

install_kitty() {
  local current_version=""
  local tmpdir

  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.config"

  if [ -x "$HOME/.local/kitty.app/bin/kitty" ]; then
    current_version="$("$HOME/.local/kitty.app/bin/kitty" --version | awk '{print $2}')"
  fi

  if [ "$current_version" = "$KITTY_VERSION" ]; then
    info "kitty $KITTY_VERSION already installed in ~/.local/kitty.app"
  else
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' RETURN

    info "Installing kitty $KITTY_VERSION from upstream binary"
    curl -L "$KITTY_ARCHIVE_URL" -o "$tmpdir/kitty.txz"
    rm -rf "$HOME/.local/kitty.app"
    tar -xJf "$tmpdir/kitty.txz" -C "$HOME/.local"
    success "kitty $KITTY_VERSION installed"

    rm -rf "$tmpdir"
    trap - RETURN
  fi

  ln -sf "$HOME/.local/kitty.app/bin/kitty" "$HOME/.local/bin/kitty"
  ln -sf "$HOME/.local/kitty.app/bin/kitten" "$HOME/.local/bin/kitten"
  cp "$HOME/.local/kitty.app/share/applications/kitty.desktop" "$HOME/.local/share/applications/kitty.desktop"
  sed -i "s|^TryExec=.*|TryExec=$HOME/.local/kitty.app/bin/kitty|" "$HOME/.local/share/applications/kitty.desktop"
  sed -i "s|^Exec=.*|Exec=$HOME/.local/kitty.app/bin/kitty|" "$HOME/.local/share/applications/kitty.desktop"
  sed -i "s|^Icon=.*|Icon=$HOME/.local/kitty.app/share/icons/hicolor/256x256/apps/kitty.png|" "$HOME/.local/share/applications/kitty.desktop"
  printf 'kitty.desktop\n' > "$HOME/.config/xdg-terminals.list"
}

step() {
  echo
  echo "──────────────────────────────────────────"
  echo "[setup] $*"
  echo "──────────────────────────────────────────"
}

# ─── Step 1: Detect OS ────────────────────────────────────────────────────────

step "1/11 — Detecting OS"

if [ ! -f /etc/os-release ]; then
  die "Cannot detect OS: /etc/os-release not found"
fi

. /etc/os-release

case "$ID" in
  fedora)
    PKG_MANAGER="dnf"
    PKG_INSTALL="sudo dnf install -y"
    PKG_COMMON="curl git gcc libatomic make pipx python3-pip stow tmux unzip zsh"
    PKG_OPTIONAL="exa fd-find fzf htop bat ripgrep openssh-clients"
    PKG_KITTY_FONT="jetbrains-mono-fonts"
    info "Detected: Fedora $VERSION_ID"
    ;;
  ubuntu|debian)
    PKG_MANAGER="apt"
    PKG_INSTALL="sudo apt-get install -y"
    PKG_COMMON="curl git gcc libatomic1 make pipx python3-pip stow tmux unzip zsh"
    PKG_OPTIONAL="exa fd-find fzf htop bat ripgrep openssh-client"
    PKG_KITTY_FONT="fonts-jetbrains-mono"
    info "Detected: $PRETTY_NAME"
    ;;
  *)
    die "Unsupported distro: $ID. Only Fedora and Ubuntu/Debian are supported."
    ;;
esac

# WSL detection (skip Kitty install under WSL)
if grep -qi microsoft /proc/version 2>/dev/null; then
  IS_WSL=1
  info "Running under WSL2"
fi

# ─── Step 2: Install common packages ─────────────────────────────────────────

step "2/11 — Installing common packages"

case "$PKG_MANAGER" in
  dnf)
    sudo dnf update -y
    $PKG_INSTALL $PKG_COMMON
    ;;
  apt)
    sudo apt-get update -y
    $PKG_INSTALL $PKG_COMMON
    ;;
esac

success "Common packages installed"

# ─── Step 3: Install Fedora container tooling ────────────────────────────────

step "3/11 — Installing Fedora container tooling"

if [ "$PKG_MANAGER" = "dnf" ]; then
  if [ "$PROFILE" != "full" ]; then
    info "Profile: slim — skipping Fedora container tooling"
  elif [ "$IS_WSL" -eq 1 ]; then
    info "WSL2 detected — skipping Fedora container tooling in setup.sh"
    info "See docs/SETUP_WSL.md for the WSL-specific Podman setup"
  else
    info "Installing Podman with Docker-compatible CLI on Fedora"
    sudo dnf install -y podman podman-docker docker-compose
    success "Fedora container tooling installed"
  fi
else
  info "Skipping Fedora container tooling on non-Fedora host"
fi

# ─── Step 4: Install optional packages (full only) ───────────────────────────

step "4/11 — Installing optional packages"

if [ "$PROFILE" = "full" ]; then
  info "Profile: full — installing optional packages"

  if [ "$IS_WSL" -eq 0 ]; then
    $PKG_INSTALL "$PKG_KITTY_FONT" || warning "Optional package '$PKG_KITTY_FONT' failed to install — skipping"
    install_kitty || warning "Upstream kitty install failed — skipping"
  else
    info "WSL2 detected — skipping Kitty and JetBrains Mono"
  fi

  for pkg in $PKG_OPTIONAL; do
    $PKG_INSTALL "$pkg" || warning "Optional package '$pkg' failed to install — skipping"
  done
  success "Optional packages done"
else
  info "Profile: slim — skipping optional packages"
fi

# ─── Step 5: Set zsh as default shell ─────────────────────────────────────────

step "5/11 — Setting zsh as default shell"

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

# ─── Step 6: Symlink repo to ~/.dotfiles ──────────────────────────────────────

step "6/11 — Symlinking repo to ~/.dotfiles"

# Ensure required directories exist
mkdir -p "$HOME/.ssh" "$HOME/.config"

if [ -L "$DOTFILES_LINK" ] && [ "$(readlink "$DOTFILES_LINK")" = "$REPO_DIR" ]; then
  info "~/.dotfiles already points to $REPO_DIR"
elif [ -e "$DOTFILES_LINK" ]; then
  die "~/.dotfiles already exists and is not a symlink to $REPO_DIR — remove it manually"
else
  ln -s "$REPO_DIR" "$DOTFILES_LINK"
  success "Created ~/.dotfiles -> $REPO_DIR"
fi

# ─── Step 7: Stow dotfiles ────────────────────────────────────────────────────

step "7/11 — Stowing dotfiles"

if make -C "$REPO_DIR" stow; then
  success "Dotfiles stowed"
else
  die "Stow failed. Resolve any conflicting files in $HOME, then rerun setup.sh. Use 'make -C $REPO_DIR unstow' only for links managed by this repo."
fi

if "$REPO_DIR/scripts/configure-compose-key.sh"; then
  success "Compose key preferences applied when supported"
else
  warning "Compose key preference setup failed — continuing"
fi

# ─── Step 8: Install Oh My Zsh ────────────────────────────────────────────────

step "8/11 — Installing Oh My Zsh"

if [ -d "$HOME/.oh-my-zsh" ]; then
  info "Oh My Zsh already installed"
else
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    "" --unattended --keep-zshrc
  success "Oh My Zsh installed"
fi

# ─── Step 9: Install zsh-autosuggestions ──────────────────────────────────────

step "9/11 — Installing zsh-autosuggestions"

ZSH_AUTOSUGGEST_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions"

if [ -d "$ZSH_AUTOSUGGEST_DIR" ]; then
  info "zsh-autosuggestions already installed"
else
  git clone --branch "$ZSH_AUTOSUGGESTIONS_VERSION" --depth 1 \
    https://github.com/zsh-users/zsh-autosuggestions \
    "$ZSH_AUTOSUGGEST_DIR"
  success "zsh-autosuggestions $ZSH_AUTOSUGGESTIONS_VERSION installed"
fi

# ─── Step 10: Install dev tools (full only) ───────────────────────────────────

step "10/11 — Installing dev tools"

if [ "$PROFILE" = "full" ]; then

  # bob-nvim → stable neovim
  if command -v bob &>/dev/null; then
    info "bob already installed"
  else
    info "Installing bob-nvim"
    cargo install bob-nvim || {
      # Fallback: install cargo first if not present
      if ! command -v cargo &>/dev/null; then
        info "cargo not found — installing rust toolchain"
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
        # shellcheck source=/dev/null
        . "$HOME/.cargo/env"
      fi
      cargo install bob-nvim
    }
    success "bob-nvim installed"
  fi

  if command -v nvim &>/dev/null; then
    info "neovim already installed"
  else
    bob use stable
    success "neovim stable installed via bob"
  fi

  # nvm
  if [ -d "$HOME/.nvm" ]; then
    info "nvm already installed"
  else
    info "Installing nvm $NVM_VERSION"
    curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh" | bash
    success "nvm $NVM_VERSION installed"
  fi

  # node LTS (load nvm first)
  export NVM_DIR="$HOME/.nvm"
  # shellcheck source=/dev/null
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

  if command -v node &>/dev/null; then
    info "node already installed: $(node --version)"
  else
    nvm install --lts
    success "node LTS installed"
  fi

  # tldr
  if command -v tldr &>/dev/null; then
    info "tldr already installed"
  else
    pipx install tldr
    tldr --update || true
    success "tldr installed"
  fi

  # llm
  if command -v llm &>/dev/null; then
    info "llm already installed"
  else
    pipx install llm
    success "llm installed"
  fi

else
  info "Profile: slim — skipping dev tools"
fi

# ─── Step 11: Done ────────────────────────────────────────────────────────────

step "11/11 — Done"

echo
echo "  Setup complete (profile: $PROFILE)"
echo "  Restart your shell to apply all changes:"
echo
echo "    exec zsh -l"
echo
