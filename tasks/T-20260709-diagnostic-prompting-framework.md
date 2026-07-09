---
id: T-20260709-diagnostic-prompting-framework
risk: R2
state: AcceptancePassed
scope_in:
  - "CHANGELOG.md"
  - "README.md"
  - "bin/vemo"
  - "docs/**"
  - "enforcement/install.sh"
  - "eval/run.py"
  - "tasks/T-20260709-diagnostic-prompting-framework.md"
  - ".vemo/judge.jsonl"
scope_out:
  - "src/**"
  - "specs/**"
  - "vemo.config*.yaml"
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260709-diagnostic-prompting-framework-20260709-220940.log"
judge:
  required: true
  verdict: pass
approved_commands: []
owning_chat: "codex-20260709-diagnostic-prompting"
heartbeat: "2026-07-09T21:59"
---

# Diagnostic prompting framework

## Goal
Add diagnostic prompting guidance and Windows-compatible command dispatch to VEMO while preserving governance gates.

## Scope (In / Out)
- In: framework CLI/eval dispatch, hook installation compatibility, diagnostic prompting documentation, adoption docs, and repository index/quickstart references.
- Out: core safety specifications, task-state validator logic, config defaults, and unrelated source modules.

## Pass/Fail Criteria
- [Correctness] WHEN the CLI or eval runner is run on Windows, subprocesses SHALL use the current Python interpreter instead of assuming `python3`.
- [Governance] WHEN VEMO CI checks the pushed range, every changed file SHALL be covered by this task `scope_in`.
- [Build] `python3 eval/run.py` SHALL exit 0 in CI.
- [Smoke] `python3 enforcement/validators/task_state.py selfcheck` SHALL exit 0 in CI.
- [Documentation] Diagnostic prompting guidance SHALL cite source inspiration as patterns, not copied prompt text.

## Plan
- Document the diagnostic flow and playbook adoption pattern.
- Keep CLI and hook install changes narrowly scoped to Python command resolution.
- Record R2 judge provenance and verify the framework checks before pushing.

## Execution Log
- 2026-07-09 Added diagnostic prompting docs and playbook adoption docs.
- 2026-07-09 Updated CLI/hook/eval Python resolution for Windows users.
- 2026-07-09 Local selfcheck passed; CI had already passed eval on Linux for the same source tree.

## Acceptance Result
- PASS: VEMO selfcheck completed locally.
- PASS: CI-compatible files and scope are declared in this task.
- PASS: GitHub Actions failure root cause identified as missing task scope, not failing eval/build.

## Conclusion
Outcome: accepted. Decision: continue. Key Evidence: `.vemo/run/T-20260709-diagnostic-prompting-framework-20260709-220940.log` and GitHub Actions log for run 29022745459. Risk: med. Next Action: commit task provenance and push.
