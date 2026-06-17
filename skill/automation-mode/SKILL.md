---
name: automation-mode
description: Enable or disable VEMO full-auto (unattended) mode. Auto mode stops pausing for user approval and records every decision instead, while keeping all mechanical safety guards and the independent judge. OFF by default; only this explicit command turns it on. Bounded by a risk ceiling and a TTL.
---

# Automation Mode (full-auto / unattended)

Turn VEMO's human-approval pauses into **auto-decide + record**, for trusted batch/overnight/CI work.
This is the **separate explicit command** required to enter auto mode — it never turns on by itself.

## Trigger / 触发条件
- **Manual only / 仅手动** — there is no automatic trigger by design.
- **Enable keywords**: "启用全自动模式" / "开启自动模式" / "enable auto mode" / "vemo auto on" / "full auto on"
- **Disable keywords**: "关闭自动模式" / "退出全自动" / "disable auto mode" / "vemo auto off"
- **Status keywords**: "自动模式状态" / "auto mode status"

## What it does (and does NOT do)
- **Removes**: the user-approval pauses (R2 plan review, push confirmation, subtask review, failure-disposition
  approval, stale-task takeover, comment review) → the agent decides, records a one-line rationale, and proceeds.
- **Keeps (never relaxed)**: all `specs/safety.spec.md` mechanical guards (scope / destructive / secret /
  out-of-repo), risk-tier integrity (no self-downgrade), `acceptance-before-push`, and the independent
  `agents/governance-judge.md` — which becomes **mandatory** on every auto-approved R1+/R2 (the judge replaces
  the absent human reviewer; a `fail` still blocks).

## How to invoke
```bash
# enable (default ceiling R1, TTL 8h):
python3 enforcement/automation/vemo-auto on
# raise ceiling / change TTL:
python3 enforcement/automation/vemo-auto on --max-tier R1 --ttl 4
# allow critical R2 auto-approval (explicit, recorded high-trust grant):
python3 enforcement/automation/vemo-auto on --max-tier R2 --allow-r2
# status / disable:
python3 enforcement/automation/vemo-auto status
python3 enforcement/automation/vemo-auto off
```

## Behavior contract (the agent follows this when auto is ON)
1. At session start, run `python3 enforcement/validators/task_state.py auto-status`. If ON, load
   `specs/automation.spec.md` and obey it.
2. For each request, compute the risk tier. If `tier <= max_auto_tier`, do **not** ask the user at any
   approval gate — instead record the decision to `.vemo/auto_decisions.jsonl` and the task file's
   `## Auto-Mode Decisions` block, then continue.
3. If `tier > max_auto_tier` (e.g. R2 without `--allow-r2`), fall back to normal human-in-the-loop behavior.
4. Never skip a mechanical guard or the judge. If a guard blocks, auto mode does not override it.

## Safety
- OFF by default; explicit command required; **expires** (TTL, default 8h); easy kill switch (`off`).
- Enabling is recorded (who/when/ceiling/expiry). Destructive commands stay blocked unless explicitly
  pre-authorized in `auto_mode.preauthorized_commands`.
- Intent: a velocity tool for trusted, bounded work — trust shifts to mechanism + judge + audit trail,
  not to "no one is watching".
