#!/usr/bin/env bash
# VEMO enforcement installer — wires the mechanical layer into a consuming repo. Idempotent:
# re-running dedupes hook registrations and migrates away any legacy guard-*.sh entries.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
echo "[VEMO] installing enforcement into $ROOT"

# 1) Claude Code hooks → merge enforcement/hooks/hooks.json into .claude/settings.json (dedup by command)
mkdir -p .claude .vemo
if command -v python3 >/dev/null 2>&1; then
  python3 - "$ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
settings = os.path.join(root, ".claude", "settings.json")
src = os.path.join(root, "enforcement", "hooks", "hooks.json")
cur = {}
if os.path.exists(settings):
    try:
        cur = json.load(open(settings))
    except ValueError:
        cur = {}
add = json.load(open(src)).get("hooks", {})
cur.setdefault("hooks", {})


def sig(entry):
    return json.dumps(entry, sort_keys=True)


def is_legacy(entry):
    return any("guard-" in (h.get("command") or "") or "check-acceptance" in (h.get("command") or "")
               or "record-judge" in (h.get("command") or "") for h in entry.get("hooks", []))


for ev, lst in add.items():
    kept = [e for e in cur["hooks"].get(ev, []) if not is_legacy(e)]   # migrate off deleted .sh guards
    seen = {sig(e) for e in kept}
    for e in lst:
        if sig(e) not in seen:
            kept.append(e); seen.add(sig(e))
    cur["hooks"][ev] = kept
json.dump(cur, open(settings, "w"), indent=2)
print("  ✓ hooks registered in .claude/settings.json (deduped; legacy .sh entries migrated)")
PY
else
  echo "  ! python3 not found — hooks NOT registered. python3 is REQUIRED for client-side guards;"
  echo "    the git/CI backstop below still applies, but install python3 for in-loop enforcement."
fi

# 2) git backstops: pre-commit (plan/scope/tier/judge/secret) + pre-push (acceptance + required judge provenance)
mkdir -p .git/hooks
cp enforcement/ci/pre-commit .git/hooks/pre-commit
cp enforcement/ci/pre-push  .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
echo "  ✓ git pre-commit + pre-push backstops installed"

# 3) make scripts executable
chmod +x enforcement/hooks/run.py enforcement/validators/*.py enforcement/automation/vemo-auto 2>/dev/null || true

# 4) telemetry sink
touch .vemo/telemetry.jsonl

# 5) server-side authority — local hooks can be bypassed (--no-verify); CI cannot.
if [ ! -e .github/workflows/vemo-ci.yml ]; then
  echo "  ! no CI workflow found. The AUTHORITATIVE layer is server-side:"
  echo "      mkdir -p .github/workflows && cp enforcement/ci/vemo-ci.yml .github/workflows/vemo-ci.yml"
  echo "    then protect your main branch so the 'vemo' check is required."
fi
echo "[VEMO] done. Verify with: python3 enforcement/validators/task_state.py selfcheck"
