#!/usr/bin/env bash
# VEMO Stop hook — surfaces an unfinished gate when a session tries to wrap up.
# Advisory-strong: it does not trap the user, but it loudly records if a code task is being
# left below AcceptancePassed. The hard stop on push is enforced by the CI backstop.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SELF/../.." && pwd)"
export VEMO_ROOT="$ROOT"
mkdir -p "$ROOT/.vemo" 2>/dev/null || true
VALIDATOR="$ROOT/enforcement/validators/task_state.py"
[ -f "$VALIDATOR" ] || exit 0
verdict="$(python3 "$VALIDATOR" gate-check --gate acceptance-before-push 2>/dev/null || echo ok)"
if [ "$verdict" != "ok" ]; then
  echo "[VEMO] reminder: active task is not yet AcceptancePassed ($verdict)." >&2
  printf '%s\n' "{\"ts\":\"$(date -Is)\",\"event\":\"stop_below_acceptance\",\"detail\":\"$verdict\"}" >> "$ROOT/.vemo/telemetry.jsonl" 2>/dev/null || true
fi
exit 0   # Stop hooks advise; the push-time CI gate enforces.
