#!/usr/bin/env bash
#
# setup.sh — Bootstrap development environment
#
# Usage: setup.sh [--slim | --full]
#   --slim  Install common packages, dotfiles, shell (default)
#   --full  All of the above + dev tools (nvim, nvm, node, tldr)

set -euo pipefail

# ─── Constants ────────────────────────────────────────────────────────────────

USER="${USER:-$(whoami)}"
PROFILE="slim"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZSH_AUTOSUGGESTIONS_VERSION="v0.7.1"
NVM_VERSION="v0.40.1"
DOTFILES_LINK="$HOME/.dotfiles"

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

step() {
  echo
  echo "──────────────────────────────────────────"
  echo "[setup] $*"
  echo "──────────────────────────────────────────"
}

# ─── Step 1: Detect OS ────────────────────────────────────────────────────────

step "1/10 — Detecting OS"

if [ ! -f /etc/os-release ]; then
  die "Cannot detect OS: /etc/os-release not found"
fi

. /etc/os-release

case "$ID" in
  fedora)
    PKG_MANAGER="dnf"
    PKG_INSTALL="sudo dnf install -y"
    PKG_COMMON="curl git make pipx python3 stow tmux unzip zsh"
    PKG_OPTIONAL="exa fd-find fzf htop bat ripgrep openssh-clients"
    info "Detected: Fedora $VERSION_ID"
    ;;
  ubuntu|debian)
    PKG_MANAGER="apt"
    PKG_INSTALL="sudo apt-get install -y"
    PKG_COMMON="curl git make pipx python3 stow tmux unzip zsh"
    PKG_OPTIONAL="exa fd-find fzf htop bat ripgrep openssh-client"
    info "Detected: $PRETTY_NAME"
    ;;
  *)
    die "Unsupported distro: $ID. Only Fedora and Ubuntu/Debian are supported."
    ;;
esac

# WSL detection (informational only)
if grep -qi microsoft /proc/version 2>/dev/null; then
  info "Running under WSL2"
fi

# ─── Step 2: Install common packages ─────────────────────────────────────────

step "2/10 — Installing common packages"

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

# ─── Step 3: Install optional packages (full only) ───────────────────────────

step "3/10 — Installing optional packages"

if [ "$PROFILE" = "full" ]; then
  info "Profile: full — installing optional packages"
  for pkg in $PKG_OPTIONAL; do
    $PKG_INSTALL "$pkg" || warning "Optional package '$pkg' failed to install — skipping"
  done
  success "Optional packages done"
else
  info "Profile: slim — skipping optional packages"
fi

# ─── Step 4: Set zsh as default shell ─────────────────────────────────────────

step "4/10 — Setting zsh as default shell"

ZSH_PATH="$(command -v zsh)"

if [ "$SHELL" = "$ZSH_PATH" ]; then
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

# ─── Step 5: Symlink repo to ~/.dotfiles ──────────────────────────────────────

step "5/10 — Symlinking repo to ~/.dotfiles"

if [ -L "$DOTFILES_LINK" ] && [ "$(readlink "$DOTFILES_LINK")" = "$REPO_DIR" ]; then
  info "~/.dotfiles already points to $REPO_DIR"
elif [ -e "$DOTFILES_LINK" ]; then
  die "~/.dotfiles already exists and is not a symlink to $REPO_DIR — remove it manually"
else
  ln -s "$REPO_DIR" "$DOTFILES_LINK"
  success "Created ~/.dotfiles -> $REPO_DIR"
fi

# ─── Step 6: Stow dotfiles ────────────────────────────────────────────────────

step "6/10 — Stowing dotfiles"

make -C "$REPO_DIR" stow
success "Dotfiles stowed"

# ─── Step 7: Install Oh My Zsh ────────────────────────────────────────────────

step "7/10 — Installing Oh My Zsh"

if [ -d "$HOME/.oh-my-zsh" ]; then
  info "Oh My Zsh already installed"
else
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    "" --unattended --keep-zshrc
  success "Oh My Zsh installed"
fi

# ─── Step 8: Install zsh-autosuggestions ──────────────────────────────────────

step "8/10 — Installing zsh-autosuggestions"

ZSH_AUTOSUGGEST_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions"

if [ -d "$ZSH_AUTOSUGGEST_DIR" ]; then
  info "zsh-autosuggestions already installed"
else
  git clone --branch "$ZSH_AUTOSUGGESTIONS_VERSION" --depth 1 \
    https://github.com/zsh-users/zsh-autosuggestions \
    "$ZSH_AUTOSUGGEST_DIR"
  success "zsh-autosuggestions $ZSH_AUTOSUGGESTIONS_VERSION installed"
fi

# ─── Step 9: Install dev tools (full only) ────────────────────────────────────

step "9/10 — Installing dev tools"

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

else
  info "Profile: slim — skipping dev tools"
fi

# ─── Step 10: Done ────────────────────────────────────────────────────────────

step "10/10 — Done"

echo
echo "  Setup complete (profile: $PROFILE)"
echo "  Restart your shell to apply all changes:"
echo
echo "    exec zsh -l"
echo
