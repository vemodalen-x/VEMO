---
id: T-20260716-product-report-naive-timestamps
risk: R1
state: AcceptancePassed
scope_in:
  - "bin/vemo_product.py"
  - "tasks/T-20260716-product-report-naive-timestamps.md"
  - ".vemo/run/T-20260716-product-report-naive-timestamps*.log"
  - ".vemo/run/receipt.json"
scope_out:
  - "README.md"
  - "enforcement/**"
  - "eval/run.py"
  - "vemo.config.yaml"
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 bin/vemo_product.py report --json"
    lint: "python3 -m py_compile bin/vemo_product.py"
    smoke: "python3 eval/run.py"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260716-product-report-naive-timestamps-20260716T092636Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: chat-20260716-ci-fix
heartbeat: 2026-07-16T09:26:06Z
---

# Fix product report parsing of legacy telemetry timestamps

## Goal
Make `vemo report --json` tolerate existing local telemetry rows whose timestamps have no timezone suffix, so
post-merge verification does not fail on older machine-local data.

## Scope (In / Out)
- In: `bin/vemo_product.py` and this task record.
- Out: README, governance hook changes, eval scenario additions, and unrelated local security-hardening work.

## Pass/Fail Criteria
- [Correctness] WHEN `.vemo/telemetry.jsonl` contains a timestamp without timezone info, `python3 bin/vemo_product.py report --json` SHALL exit 0 and emit valid local-only JSON.
- [Regression] WHEN product report parsing handles UTC-aware timestamps ending in `Z`, existing behavior SHALL remain unchanged.
- [Build] `python3 -m py_compile bin/vemo_product.py` SHALL exit 0.
- [Build] `python3 eval/run.py` SHALL exit 0.

## Plan
- Normalize naive telemetry timestamps to UTC in `_stamp()`.
- Re-run product report, py_compile, selfcheck, and the full conformance eval.

## Execution Log
- 2026-07-16T09:26:06Z PlanCreated after GitHub Actions run 29485559859 showed the merged PR check red; local diagnosis found `vemo_product.py report --json` failed on naive local telemetry timestamps.
- 2026-07-16T09:26:36Z `verify-run --all-tasks --no-cache` passed focused profile: product report, py_compile, and eval 169/169.

## Acceptance Result
- [Correctness] Product report exits 0 and emits valid local-only JSON against current telemetry, including legacy naive timestamps — PASS.
- [Regression] UTC-aware timestamp parsing is unchanged by the normalization path — PASS by focused product report/eval coverage.
- [Build] `python3 -m py_compile bin/vemo_product.py` exit 0 — PASS.
- [Build] `python3 eval/run.py` exit 0 — PASS (169/169).

## Conclusion
Outcome: accepted · Decision: continue · Key Evidence: `.vemo/run/T-20260716-product-report-naive-timestamps-20260716T092636Z.log`, `.vemo/run/receipt.json` · Risk: low · Next Action: commit and push the CI follow-up.
