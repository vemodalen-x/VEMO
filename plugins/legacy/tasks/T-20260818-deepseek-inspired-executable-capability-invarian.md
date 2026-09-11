---
id: T-20260818-deepseek-inspired-executable-capability-invarian
risk: R1
change_class: standard
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_product.py", "tests/test_product.py", "docs/PLATFORM.md", "README.md", "tasks/T-20260818-deepseek-inspired-executable-capability-invarian.md"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 -m unittest tests.test_product"
    lint: "python3 -m py_compile bin/vemo bin/vemo_product.py"
    smoke: "bin/vemo platform --check --json"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260818-deepseek-inspired-executable-capability-invarian-20260818T075724Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: "codex-deepseek-platform-invariants-20260818"
heartbeat: 2026-08-18T07:58:02Z
---

# DeepSeek-inspired executable capability invariants

## Goal
Turn the existing VEMO platform inventory into an executable, content-minimizing integration contract by
adopting DeepSeek Harness's explicit capability seams and owner-local relationship invariants without adding
a plugin runtime or moving authority out of the existing enforcement layer.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: enforcement behavior, adapter installation files, VEMO configuration, generated evidence, and the
  unrelated user-owned `VEMO_SKILLS/` tree.

## Pass/Fail Criteria
- [x] `vemo platform --json` exposes stable Definition/Provider/Consumer roles for each declared capability
  seam and distinguishes source, durable-record, and runtime-artifact materialization.
- [x] The platform report validates installed ring-1 adapter bindings against the canonical hook contract and
  validates an observed verification receipt's task/log references; an absent optional adapter or receipt is
  reported as `not_observed`, not as a core failure.
- [x] `vemo platform --check` returns non-zero when a required component or an observed relationship fails,
  while the repository's healthy topology returns zero.
- [x] The probe stays read-only and emits no command bodies, source, prompt/telemetry content, credentials, or
  absolute checkout path; tests cover healthy, absent, malformed, stale-reference, and privacy cases.
- [x] README and `docs/PLATFORM.md` explain the DeepSeek-derived choices and the boundary between topology,
  relationship checking, runtime execution proof, and remote authority.

## Plan
- Extend the versioned platform schema with capability seams, component materialization, and narrowly owned
  relationship checks.
- Add `--check` exit semantics while retaining `platform` as a read-only inspection command.
- Exercise positive and counterexample fixtures through the public builder/CLI and update the architecture
  documentation.
- Run the focused task verification plus the repository self-check and inspect the generated evidence log.

## Execution Log
- 2026-08-18T07:40:15Z Task created by `vemo task create`.
- 2026-08-18T07:50:02Z Implemented schema v2 capability seams, source/record/artifact materialization, ring-1 adapter and receipt-chain invariants, plus --check exit semantics. Added positive/counterexample/privacy tests and documented the DeepSeek Harness design transfer. Targeted unit suite passes (10 tests); one pre-existing subprocess ResourceWarning remains visible.
- 2026-08-18T07:51:33Z Verification: focused vemo verify ran uncached; test/lint/smoke all exited 0. Evidence log inspected by command markers and tail (506 lines, so not bulk-read): 10 focused tests OK, schema_version=2, invariant_status=pass, check_status=pass. Full suite also passed 25 tests; selfcheck and doctor returned OK.
- 2026-08-18T07:55:38Z Code review reopened acceptance: fix out-of-checkout symlink false-presence/read risk, fail closed on NUL-bearing receipt log paths, and remove the optional adapter-doc/required seam-definition contradiction; add counterexample coverage before commit.
- 2026-08-18T07:57:14Z Resolved all code-review findings: all platform presence/config/authority probes now reject out-of-checkout symlinks, path parsing catches malformed/NUL inputs, hook matching requires an enforcement path-segment boundary, and the ring-1 seam no longer makes optional adapter docs mandatory. Added symlink and NUL counterexamples; focused suite passes 11 tests.
- 2026-08-18T07:57:47Z Post-review verification: full suite 26/26, focused suite 11/11, py_compile and platform --check passed, selfcheck/doctor OK. Inspected the 502-line uncached evidence log via markers and tail; all three commands exited 0 and schema/invariant/check status are healthy.

## Acceptance Result
PASS after review fixes. The uncached focused receipt records `test=0`, `lint=0`, and `smoke=0`; its
502-line log was sampled through command/exit markers and the final platform payload. Focused tests passed
11/11, the complete unit suite passed 26/26, and `vemo selfcheck`, `vemo doctor`, and the post-run platform
check returned OK. The full suite still surfaces a non-failing, pre-existing Python `ResourceWarning` from
subprocess cleanup; this task does not alter that enforcement-owned path.

## Conclusion
Outcome: accepted after code review. Decision: continue to the user-authorized commit and push. Key evidence:
the focused receipt/log above plus negative fixtures covering incomplete bindings, malformed/dangling/NUL
receipt references, privacy, and out-of-checkout symlinks. Residual risk: these checks prove local composition
and referential integrity, not hook execution or remote branch protection; the existing eval, Git, and CI
mechanisms retain that authority.
