#!/usr/bin/env bash
# VEMO PreToolUse(Edit/Write) hook — SECRETS (safety.spec rule 5).
# Blocks writing obvious credentials into a file. Best-effort; CI re-scans the staged diff.
set -euo pipefail
content="$(cat | python3 -c 'import sys,json;ti=json.load(sys.stdin).get("tool_input",{});print(ti.get("content") or ti.get("new_string") or "")' 2>/dev/null || true)"
if printf '%s' "$content" | grep -iqE '(api[_-]?key|secret|password|token)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/_+\-]{16,}|BEGIN (RSA|OPENSSH) PRIVATE KEY'; then
  echo "[VEMO] BLOCKED (safety.spec#5): the content looks like a credential/secret. Use an env var or a secrets manager, not a committed file." >&2
  exit 2
fi
exit 0
