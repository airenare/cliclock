#!/usr/bin/env bash
# User-level installer for cliclock (no root needed for the default prefix).
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<USAGE
Usage: install.sh [--prefix DIR] [--uninstall] [-h|--help]

Installs cliclock under a prefix:
  <prefix>/bin/cliclock
  <prefix>/lib/cliclock/cliclock/*.py

Options:
  --prefix DIR   install prefix (default: \$HOME/.local; /usr/local when run
                 via sudo or as root, i.e. \`sudo ./install.sh\`)
  --uninstall    remove <prefix>/bin/cliclock and <prefix>/lib/cliclock
  -h, --help     show this help

Your config (~/.config/cliclock) is never read or modified.
USAGE
}

prefix=""
uninstall=0
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix)
            [ $# -ge 2 ] || { echo "install.sh: --prefix needs a directory" >&2; usage >&2; exit 2; }
            prefix="$2"; shift 2 ;;
        --prefix=*) prefix="${1#--prefix=}"; shift ;;
        --uninstall) uninstall=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "install.sh: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "$prefix" ]; then
    if [ -n "${SUDO_USER:-}" ] || [ "$EUID" -eq 0 ]; then
        prefix=/usr/local
    else
        prefix="$HOME/.local"
    fi
fi

# Guard against empty or root-like prefixes.
case "$prefix" in
    ""|/|.|..|//*) echo "install.sh: refusing unsafe prefix '$prefix'" >&2; exit 2 ;;
esac
mkdir -p "$prefix"
prefix="$(cd "$prefix" && pwd -P)"
if [ "$prefix" = "/" ]; then
    echo "install.sh: refusing prefix '/'" >&2; exit 2
fi

bin_path="$prefix/bin/cliclock"
lib_path="$prefix/lib/cliclock"

if [ "$uninstall" -eq 1 ]; then
    removed=0
    if [ -e "$bin_path" ] || [ -L "$bin_path" ]; then
        rm -f -- "$bin_path"; echo "removed $bin_path"; removed=1
    fi
    if [ -d "$lib_path" ]; then
        rm -rf -- "$lib_path"; echo "removed $lib_path"; removed=1
    fi
    [ "$removed" -eq 1 ] || echo "nothing to remove under $prefix"
    exit 0
fi

# Preflight.
if ! command -v python3 >/dev/null 2>&1; then
    echo "install.sh: python3 not found (install it with: sudo pacman -S python)" >&2
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    echo "install.sh: Python >= 3.11 required (tomllib); found $(python3 -V 2>&1)" >&2
    exit 1
fi
if [ ! -w "$prefix" ]; then
    echo "install.sh: prefix $prefix is not writable (try --prefix DIR or sudo)" >&2
    exit 1
fi

# Replace any previous install cleanly (also drops a stale bin symlink).
rm -rf -- "$lib_path"
rm -f -- "$bin_path"
mkdir -p "$lib_path/cliclock" "$prefix/bin"

for f in "$SRC"/cliclock/*.py; do
    install -m 0644 "$f" "$lib_path/cliclock/"
done
install -m 0755 "$SRC/packaging/cliclock" "$bin_path"

echo "Installed files:"
(find "$lib_path" -type f; echo "$bin_path") | sort

# Verify without leaving bytecode behind in the install tree.
if ! PYTHONDONTWRITEBYTECODE=1 "$bin_path" --version; then
    echo "install.sh: verification failed: '$bin_path --version' returned non-zero" >&2
    exit 1
fi

case ":$PATH:" in
    *":$prefix/bin:"*) ;;
    *)
        echo "warning: $prefix/bin is not in your PATH. Add this to your shell profile:" >&2
        echo "  export PATH=\"$prefix/bin:\$PATH\"" >&2 ;;
esac
