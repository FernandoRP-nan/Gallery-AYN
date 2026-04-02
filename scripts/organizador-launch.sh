#!/usr/bin/env bash
# Lanza el organizador con Qt WebEngine (mismo criterio que ORGANIZADOR_PREFER_QT=1).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export ORGANIZADOR_PREFER_QT=1
cd "$REPO_ROOT"
exec python3 -m org_multimedia "$@"
