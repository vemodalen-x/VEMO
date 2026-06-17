#!/usr/bin/env bash
# VEMO PreToolUse hook — SCOPE CONTAINMENT (safety.spec rule 1)
# Blocks any Edit/Write whose target path is outside the active task's scope_in globs.
# Contract: receives the tool call as JSON on stdin; exit 2 = block (stderr shown to agent).
#
# This is the rule Wildpanda could only *ask* for (Z-03). Here it is mechanically enforced.
set -euo pipefail
# Resolve repo root from THIS script's location (enforcement/hooks/ -> repo root), not via git.
# This keeps the guard correct even when VEMO is nested inside another git repo.
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SELF/../.." && pwd)"
export VEMO_ROOT="$ROOT"
VALIDATOR="$ROOT/enforcement/validators/task_state.py"
mkdir -p "$ROOT/.vemo" 2>/dev/null || true
log(){ printf '%s\n' "{\"ts\":\"$(date -Is)\",\"event\":\"$1\",\"target\":\"${2:-}\"}" >> "$ROOT/.vemo/telemetry.jsonl" 2>/dev/null || true; }

payload="$(cat)"
target="$(printf '%s' "$payload" | python3 -c 'import sys,json;d=json.load(sys.stdin);ti=d.get("tool_input",{});print(ti.get("file_path") or ti.get("path") or "")' 2>/dev/null || true)"
[ -z "$target" ] && exit 0   # nothing to check

if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$VALIDATOR" ]; then
  # v1.1: scope is safety-critical → FAIL CLOSED unless the project explicitly opts into fail-open.
  log scope_guard_degraded "$target"
  if grep -qiE 'degrade_gracefully:[[:space:]]*true' "$ROOT/vemo.config.yaml" 2>/dev/null; then
    echo "[VEMO] scope guard degraded (validator unavailable) — degrade_gracefully=true, allowing + logging." >&2
    exit 0
  fi
  echo "[VEMO] BLOCKED (fail-closed): scope guard cannot verify '$target' (python3/validator unavailable). Install python3, or set enforcement.degrade_gracefully: true to opt into fail-open." >&2
  exit 2
fi

verdict="$(python3 "$VALIDATOR" scope-check --path "$target" 2>/dev/null || echo "no-active-task")"
case "$verdict" in
  in-scope)      exit 0 ;;
  no-active-task)
    log scope_block_no_task "$target"
    echo "[VEMO] BLOCKED (safety.spec#1): no active task declares a Scope (In). Create/continue a task (tasks/_TASK_TEMPLATE.md) first, then edit." >&2
    exit 2 ;;
  out-of-scope)
    log scope_block_out "$target"
    echo "[VEMO] BLOCKED (safety.spec#1): '$target' is outside the active task's scope_in. If it truly belongs to this task, add it via a replan; otherwise it is a different task. Do not edit unrelated files." >&2
    exit 2 ;;
  *) exit 0 ;;
esac
