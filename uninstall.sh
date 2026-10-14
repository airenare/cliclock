#!/usr/bin/env bash
# Thin wrapper: same prefix rules as install.sh (sudo => /usr/local).
set -euo pipefail
exec "$(dirname "$0")/install.sh" --uninstall "$@"
