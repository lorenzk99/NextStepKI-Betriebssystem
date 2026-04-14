#!/usr/bin/env bash
# Monatliches Review als Cron-Job.
#
# Beispiel (crontab -e):
#   0 8 1 * *  /pfad/zum/projekt/scripts/monthly-review.sh >> /pfad/logs/review.log 2>&1
#
# Das Skript aktiviert optional ein venv, läuft vom Projekt-Root und
# erzeugt/speichert den Report unter data/feedback/reviews/.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

export PYTHONPATH="${PYTHONPATH:-}:$PROJECT_ROOT/src"

python -m nextstep_os.cli review monthly --tage 30
