STOW_PACKAGES = zshrc zprofile tmux nvim foot themes hypr waybar wofi mako opencode claude espanso
STOW_PACKAGES_SERVER = bashrc-server tmux-server vim-server
STOW_PACKAGES_GTK = gtk
STOW_PACKAGES_FOOT = foot
STOW_TARGET = $(HOME)

.PHONY: stow unstow restow stow-server unstow-server stow-gtk unstow-gtk stow-foot unstow-foot

stow:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES)
	@if [ ! -e "$(STOW_TARGET)/.local/state/dotfiles/theme/current" ]; then \
		HOME="$(STOW_TARGET)" "$(STOW_TARGET)/.local/bin/theme-set" everforest; \
	fi

unstow:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES)

restow: unstow stow

stow-server:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)

unstow-server:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)

stow-gtk:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_GTK)

unstow-gtk:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_GTK)

stow-foot:
	stow --restow --target=$(STOW_TARGET) themes $(STOW_PACKAGES_FOOT)
	@if [ ! -e "$(STOW_TARGET)/.local/state/dotfiles/theme/current" ]; then \
		HOME="$(STOW_TARGET)" "$(STOW_TARGET)/.local/bin/theme-set" everforest; \
	fi

unstow-foot:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_FOOT)
