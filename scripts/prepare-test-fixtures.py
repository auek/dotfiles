#!/usr/bin/env python3
"""Download test dependencies into an explicit disposable directory, never HOME.

Linux x86_64; requires Python 3.11+, Git, curl, tar, make and a C compiler.
Preparation uses the network. The checks themselves can run without it.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("the fixture binaries currently target Linux x86_64")
    dest = args.directory.resolve()
    inputs = [ROOT / "scripts/test-fixtures.json", ROOT / "scripts/prepare-test-fixtures.py",
              ROOT / "packages/nvim/.config/nvim/lazy-lock.json", ROOT / "packages/mise/.config/mise/config.toml"]
    identity = hashlib.sha256(b"".join(path.read_bytes() for path in inputs)).hexdigest()
    ready = dest / "ready.json"
    if ready.exists() and json.loads(ready.read_text())["identity"] == identity:
        print(f"Fixtures ready: {dest}")
        return
    if dest.exists() and any(dest.iterdir()):
        parser.error("use an empty directory (existing fixtures differ or preparation was interrupted)")
    dest.mkdir(parents=True, exist_ok=True)
    config = json.loads(inputs[0].read_text())
    node = tomllib.loads(inputs[3].read_text())["tools"]["node"]
    home = dest / "home"
    home.mkdir()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("MISE_", "__MISE_", "NPM_CONFIG_", "npm_config_", "XDG_", "GIT_CONFIG_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".data"), XDG_STATE_HOME=str(home / ".state"),
               XDG_CACHE_HOME=str(home / ".cache"), MISE_DATA_DIR=str(dest / "mise-data"),
               MISE_TRUSTED_CONFIG_PATHS=str(home), MISE_YES="1",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def run(*command, cwd=dest):
        print("+ " + " ".join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True, timeout=600)

    def download(url, output):
        run("curl", "--fail", "--location", "--retry", "3", "--silent", "--show-error", url, "-o", output)

    def archive(url, target, checksums=None, sha256=None):
        filename = url.rsplit("/", 1)[1]
        output = dest / filename
        download(url, output)
        checksum_file = dest / (filename + ".checksums")
        if checksums:
            download(checksums, checksum_file)
            matching = [line.split()[0] for line in checksum_file.read_text().splitlines()
                        if line.split() and line.split()[-1].lstrip("*./") == filename]
        else:
            matching = [sha256]
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if matching != [digest]:
            raise RuntimeError(f"Checksum mismatch or missing entry: {filename}")
        target.mkdir()
        run("tar", "xf", output, "--strip-components=1", "-C", target)
        output.unlink()
        checksum_file.unlink(missing_ok=True)

    for version, name in ((node, "node"), (config["other-node"], "other-node")):
        base = f"https://nodejs.org/dist/v{version}"
        archive(f"{base}/node-v{version}-linux-x64.tar.xz", dest / name, f"{base}/SHASUMS256.txt")
    version = config["neovim"]
    base = f"https://github.com/neovim/neovim/releases/download/v{version}"
    archive(f"{base}/nvim-linux-x86_64.tar.gz", dest / "neovim", sha256=config["neovim-sha256"])
    version = config["mise"]
    base = f"https://github.com/jdx/mise/releases/download/v{version}"
    archive(f"{base}/mise-v{version}-linux-x64.tar.xz", dest / "mise", f"{base}/SHASUMS256.txt")
    bindir = dest / "bin"
    bindir.mkdir()
    for name, binary in {"node": "node/bin/node", "npm": "node/bin/npm", "npx": "node/bin/npx",
                         "nvim": "neovim/bin/nvim", "mise": "mise/bin/mise"}.items():
        (bindir / name).symlink_to(dest / binary)
    env["PATH"] = str(bindir) + os.pathsep + env["PATH"]

    def checkout(repo, revision, directory):
        directory.mkdir(parents=True)
        run("git", "init", "-q", directory)
        run("git", "-C", directory, "fetch", "--depth=1", f"https://github.com/{repo}.git", revision)
        run("git", "-C", directory, "checkout", "-q", "--detach", "FETCH_HEAD")

    checkout("ohmyzsh/ohmyzsh", config["ohmyzsh"], dest / "ohmyzsh")
    checkout("zsh-users/zsh-autosuggestions", config["autosuggestions"],
             dest / "ohmyzsh/custom/plugins/zsh-autosuggestions")
    pins = json.loads(inputs[2].read_text())
    repos = {}
    for path in (ROOT / "packages/nvim/.config/nvim/lua").rglob("*.lua"):
        for repo in re.findall(r'"([\w.-]+/[\w.-]+)"', path.read_text()):
            if repo.split("/")[1] in pins:
                repos[repo.split("/")[1]] = repo
    if set(repos) != set(pins):
        raise RuntimeError(f"Plugin sources missing: {set(pins) - set(repos)}")
    for name, pin in pins.items():
        checkout(repos[name], pin["commit"], dest / "plugins" / name)
    run("make", cwd=dest / "plugins/telescope-fzf-native.nvim")
    # Build the generated C sources at the plugin's own pinned revisions. This
    # needs no tree-sitter CLI binary (whose glibc floor can exclude EL9).
    treesitter = dest / "plugins/nvim-treesitter"
    metadata = dest / "parser-metadata.json"
    run("nvim", "--headless", "-u", "NONE", "-i", "NONE", "-c",
        'lua local p=dofile(' + json.dumps(str(treesitter / "lua/nvim-treesitter/parsers.lua")) +
        '); vim.fn.writefile({vim.json.encode(p)}, ' + json.dumps(str(metadata)) + ')', "-c", "qa!")
    parsers = json.loads(metadata.read_text())
    output = dest / "parsers"
    (output / "parser").mkdir(parents=True)
    shutil.copytree(treesitter / "runtime/queries", output / "queries")
    for language in ("bash", "typescript", "markdown", "markdown_inline"):
        info = parsers[language]["install_info"]
        source = dest / "grammar-sources" / language
        checkout(info["url"].removeprefix("https://github.com/"), info["revision"], source)
        source = source / info.get("location", "") / "src"
        files = [source / "parser.c"]
        if (source / "scanner.c").exists():
            files.append(source / "scanner.c")
        run("cc", "-shared", "-fPIC", "-O2", "-I", source, *files, "-o", output / "parser" / f"{language}.so")
    for name, packages in config["npm"].items():
        directory = dest / name
        directory.mkdir()
        (directory / "package.json").write_text(json.dumps({"private": True}))
        run("npm", "install", "--no-audit", "--no-fund", "--save-exact", *packages, cwd=directory)
    # Mason's runtime interface is its bin directory; no registry/downloads are
    # needed to exercise the configured servers against real project files.
    mason = dest / "mason"
    (mason / "bin").mkdir(parents=True)
    for binary in (dest / "lsp/node_modules/.bin").iterdir():
        (mason / "bin" / binary.name).symlink_to(binary)
    # Pin the official schema to a commit instead of consulting the live URL.
    checkout("microsoft/azure-pipelines-vscode", config["azure-schema"], dest / "azure-schema")
    shutil.copy2(dest / "azure-schema/service-schema.json", mason / "azure-schema.json")
    # Preserve the Aqua backend metadata required by the real mise tests.
    run("mise", "install", f"aqua:neovim/neovim@{config['neovim']}", cwd=home)
    ready.write_text(json.dumps({"identity": identity, "versions": config}, indent=2) + "\n")
    print(f"Fixtures ready: {dest}")


if __name__ == "__main__":
    main()
