---
id: T-20260711-governance-cost-proportionality
risk: R2
change_class: security
state: AcceptancePassed
scope_in: ["enforcement/validators/task_state.py", "enforcement/automation/vemo-auto", "enforcement/hooks/run.py", "enforcement/ci/pre-commit", "enforcement/ci/pre-push", "vemo.config.yaml", "specs/task.spec.md", "specs/verify.spec.md", "specs/concurrency.spec.md", "agents/governance-judge.md", "bin/vemo", "eval/run.py", "tasks/_TASK_TEMPLATE.md", "tasks/T-20260711-governance-cost-proportionality.md", "README.md", "CHANGELOG.md", ".vemo/judge.jsonl", ".vemo/run/T-20260711-governance-cost-proportionality*.log", ".vemo/run/receipt.json", ".vemo/run/cache.json"]
scope_out: [".github/**", "bin/vemo_fleet.py", "profiles/**", "tests/test_fleet.py", "../VEMO_SKILLS/**", "../photo_archive*", "../m3u8_*"]
trifecta: []
verification:
  profile: full
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260711-governance-cost-proportionality-20260712T074157Z.log"
judge:
  required: true
  verdict: pass
  evidence_checked: [".vemo/run/T-20260711-governance-cost-proportionality-20260712T031721Z.log", "eval/out/report.json", "staged diff"]
  confidence: high
approved_commands: []
owning_chat: "chat-20260711-cost"
heartbeat: 2026-07-12T07:42:51Z
---

# Governance Cost Proportionality

## Goal
Make VEMO ceremony proportional to semantic blast radius while preserving fail-closed protection for gates, permissions, releases, and security mechanisms.

## Scope (In / Out)
- In: semantic risk classification, staged/range-isolated judge dossiers, layered verification profiles, change-class-aware judge depth, tool-written UTC task timestamps, scoped verification caching, specs, CLI, and conformance tests.
- Out: changing GitHub workflow contents, weakening secret/destructive/scope gates, business application code, automatic approval, and release tagging.

## Pass/Fail Criteria
- [Safety] WHEN a workflow diff only adds Python or dependency initialization and changes no gate command, trigger, permission, release, deploy, or attestation logic, tier classification SHALL return R1; WHEN those protected semantics change, it SHALL return R2.
- [Isolation] WHEN unrelated untracked files from another task exist, the default judge dossier SHALL list only the staged diff or explicit CI range; metric: an end-to-end Git fixture excludes the unrelated path.
- [Correctness] WHEN an R1 task selects `focused`, verification SHALL execute exactly task-local `test`, `lint`, and one `smoke`; WHEN `release` is selected, it SHALL include configured full build, smoke, and package scan.
- [Correctness] WHEN change class is `ci-narrow`, an R2 task SHALL require one Judge; security, release, and permissions classes SHALL retain capability-tier full depth (two at tier=high).
- [Correctness] WHEN task lifecycle, note, judge, receipt, budget, or heartbeat timestamps are written, the tool SHALL emit UTC RFC3339 values ending in `Z`; task templates SHALL direct agents to tools instead of hand entry.
- [Performance] WHEN scoped inputs and verification commands are unchanged after a successful run, `vemo verify` SHALL reuse the cached result; an in-scope content change SHALL invalidate it while unrelated untracked files SHALL not.
- [Compatibility] Existing tasks without new semantic/verification fields SHALL retain conservative R2 path behavior and legacy global build/smoke verification.
- [Build] `python eval/run.py` and `python bin/vemo selfcheck` SHALL exit 0 with all conformance checks passing.

## Plan
- Add conservative semantic diff classification and validate declared change classes at the Git backstop.
- Add layered command selection, scope fingerprints, successful-result cache reuse, and receipt freshness checks.
- Restrict judge dossiers to staged/range changes and derive Judge depth from validated change class.
- Add UTC task create/note/state/heartbeat commands, migrate internal writers, update specs/templates/CLI, and extend adversarial eval coverage.

## Execution Log
- 2026-07-11T12:54:28Z Implemented semantic workflow risk, staged/range Judge isolation, verification profiles/cache, change-class Judge depth, and UTC tool timestamps; targeted conformance passed.
- 2026-07-11T12:56:03Z Full verification first run failed with exit 9009 because Windows lacked python3; adapted verify runtime to use the current interpreter only when python3 is unavailable.
- 2026-07-12T02:36:45Z Independent correctness and safety Judges failed the staged snapshot: command chaining, release upload classification, shell/working-directory allowlisting, deleted-workflow semantics, and invalid-range fail-closed coverage require rework.
- 2026-07-12T02:38:43Z Closed both Judge failure sets and added five adversarial checks: chained commands, shell/workdir changes, release uploads, deleted permission workflows, and invalid range fail-closed.
- 2026-07-12T02:39:45Z Post-Judge full run found git-less dossier regression (100/101); narrowed fail-closed behavior to explicit ranges and retained default staged degradation.
- 2026-07-12T02:50:47Z Closed second Judge failure set: all shell control tokens rejected for ci-init, explicit ranges validated, critical class ordering enforced, and release class now requires release verification profile; targeted validator and Git backstop tests passed.
- 2026-07-12T03:02:49Z Closed process-substitution bypass by rejecting shell expansion/redirection tokens; added task-scoped Judge snapshot binding so rework invalidates passes without coupling sibling tasks. Git conformance 4/4 passed.
- 2026-07-12T03:05:34Z Closed process-substitution bypass and bound Judge provenance to task-scoped snapshots; normalized only the mirrored judge cache. Multi-task range and post-verdict-mirror Git tests pass 4/4.
- 2026-07-12T03:16:12Z Closed rename-out and template snapshot bypasses: Git risk inputs use --no-renames, removed workflows classify security, and only the active task verdict cache is normalized. Git conformance 5/5 passed.
- 2026-07-12T03:17:21Z Full run 104/105 exposed an obsolete test expectation: deleted workflows now intentionally classify security rather than permissions; updated expectation with judge depth still 2.
- 2026-07-12T07:41:46Z Real Git Bash pre-commit now resolves a working Python launcher on Windows; direct gate reached only the expected stale-Judge block after this in-scope change.

## Acceptance Result
- PASS Safety/Isolation/Correctness/Performance/Compatibility: conformance `105/105`, including Judge-driven adversarial cases.
- PASS Build: full profile ran uncached; build exit 0, smoke exit 0.
- Evidence: `.vemo/run/T-20260711-governance-cost-proportionality-20260712T074157Z.log` and machine receipt.

## Conclusion
Outcome: accepted | Decision: continue | Key Evidence: uncached full receipt + conformance 105/105 | Risk: high | Next Action: complete two independent Judge passes.
