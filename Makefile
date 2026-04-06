STOW_PACKAGES = zshrc zprofile tmux nvim kitty opencode claude
STOW_TARGET = $(HOME)

.PHONY: stow unstow restow

stow:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES)

unstow:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES)

restow: unstow stow
