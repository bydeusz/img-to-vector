#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PIPENV_IGNORE_VIRTUALENVS=1

if ! command -v pipenv >/dev/null 2>&1; then
    echo "pipenv is niet gevonden. Installeer het met: pip3 install --user pipenv" >&2
    exit 1
fi

if ! pipenv --venv >/dev/null 2>&1; then
    echo "Eerste keer: omgeving opzetten, dit duurt even..."
    pipenv install
fi

exec pipenv run vectorize "$@"
