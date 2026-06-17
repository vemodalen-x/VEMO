#!/usr/bin/env bash
# VEMO PreToolUse(all tools) hook — RUN BUDGET / STOP RULES (v1.3, from the Fable 5 analysis).
# Mythos-class models "run until the harness cuts them off." This counts tool calls / files / wall-clock
# per run and stops a runaway. Enforcement is asymmetric by who is watching:
#   * AUTO MODE ON (unattended) -> HARD stop (exit 2): no human is there to catch a runaway.
#   * human present (interactive) -> ADVISORY (warn, exit 0): the human is the stop rule.
# Counters: .vemo/run.json (reset by `vemo-auto on` or `task_state.py budget-reset`). Limits: vemo.config.yaml.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SELF/../.." && pwd)"
export VEMO_ROOT="$ROOT"
V="python3 $ROOT/enforcement/validators/task_state.py"
command -v python3 >/dev/null 2>&1 || exit 0   # without python we cannot count; other guards still apply

payload="$(cat)"
target="$(printf '%s' "$payload" | python3 -c 'import sys,json;ti=json.load(sys.stdin).get("tool_input",{});print(ti.get("file_path") or ti.get("path") or "")' 2>/dev/null || true)"
verdict="$($V budget-tick ${target:+--path "$target"} 2>/dev/null || echo ok)"

case "$verdict" in
  ok|"" ) exit 0 ;;
  stop:* )
    if $V auto-status 2>/dev/null | grep -q '^on'; then
      echo "[VEMO] STOP RULE (unattended auto mode): run budget exceeded — $verdict. Autonomous run halted." >&2
      echo "       A human checkpoint is required. Reset with: python3 enforcement/validators/task_state.py budget-reset" >&2
      exit 2
    fi
    echo "[VEMO] run budget exceeded — $verdict (advisory: a human is present, not blocking). Consider a checkpoint or budget-reset." >&2
    exit 0 ;;
  * ) exit 0 ;;
esac
