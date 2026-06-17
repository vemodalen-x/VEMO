#!/usr/bin/env bash
# VEMO SubagentStop hook — captures the governance-judge verdict into telemetry.
# The judge writes its structured verdict to the task front-matter (judge.verdict); this hook
# logs the event so eval/ can measure how often gates ran and what they found.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SELF/../.." && pwd)"
mkdir -p "$ROOT/.vemo" 2>/dev/null || true
printf '%s\n' "{\"ts\":\"$(date -Is)\",\"event\":\"subagent_stop\"}" >> "$ROOT/.vemo/telemetry.jsonl" 2>/dev/null || true
exit 0
