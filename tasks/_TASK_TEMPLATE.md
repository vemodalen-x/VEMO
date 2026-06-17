---
# ── Machine-readable state (hooks & CI parse THIS; keep it accurate) ──
id: T-YYYYMMDD-xxx
risk: R1                       # R0 | R1 | R2  (lowest that fits)
state: PlanCreated             # PlanCreated|ReviewApproved|ImplementationDone|AcceptancePassed|ProcedureCompleted|Archived
scope_in: []                   # globs the hook allows edits within, e.g. ["src/fusion/**","tests/fusion/**"]
scope_out: []                  # explicitly excluded (documentation)
acceptance:
  status: not_run              # not_run|passed|partial|failed|not_applicable
  build_exit: null
  smoke_exit: null
  evidence: ""                 # path under .vemo/run/
judge:
  required: false              # set by risk tier + capability.tier
  verdict: null                # pass|fail (written by agents/governance-judge.md)
owning_chat: ""                # chat-YYYYMMDD-HHMM-xxx
heartbeat: ""                  # ISO-8601, updated on every state write
---

# <Task title>

## Goal
One sentence: what done looks like.

## Scope (In / Out)
- In: <the files/areas this task may touch — mirror `scope_in` above>
- Out: <explicitly not this task>

## Pass/Fail Criteria  (EARS-style, measurable, falsifiable, attributed)
- [Correctness] WHEN <trigger>, the system SHALL <observable> — metric/threshold: <...>
- [Build] `<build cmd>` SHALL exit 0.
- [Performance] <metric> SHALL be <threshold>.

## Plan
Approach in 2–5 bullets. (R0: this can be a single inline sentence.)

## Execution Log
- <ts> <what happened, commands, exit codes, evidence path>

## Acceptance Result
Per-criterion PASS/FAIL + evidence. Any FAIL → disposition (RCA-inline|RCA-subtask|Criterion-revision|Known-limitation) + user approval where required.

## Conclusion
Outcome: accepted|partial|rejected · Decision: continue|stop|rollback · Key Evidence: <...> · Risk: low|med|high · Next Action: <...>
