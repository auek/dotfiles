#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yml"

# Default values for options
distro="ubuntu"
profile="slim"

usage() {
  echo "Docker Development Environment Setup Script"
  echo
  echo "Usage: $0 [-d|--distro <distro>] [-t|--tags <profile>]"
  echo
  echo "Options:"
  echo "  -h, --help              Show this help message"
  echo "  -d, --distro <distro>   Specify distribution (arch|fedora|ubuntu)"
  echo "                          Default: ubuntu"
  echo "  -t, --tags <profile>    Specify installation profile:"
  echo "                          - server: Minimal remote/headless server install"
  echo "                          - slim: Minimal installation (default)"
  echo "                          - full: Complete development environment"
  echo
  echo "Examples:"
  echo "  $0                      # Run slim setup in ubuntu container"
  echo "  $0 -d arch              # Run slim setup in Arch container"
  echo "  $0 -d fedora            # Run slim setup in fedora container"
  echo "  $0 -d fedora -t server  # Run server setup in fedora container"
  echo "  $0 -d ubuntu -t full    # Run full setup in ubuntu container"
  echo
  exit 1
}

while [ "$1" != "" ]; do
  case $1 in
  -h | --help)
    usage
    ;;
  --distro=*)
    distro="${1#*=}"
    ;;
  -d)
    shift
    distro="$1"
    ;;
    --tags=*)
      profile="${1#*=}"
      ;;
    -t)
      shift
      profile="$1"
      ;;
  *)
    echo "Invalid option: $1"
    exit 1
    ;;
  esac
  shift
done

# Validate profile
if [ "$profile" != "server" ] && [ "$profile" != "slim" ] && [ "$profile" != "full" ]; then
  echo "Invalid profile: $profile"
  echo "Profiles must be one of: server, slim, full"
  exit 1
fi

# Validate distro
if [ "$distro" == "" ]; then
  printf "Please provide a distro argument. Use 'arch', 'fedora', or 'ubuntu'.\n"
  exit 1
fi

if [ "$distro" == "arch" ] || [ "$distro" == "ubuntu" ] || [ "$distro" == "fedora" ]; then
  docker compose -f "$COMPOSE_FILE" up -d "dotfiles-$distro" &&
    docker compose -f "$COMPOSE_FILE" exec "dotfiles-$distro" bash -lc "bash /home/devuser/code/dotfiles/setup.sh --$profile && exec bash"
else
  printf "Invalid distro: %s. Please use 'arch', 'fedora', or 'ubuntu'.\n" "$distro"
  exit 1
fi
