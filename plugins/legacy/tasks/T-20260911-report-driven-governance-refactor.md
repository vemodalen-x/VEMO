---
id: T-20260911-report-driven-governance-refactor
risk: R2
change_class: security
state: AcceptancePassed
scope_in: ["enforcement/validators/**", "enforcement/hooks/run.py", "enforcement/automation/vemo-auto", "bin/vemo", "bin/vemo_product.py", "bin/vemo_setup/**", "bin/vemo_composition/**", "bin/vemo_extensions.py", "extensions/**", "tests/**", "eval/run.py", "docs/**", "README.md", "SECURITY.md", "CHANGELOG.md", "ROADMAP.md", "specs/**", "tasks/T-*-report-driven*", ".vemo/judge.jsonl", ".vemo/run/**"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 -m unittest discover -s tests"
    lint: "python3 enforcement/validators/task_state.py selfcheck"
    smoke: "python3 eval/run.py"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260911-report-driven-governance-refactor-20260911T080317Z.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked: [".vemo/run/T-20260911-report-driven-governance-refactor-20260911T080317Z.log", "enforcement/validators/task_state.py:68", "enforcement/validators/task_state.py:120", "enforcement/validators/task_state.py:744", "enforcement/hooks/run.py:229", "bin/vemo_setup/service.py:341", "SECURITY.md:15"]
  confidence: high
approved_commands: []
owning_chat: ""
heartbeat: 2026-09-11T08:04:53Z
---

# Report-driven governance refactor

## Goal
Implement the report's highest-value P0 recommendations as a compatibility-preserving governance-kernel
increment: stable policy-decision/evidence contracts, tamper-evident judge provenance, explicit extension
capability metadata, stronger installation live-fire diagnostics, and product-visible posture. Keep VEMO
repo-native and avoid introducing a central service, workflow engine, UI rewrite, or sandbox implementation.

## Scope (In / Out)
- In: the validator/hook decision path, judge evidence ledger, declarative extension contract and resolver,
  setup diagnostics, product/platform reporting, focused conformance tests, and synchronized documentation.
- Out: the untracked report itself; `.governance/**`; remote mutations; OPA/Cedar/OpenFGA/Temporal/E2B
  integrations; OS sandboxing; signed package registries; schema migrations requiring consumer intervention.

## Pass/Fail Criteria
- [x] **Security — Evidence integrity:** WHEN judge records are appended, the system SHALL emit a versioned,
  canonical hash-linked row; WHEN a linked row is altered, removed from the linked suffix, reordered, or has
  an invalid predecessor, `selfcheck` and the required-judge gate SHALL fail. Existing legacy rows SHALL remain
  readable as an explicit legacy prefix so current repositories do not break on upgrade.
- [x] **Correctness — Decision contract:** WHEN ring-1 guards evaluate an action, the internal result SHALL use
  a stable decision envelope with `effect`, `reason_code`, and obligations/details suitable for adapters, while
  preserving the current exit-code/stdout/stderr contract and redacting sensitive payload values.
- [x] **Correctness — Extension contract:** WHEN an extension declares compatibility/capability permissions,
  validation SHALL reject unknown, duplicate, malformed, or incompatible declarations deterministically;
  schema-v1 manifests without the optional fields SHALL continue to resolve unchanged, and manifests SHALL
  remain non-executable data.
- [x] **Operational safety — Installation diagnostics:** WHEN `check_install` runs in an isolated installed
  fixture, it SHALL report executable allow, deny, and configured fail-closed probes plus Python/runtime source;
  every probe SHALL be bounded, read-only outside its temporary fixture, and return structured remediation.
- [x] **Observability — Product posture:** WHEN `vemo platform --json` or the product report is generated, it
  SHALL expose decision-contract version, evidence-ledger integrity state, extension compatibility state, and
  installation probe posture without exposing repository absolute paths, prompts, secrets, or telemetry bodies.
- [x] **Compatibility:** Existing public CLI verbs, hook exit semantics, task schema, manifest schema-v1 happy
  path, setup preview/apply/rollback, and current test fixtures SHALL remain backward compatible.
- [x] **Verification:** focused unit suite, validator selfcheck, hook selftest, setup/product/extension/judge
  regression tests, full `eval/run.py`, shell syntax checks, and two independent R2 judge passes SHALL all pass
  with evidence recorded under `.vemo/run/**`.

## Plan
1. Introduce small, dependency-free contract helpers at existing ownership boundaries; do not move Git/CI
   authority into a new service. Preserve adapter-facing behavior and add stable reason codes/envelopes behind it.
2. Upgrade judge provenance append/verify logic to a versioned hash chain with a documented legacy-prefix rule;
   wire integrity failures into `selfcheck`, doctor/platform posture, and the existing required-judge gate.
3. Extend declarative extension validation/resolution with optional compatibility and permission metadata,
   deterministic diagnostics, and no executable entry-point support.
4. Add bounded setup live-fire probes that exercise one allow, one deny, and one fail-closed path in temporary
   fixtures; report runtime provenance and remediation through existing CLI/UI data structures.
5. Surface the new contract/integrity/posture signals through `vemo platform` and product reports; update adapter,
   platform, extension, installation, security, roadmap, changelog, and index documentation without overstating
   remote protection or sandbox guarantees.
6. Add unit and conformance regressions for positive, negative, tamper, legacy-compatibility, redaction, and
   packaged-install cases. Run the focused commands above, address failures, then obtain two fresh independent
   governance-judge passes bound to the final staged snapshot.

## Assumptions and compatibility decisions
- The report is architectural guidance, not a mandate to implement every P0/P1/P2 item in one patch. This task
  implements a reviewable P0 kernel increment; environment brokers, external PDP providers, OTLP, durable
  execution, signatures, and remote-control mutation remain follow-up work.
- `allow/deny/ask/obligations` is introduced as a portable contract vocabulary, but existing local guards still
  produce only allow/deny until an approval-capable adapter is implemented.
- Hash chaining begins after the existing ledger as an explicitly recognized legacy prefix. Rewriting historical
  `.vemo/judge.jsonl` rows would destroy audit history and is therefore forbidden.
- Optional extension metadata is additive under schema version 1; making it mandatory would be a breaking change.

## Execution Log
- 2026-09-11T06:45:16Z Task created by `vemo task create`.
- Claude Code completed repository/report discovery and baseline tests, then stopped before implementation due
  to an Anthropic API rate-limit error; no tracked source file was changed.
- Codex resumed the same session binding, verified baseline `dd3845d`, recovered the original request and audit
  trail, and replaced the placeholder task card with this report-mapped R2 plan.
- Implementation added policy-decision schema v1, a legacy-anchored judge hash chain, additive extension
  compatibility/permission metadata, isolated setup live-fire probes, platform schema v4 posture, and docs/tests.
- Focused verification first failed because the task YAML subset parser does not preserve nested single quotes
  in a double-quoted command; disposition `RCA-inline`: replaced the equivalent unittest glob with discovery's
  default `test*.py`, reran uncached, and passed all commands.

## Acceptance Result
PASS (worker verification complete; independent R2 review completed against the final staged snapshot).

- `python3 -m unittest discover -s tests`: 83/83 PASS.
- `python3 enforcement/validators/task_state.py selfcheck`: PASS.
- `python3 eval/run.py`: 133/133 PASS.
- `python3 enforcement/hooks/run.py --selftest`: PASS.
- Python `py_compile`, Git-hook/automation `bash -n`, `git diff --check`, and
  `python3 bin/vemo platform --check --json`: PASS.
- Machine receipt: `.vemo/run/receipt.json`; evidence:
  `.vemo/run/T-20260911-report-driven-governance-refactor-20260911T080317Z.log`.

## Conclusion
Outcome accepted. Decision: commit the verified governance-kernel increment. Baseline/rollback point:
`dd3845d7a9c41a4faa580d6aa248287783f93991`. Compatibility risk is limited to additive JSON fields and platform
schema v4; existing CLI/hook behavior remains stable. Existing untracked `.governance/**` and the report HTML
remain inputs/out-of-scope and are intentionally excluded from this task's commit.
