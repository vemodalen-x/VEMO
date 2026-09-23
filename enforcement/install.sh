#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
[ -d "$ROOT/.git" ] && [ ! -L "$ROOT/.git" ] || {
  echo "VEMO lightweight init requires a repository with its own .git directory" >&2
  exit 2
}
HOOKS_PATH="$(git -C "$ROOT" config --get core.hooksPath || true)"
[ -z "$HOOKS_PATH" ] || { echo "VEMO refuses custom core.hooksPath: $HOOKS_PATH" >&2; exit 2; }
for path in \
  "$ROOT/.git" \
  "$ROOT/.git/hooks" \
  "$ROOT/.github" \
  "$ROOT/.github/workflows" \
  "$ROOT/.vemo" \
  "$ROOT/.vemo/evidence" \
  "$ROOT/.claude" \
  "$ROOT/.claude/settings.json" \
  "$ROOT/bin" \
  "$ROOT/bin/vemo" \
  "$ROOT/enforcement" \
  "$ROOT/enforcement/ci" \
  "$ROOT/enforcement/hooks" \
  "$ROOT/enforcement/hooks/hooks.json" \
  "$ROOT/enforcement/hooks/run.py"
do
  [ ! -L "$path" ] || { echo "VEMO refuses symlinked managed path: ${path#"$ROOT"/}" >&2; exit 2; }
done
check_managed() {
  source="$1"
  target="$2"
  if [ -L "$target" ]; then
    echo "VEMO refuses symlinked managed file: ${target#"$ROOT"/}" >&2
    exit 2
  fi
  if [ -e "$target" ] && ! cmp -s "$source" "$target"; then
    echo "VEMO refuses to overwrite existing file: ${target#"$ROOT"/}" >&2
    exit 2
  fi
}
check_managed "$ROOT/enforcement/ci/pre-commit" "$ROOT/.git/hooks/pre-commit"
check_managed "$ROOT/enforcement/ci/pre-push" "$ROOT/.git/hooks/pre-push"
check_managed "$ROOT/enforcement/ci/vemo-ci.yml" "$ROOT/.github/workflows/vemo-ci.yml"
python3 - "$ROOT" <<'PY'
import json, os, pathlib, sys, tempfile
root = pathlib.Path(sys.argv[1])
source = json.loads((root / "enforcement/hooks/hooks.json").read_text())
target = root / ".claude/settings.json"
value = json.loads(target.read_text()) if target.exists() else {}
if not isinstance(value, dict) or not isinstance(value.get("hooks", {}), dict):
    raise SystemExit("VEMO refuses invalid .claude/settings.json")
if not isinstance(source, dict) or not isinstance(source.get("hooks"), dict):
    raise SystemExit("VEMO hook source is invalid")
hooks = value.get("hooks", {})
for event, entries in source["hooks"].items():
    if not isinstance(entries, list) or not isinstance(hooks.get(event, []), list):
        raise SystemExit("VEMO refuses incompatible Claude hook settings")
PY
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
descriptor, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
echo "VEMO core installed: policy, task, gate, verify, evidence"
