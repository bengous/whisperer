#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON:-}" && -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="${PYTHON:-python}"
fi

"$PYTHON" -m compileall -q whisperer tests
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m whisperer --help >/dev/null
"$PYTHON" -m whisperer.web --help >/dev/null
