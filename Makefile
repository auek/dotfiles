STOW_PACKAGES = zshrc zprofile tmux nvim kitty foot hypr waybar wofi mako opencode claude espanso
STOW_PACKAGES_SERVER = bashrc-server tmux-server vim-server
STOW_PACKAGES_GTK = gtk
STOW_PACKAGES_FOOT = foot
STOW_TARGET = $(HOME)

.PHONY: stow unstow restow stow-server unstow-server stow-gtk unstow-gtk stow-foot unstow-foot

stow:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES)

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
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_FOOT)

unstow-foot:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_FOOT)
