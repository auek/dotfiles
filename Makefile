STOW_PACKAGES = zshrc zprofile readline tmux nvim themes mise tealdeer
STOW_INCLUDE ?=
STOW_PACKAGES_HYPRLAND = foot hypr waybar wofi mako
STOW_PACKAGES_SERVER = bashrc-server readline tmux-server vim-server
STOW_PACKAGES_GTK = gtk
STOW_PACKAGES_FOOT = foot
STOW_DIR = $(CURDIR)/packages
STOW_TARGET = $(HOME)
# Keep shared XDG directories writable for tools such as uv and pipx.
STOW = stow --no-folding --dir=$(STOW_DIR) --target=$(STOW_TARGET)

# Ordinary machine-local preferences, never Stow-managed.
-include $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/dotfiles/local.mk
STOW_SELECTED_PACKAGES = $(sort $(STOW_PACKAGES) $(STOW_INCLUDE))

.PHONY: stow unstow restow stow-hyprland unstow-hyprland stow-server unstow-server stow-gtk unstow-gtk stow-foot unstow-foot themes-generate themes-check check check-runtime

themes-generate:
	python3 scripts/generate-themes.py generate

themes-check:
	python3 scripts/generate-themes.py check

restow: STOW += --restow

stow restow:
	mkdir -p "$(STOW_TARGET)/.local/state"
	$(STOW) $(STOW_SELECTED_PACKAGES)
	@if [ ! -e "$(STOW_TARGET)/.local/state/dotfiles/theme/current" ]; then \
		HOME="$(STOW_TARGET)" "$(STOW_TARGET)/.local/bin/theme-set" everforest; \
	fi

unstow:
	$(STOW) --delete $(STOW_SELECTED_PACKAGES)

stow-hyprland: stow
	$(STOW) $(STOW_PACKAGES_HYPRLAND)

unstow-hyprland:
	$(STOW) --delete $(STOW_PACKAGES_HYPRLAND)

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

check:
	python3 scripts/check.py static

check-runtime:
	python3 scripts/check.py runtime --fixtures "$(FIXTURES)"
