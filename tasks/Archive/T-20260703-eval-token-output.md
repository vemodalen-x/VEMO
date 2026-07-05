---
id: T-20260703-eval-token-output
risk: R1
state: Archived
scope_in: ["eval/run.py", "tasks/T-20260703-eval-token-output.md"]
scope_out: ["enforcement/**", "specs/**", "vemo.config.yaml", ".github/**"]
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260703-eval-token-output-20260703-151911.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: chat-20260703-1514-cdx
heartbeat: 2026-07-03T15:20
---

# T-20260703-eval-token-output - eval runner token-output optimization

## Goal
Reduce agent-facing token noise from `python3 eval/run.py` while preserving the full default conformance run.

## Scope
- In: `eval/run.py`, this task file.
- Out: validator semantics, hook semantics, safety specs, CI workflows, release gating rules.

## Pass/Fail Criteria
- [Correctness] WHEN `python3 eval/run.py` runs with no flags, it SHALL execute the full conformance suite and exit 0.
- [TokenOutput] WHEN `python3 eval/run.py` runs with no flags, stdout SHALL use compact summary output instead of listing every passing check.
- [Debuggability] WHEN `python3 eval/run.py --verbose` runs, stdout SHALL include per-check PASS/FAIL lines.
- [Debuggability] WHEN `python3 eval/run.py --failures-only --match impossible` runs, stdout SHALL produce a compact no-checks-selected summary and exit nonzero.
- [Selectivity] WHEN `python3 eval/run.py --group hook --match destructive` runs, only matching selected checks SHALL be counted in the report.

## Plan
1. Add CLI flags to `eval/run.py` for compact/verbose reporting and check selection.
2. Keep default behavior semantically equivalent: all checks still run unless filtered by explicit flags.
3. Run full eval plus targeted selector smoke tests.
4. Commit and push only the scoped files.

## Read Audit
- `eval/run.py`: whole_file, purpose=implementation target, read_trigger_outcome=comment_added_for_new_helpers.
- `enforcement/hooks/run.py`: lines 1-280, purpose=understand hook e2e behavior, read_trigger_outcome=not_in_comment_scope.
- `enforcement/validators/task_state.py`: lines 1-320, purpose=understand validator command behavior, read_trigger_outcome=not_in_comment_scope.

## Execution Log
- 2026-07-03T15:14 Plan created from user request to implement the token optimization and commit/push.
- 2026-07-03T15:18 Implemented compact default reporting, `--verbose`, `--failures-only`, `--fail-fast`,
  `--list`, `--group`, and `--match` in `eval/run.py`. Default execution still selects all 60 checks.
- 2026-07-03T15:19 Acceptance passed via `task_state.py verify-run`: build `python3 eval/run.py` exit 0,
  smoke `python3 enforcement/validators/task_state.py selfcheck` exit 0, receipt `.vemo/run/receipt.json`.

## Acceptance Result
- [Correctness] `python3 eval/run.py` with no flags executed the full suite: PASS, 60/60, exit 0.
- [TokenOutput] Default stdout is compact summary only: PASS.
- [Debuggability] `python3 eval/run.py --verbose --group auto` printed a per-check PASS line: PASS.
- [Debuggability] `python3 eval/run.py --failures-only --match impossible` produced no-checks-selected and exit 1: PASS.
- [Selectivity] `python3 eval/run.py --group hook --match destructive` counted only 2 selected checks: PASS.

## Conclusion
Outcome: accepted
Decision: continue
Key Evidence: `.vemo/run/T-20260703-eval-token-output-20260703-151911.log`, `.vemo/run/receipt.json`, `eval/out/report.json`
Risk: low
Next Action: commit and push.
