---
# ── Machine-readable state (hooks & CI parse THIS; keep it accurate) ──
id: T-20260708-skill-eval-and-consistency-audit
risk: R2                        # touches enforcement/** + vemo.config.yaml — highest blast radius
state: AcceptancePassed         # PlanCreated|ReviewApproved|ImplementationDone|AcceptancePassed|ProcedureCompleted|Archived
scope_in:
  - "enforcement/validators/skill_check.py"
  - "bin/vemo"
  - "eval/run.py"
  - "VERSION"
  - "vemo.config.yaml"
  - "CHANGELOG.md"
  - "README.md"
  - "docs/html/**"
  - "tasks/T-20260708-skill-eval-and-consistency-audit.md"
  - ".vemo/judge.jsonl"
scope_out:
  - "enforcement/validators/task_state.py (the verdict engine — untouched; 68/68 core must hold)"
  - "existing eval check semantics (only additive: a new `skill` group)"
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260708-skill-eval-and-consistency-audit-20260708-115243.log"
judge:
  required: true                # R2 + capability.tier=high → 2 independent judge passes required
  verdict: pass
approved_commands: []
owning_chat: local-improvement
heartbeat: 2026-07-08T12:00
---

# Skill quality bar + registry consistency audit (VEMO skill/)

## Goal
Close the gap where `selfcheck` only asserted a SKILL.md *exists*: add a transparent, gating skill
quality bar and a catalog<->disk consistency audit — additively, keeping the verdict engine untouched
and the conformance eval green.

## Scope (In / Out)
- In: a self-contained `skill_check.py`, its `bin/vemo` verbs, a new eval `skill` group, and the
  version/docs the release obliges.
- Out: `task_state.py` (the verdict engine) and existing eval semantics — this change is purely additive.

## Pass/Fail Criteria  (EARS-style, measurable)
- [Additive] WHEN `python3 eval/run.py` runs, it SHALL report 71/71 (68 prior + 3 new `skill` checks).
- [Consistency] WHEN a skill is unlisted in `_catalog.md`, orphaned, or cites a missing script, `vemo
  skill-audit` SHALL fail with the specific reason.
- [Honesty] `vemo selfcheck` SHALL stay green: no new `vemo.config.yaml` key (every-key-has-a-consumer holds).
- [Fidelity] `vemo skill-score` SHALL pass on VEMO's 7 real skills (noun names accepted; no gerund rule).
- [Ground truth] `vemo verify` SHALL produce a passing receipt (build=eval 71/71, smoke=selfcheck OK).

## Plan
- Add `enforcement/validators/skill_check.py` (score + audit + hermetic selftest), self-contained.
- Wire `skill-score`/`skill-audit` into `bin/vemo`; add an eval `skill` group (score/audit/selftest).
- Bump VERSION/config/CHANGELOG/README + regenerate `docs/html`; keep eval + selfcheck green.

## Execution Log
- 2026-07-08: added skill_check.py; selftest 8/8; scores VEMO's 7 skills PASS (6/6 gating).
- 2026-07-08: wired bin/vemo + eval skill group; `eval` 71/71; `selfcheck` OK.
- 2026-07-08: bumped to 1.3.0 (VERSION/config/CHANGELOG/README) + regenerated docs/html.
- 2026-07-08: `vemo verify` receipt + 2 independent governance-judge passes (see Acceptance/judge).

## Acceptance Result
- [Additive] PASS — `git diff task_state.py` empty; eval 68→71/71.
- [Consistency] PASS — `skill-audit` fails on unlisted/orphan/dangling (judges reproduced independently).
- [Honesty] PASS — `selfcheck` OK; no new config key.
- [Fidelity] PASS — `skill-score` PASS on 7 real skills (noun names; cue advisory).
- [Ground truth] PASS — `vemo verify` receipt build_exit=0 smoke_exit=0.
- Judge: 2 independent passes (correctness/additivity + safety/consistency lenses) in `.vemo/judge.jsonl`.

## Conclusion
Outcome: accepted · Decision: continue → PR · Key Evidence: eval 71/71, selfcheck OK, receipt 0/0, 2 judge passes ·
Risk: R2 (additive; verdict engine untouched) · Next Action: branch → commit → push → PR (PR-only).
