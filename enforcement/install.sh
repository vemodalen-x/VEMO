#!/usr/bin/env bash
# VEMO enforcement installer — wires the mechanical layer into a consuming repo.
# Portable (bash); no PowerShell dependency. Idempotent.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
echo "[VEMO] installing enforcement into $ROOT"

# 1) Claude Code hooks → merge enforcement/hooks/hooks.json into .claude/settings.json
mkdir -p .claude .vemo
if command -v python3 >/dev/null 2>&1; then
  python3 - "$ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
settings = os.path.join(root, ".claude", "settings.json")
src = os.path.join(root, "enforcement", "hooks", "hooks.json")
cur = {}
if os.path.exists(settings):
    cur = json.load(open(settings))
add = json.load(open(src)).get("hooks", {})
cur.setdefault("hooks", {})
for ev, lst in add.items():
    cur["hooks"].setdefault(ev, [])
    cur["hooks"][ev].extend(lst)
json.dump(cur, open(settings, "w"), indent=2)
print("  ✓ hooks registered in .claude/settings.json")
PY
else
  echo "  ! python3 not found — hooks NOT registered (degrade: CI backstop still applies)"
fi

# 2) git pre-commit backstop
mkdir -p .git/hooks
cp enforcement/ci/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "  ✓ git pre-commit backstop installed"

# 3) make scripts executable
chmod +x enforcement/hooks/*.sh enforcement/validators/*.py 2>/dev/null || true

# 4) telemetry sink
touch .vemo/telemetry.jsonl
echo "[VEMO] done. CI should also run: bash enforcement/ci/pre-commit (server-side authority)."
