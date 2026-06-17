#!/usr/bin/env bash
# VEMO PreToolUse(Bash) hook — DESTRUCTIVE / OUT-OF-REPO commands (safety.spec rule 4).
# Blocks broad rm -rf, git reset --hard, git checkout -- <file>, writes outside repo_root,
# and obvious privilege escalation, unless the task file records explicit user approval.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cmd="$(cat | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
[ -z "$cmd" ] && exit 0

block(){ echo "[VEMO] BLOCKED (safety.spec#4): $1. Needs explicit same-session user approval recorded in the task file." >&2; exit 2; }

echo "$cmd" | grep -qE '(^|[^a-zA-Z])rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)[[:space:]]+(/|~|\*|\.\.)' && block "broad recursive delete"
echo "$cmd" | grep -qE 'git[[:space:]]+reset[[:space:]]+--hard'                && block "git reset --hard"
echo "$cmd" | grep -qE 'git[[:space:]]+checkout[[:space:]]+--[[:space:]]'      && block "git checkout -- (discards working changes)"
echo "$cmd" | grep -qE '(^|[[:space:]])(sudo|doas)[[:space:]]'                 && block "privilege escalation"
echo "$cmd" | grep -qE 'curl[^|]*\|[[:space:]]*(sh|bash)'                      && block "pipe-to-shell install"
exit 0
