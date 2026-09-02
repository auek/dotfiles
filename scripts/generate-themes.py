#!/usr/bin/env python3
"""Generate native theme fragments from semantic JSON palettes.

Usage:
  scripts/generate-themes.py generate   # render palettes x templates into packs
  scripts/generate-themes.py check      # verify palettes, templates, and packs agree

Uses only the Python standard library. Output is deterministic: fragments are a
pure function of their palette JSON and template file, and writes are atomic.
"""

import argparse
import json
import os
import pathlib
import string
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PALETTES_DIR = pathlib.Path(__file__).resolve().parent / "palettes"
TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent / "templates"
THEMES_DIR = ROOT / "packages" / "themes" / ".local" / "share" / "dotfiles" / "themes"

FRAGMENTS = (
    "foot.ini",
    "tmux.conf",
    "nvim.lua",
    "waybar.css",
    "hyprland.lua",
    "wofi.css",
    "mako.conf",
    "swaybg-color",
    "wallpaper-name",
)


class TemplateError(Exception):
    pass


def palette_names():
    return sorted(p.stem for p in PALETTES_DIR.glob("*.json"))


def load_palette(name):
    path = PALETTES_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as fh:
        palette = json.load(fh)
    colors = palette["colors"]
    meta = palette["meta"]
    overlap = set(colors) & set(meta)
    if overlap:
        raise TemplateError(f"{name}: role defined in both colors and meta: {sorted(overlap)}")
    if palette.get("name") != name:
        raise TemplateError(f"{name}: palette 'name' does not match file name")
    return palette


def template_path(fragment, theme):
    themed = TEMPLATES_DIR / f"{fragment}.{theme}"
    if themed.is_file():
        return themed
    shared = TEMPLATES_DIR / fragment
    if shared.is_file():
        return shared
    return None


def render(palette, fragment, theme):
    path = template_path(fragment, theme)
    if path is None:
        raise TemplateError(f"{theme}: no template for {fragment}")
    template = string.Template(path.read_text(encoding="utf-8"))
    substitutions = dict(palette["colors"])
    substitutions.update(palette["meta"])
    substitutions.setdefault("name", palette["name"])
    try:
        return template.substitute(substitutions)
    except KeyError as exc:
        raise TemplateError(
            f"{theme}/{fragment}: template references missing role {exc.args[0]!r}"
        ) from exc


def pack_issues(theme_dir):
    missing = [f for f in FRAGMENTS if not (theme_dir / f).is_file()]
    empty = [
        f for f in FRAGMENTS
        if (theme_dir / f).is_file() and (theme_dir / f).stat().st_size == 0
    ]
    return missing, empty


def action_generate(args):
    generated = 0
    for name in palette_names():
        palette = load_palette(name)
        theme_dir = THEMES_DIR / name
        theme_dir.mkdir(parents=True, exist_ok=True)
        for fragment in FRAGMENTS:
            output = render(palette, fragment, name)
            target = theme_dir / fragment
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=theme_dir, delete=False
            ) as fh:
                fh.write(output)
                tmp = pathlib.Path(fh.name)
            os.replace(tmp, target)
            generated += 1
    print(f"generated {generated} fragments for {', '.join(palette_names())}")
    return 0


def action_check(args):
    errors = []
    names = palette_names()
    for name in names:
        try:
            palette = load_palette(name)
        except TemplateError as exc:
            errors.append(str(exc))
            continue
        theme_dir = THEMES_DIR / name
        if not theme_dir.is_dir():
            errors.append(f"{name}: theme pack directory missing")
            continue
        missing, empty = pack_issues(theme_dir)
        for fragment in missing:
            errors.append(f"{name}: missing fragment {fragment}")
        for fragment in empty:
            errors.append(f"{name}: empty fragment {fragment}")
        for fragment in FRAGMENTS:
            try:
                output = render(palette, fragment, name)
            except TemplateError as exc:
                errors.append(str(exc))
                continue
            target = theme_dir / fragment
            if not target.is_file():
                continue
            if target.read_text(encoding="utf-8") != output:
                errors.append(f"{name}: stale fragment {fragment} (run generate)")
    if THEMES_DIR.is_dir():
        for path in sorted(THEMES_DIR.iterdir()):
            if path.is_dir() and path.name not in names:
                errors.append(
                    f"{path.name}: orphan theme pack (no palette; remove the "
                    "directory or restore its palette)"
                )
    if errors:
        for error in errors:
            print(f"check failed: {error}", file=sys.stderr)
        return 1
    print("check ok: palettes, templates, and packs are consistent")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("generate", "check"))
    args = parser.parse_args(argv)
    if args.action == "generate":
        return action_generate(args)
    return action_check(args)


if __name__ == "__main__":
    sys.exit(main())
