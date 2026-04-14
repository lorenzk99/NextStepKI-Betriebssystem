#!/usr/bin/env bash
# Installiert einen einfachen pre-commit-Hook, der pytest vor jedem Commit ausführt.
# Alternative zu `pre-commit install` (siehe .pre-commit-config.yaml).
#
# Nutzung:
#   bash scripts/install-git-hooks.sh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
HOOK="$ROOT/.git/hooks/pre-commit"

cat >"$HOOK" <<'EOF'
#!/usr/bin/env bash
# Auto-generiert durch scripts/install-git-hooks.sh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "▶ pytest (pre-commit)..."
PYTHONPATH=src python -m pytest tests/ -q
EOF

chmod +x "$HOOK"
echo "✅ pre-commit-Hook installiert: $HOOK"
