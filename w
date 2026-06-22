#!/usr/bin/env bash
# Whisperer local launcher
# Usage: ./w                     (start web UI)
#        ./w <file>              (transcribe)
#        ./w <file> [options]    (transcribe with options)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

PYTHON="${PYTHON:-python}"
if [[ -x "$VENV/bin/python" ]]; then
    PYTHON="$VENV/bin/python"
fi

if [[ $# -eq 0 ]]; then
    exec "$PYTHON" -m whisperer.web
fi

exec "$PYTHON" -m whisperer "$@"
