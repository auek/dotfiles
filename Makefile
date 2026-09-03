STOW_PACKAGES = zshrc zprofile tmux nvim foot themes hypr waybar wofi mako opencode claude espanso bob
STOW_PACKAGES_SERVER = bashrc-server tmux-server vim-server
STOW_PACKAGES_GTK = gtk
STOW_PACKAGES_FOOT = foot
STOW_DIR = $(CURDIR)/packages
STOW_TARGET = $(HOME)
# Keep shared XDG directories writable for tools such as uv and pipx.
STOW = stow --no-folding --dir=$(STOW_DIR) --target=$(STOW_TARGET)

.PHONY: stow unstow restow stow-server unstow-server stow-gtk unstow-gtk stow-foot unstow-foot themes-generate themes-check

themes-generate:
	python3 scripts/generate-themes.py generate

themes-check:
	python3 scripts/generate-themes.py check

stow:
	mkdir -p "$(STOW_TARGET)/.local/state"
	$(STOW) $(STOW_PACKAGES)
	@if [ ! -e "$(STOW_TARGET)/.local/state/dotfiles/theme/current" ]; then \
		HOME="$(STOW_TARGET)" "$(STOW_TARGET)/.local/bin/theme-set" everforest; \
	fi

unstow:
	$(STOW) --delete $(STOW_PACKAGES)

restow: stow

stow-server:
	$(STOW) --restow $(STOW_PACKAGES_SERVER)

unstow-server:
	$(STOW) --delete $(STOW_PACKAGES_SERVER)

stow-gtk:
	$(STOW) --restow $(STOW_PACKAGES_GTK)

unstow-gtk:
	$(STOW) --delete $(STOW_PACKAGES_GTK)

stow-foot:
	mkdir -p "$(STOW_TARGET)/.local/state"
	$(STOW) --restow themes $(STOW_PACKAGES_FOOT)
	@if [ ! -e "$(STOW_TARGET)/.local/state/dotfiles/theme/current" ]; then \
		HOME="$(STOW_TARGET)" "$(STOW_TARGET)/.local/bin/theme-set" everforest; \
	fi

unstow-foot:
	$(STOW) --delete $(STOW_PACKAGES_FOOT)
