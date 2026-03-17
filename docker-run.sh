#!/bin/bash

# Default values for options
distro="ubuntu"
tags="slim"

usage() {
  echo "Docker Development Environment Setup Script"
  echo
  echo "Usage: $0 [-d|--distro <distro>] [-t|--tags <tags>]"
  echo
  echo "Options:"
  echo "  -h, --help              Show this help message"
  echo "  -d, --distro <distro>   Specify distribution (ubuntu|fedora)"
  echo "                          Default: ubuntu"
  echo "  -t, --tags <tags>       Specify installation profile:"
  echo "                          - slim: Minimal installation (default)"
  echo "                          - full: Complete development environment"
  echo
  echo "Examples:"
  echo "  $0                      # Drop into ubuntu container (slim)"
  echo "  $0 -d fedora            # Drop into fedora container (slim)"
  echo "  $0 -d fedora -t full    # Drop into fedora container (full)"
  echo "  $0 -d ubuntu -t slim    # Drop into ubuntu container (slim)"
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
    tags="${1#*=}"
    ;;
  -t)
    shift
    tags="$1"
    ;;
  *)
    echo "Invalid option: $1"
    exit 1
    ;;
  esac
  shift
done

# Validate tags
if [ "$tags" != "slim" ] && [ "$tags" != "full" ]; then
  echo "Invalid tag: $tags"
  echo "Tags must be one of: slim, full"
  exit 1
fi

# Validate distro
if [ "$distro" == "" ]; then
  printf "Please provide a distro argument. Use 'ubuntu' or 'fedora'.\n"
  exit 1
fi

if [ "$distro" == "ubuntu" ] || [ "$distro" == "fedora" ]; then
  docker compose up -d "dotfiles-$distro" &&
    docker compose exec "dotfiles-$distro" bash
else
  printf "Invalid distro: %s. Please use 'ubuntu' or 'fedora'.\n" "$distro"
  exit 1
fi
