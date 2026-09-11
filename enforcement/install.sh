#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$ROOT/.git/hooks" "$ROOT/.github/workflows" "$ROOT/.vemo/evidence"
cp "$ROOT/enforcement/ci/pre-commit" "$ROOT/.git/hooks/pre-commit"
cp "$ROOT/enforcement/ci/pre-push" "$ROOT/.git/hooks/pre-push"
cp "$ROOT/enforcement/ci/vemo-ci.yml" "$ROOT/.github/workflows/vemo-ci.yml"
chmod +x "$ROOT/.git/hooks/pre-commit" "$ROOT/.git/hooks/pre-push" "$ROOT/bin/vemo" "$ROOT/enforcement/hooks/run.py"
python3 - "$ROOT" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
source = json.loads((root / "enforcement/hooks/hooks.json").read_text())
target = root / ".claude/settings.json"
value = json.loads(target.read_text()) if target.exists() else {}
hooks = value.setdefault("hooks", {})
for event, entries in source["hooks"].items():
    current = hooks.setdefault(event, [])
    current[:] = [row for row in current if "enforcement/hooks/run.py" not in json.dumps(row)]
    current.extend(entries)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
PY
echo "VEMO core installed: policy, task, gate, verify, evidence"
