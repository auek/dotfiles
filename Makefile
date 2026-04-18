STOW_PACKAGES = zshrc zprofile tmux nvim kitty opencode claude espanso
STOW_PACKAGES_SERVER = bashrc-server tmux-server vim-server
STOW_TARGET = $(HOME)

.PHONY: stow unstow restow stow-server unstow-server

stow:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES)

unstow:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES)

restow: unstow stow

stow-server:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)

unstow-server:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)
