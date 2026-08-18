---
id: T-20260818-executable-ai-platform-topology
risk: R1
change_class: standard
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_product.py", "tests/test_product.py", "docs/PLATFORM.md", "docs/ADAPTERS.md", "docs/INDEX.md", "README.md", "tasks/T-20260818-executable-ai-platform-topology.md"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 -m unittest tests.test_product"
    lint: "python3 -m py_compile bin/vemo bin/vemo_product.py"
    smoke: "bin/vemo platform --json"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260818-executable-ai-platform-topology-20260818T073549Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: 2026-08-18T07:36:11Z
---

# executable ai platform topology

## Goal
Turn VEMO's implicit AI-governance middle-platform structure into a stable, read-only, machine-readable
platform topology and runtime-authority view, informed by Wildmeerkat's explicit plane separation without
importing its channel coupling or single-writer bottleneck.

## Scope (In / Out)
- In: the user-facing CLI/product module, focused product tests, a platform architecture explanation,
  adapter/index/README integration, and this task record; mirror `scope_in` above.
- Out: `specs/**`, `enforcement/**`, `vemo.config*.yaml`, Fleet behavior, external channel bridges,
  source-repository mutations in Wildmeerkat, releases, commits, and pushes.

## Pass/Fail Criteria
- [Correctness] WHEN `build_platform()` inspects a repository, the result SHALL contain exactly the six
  unique responsibility planes `ingress`, `control`, `policy`, `execution`, `enforcement`, and `evidence`,
  plus an ordered request lifecycle and per-component presence facts — metric: focused unit assertions pass.
- [Authority] WHEN ring-2 Git gates and ring-3 CI are absent/present, the result SHALL classify locally
  observable posture as `advisory` / `local_gates` / `ci_backstop_present`, while marking remote branch
  protection `not_locally_verified`; it SHALL NOT infer authority that local files cannot prove — metric:
  all three synthetic-repository cases pass.
- [Safety] WHEN platform inspection runs against a repository containing a sentinel secret, it SHALL make no
  filesystem changes and SHALL emit neither file contents nor absolute repository paths — metric: before/after
  tree snapshots are identical and the sentinel is absent from serialized output.
- [CLI] WHEN `bin/vemo platform --json` runs, it SHALL exit 0 and emit parseable schema-versioned JSON with
  `read_only=true` — metric: wrapper/JSON unit assertion and smoke command pass.
- [Documentation] WHEN a reader opens `docs/PLATFORM.md`, it SHALL find plane ownership, authority boundaries,
  the end-to-end lifecycle, and explicit adopt/retain decisions from the Wildmeerkat comparison; README,
  adapter docs, and docs index SHALL link the interface — metric: documentation assertions pass.
- [Build] `python3 -m unittest tests.test_product`, `python3 -m py_compile bin/vemo bin/vemo_product.py`, and
  `bin/vemo selfcheck` SHALL each exit 0.

## Plan
1. Add a declarative six-plane contract and read-only filesystem probes to `bin/vemo_product.py`.
2. Route `vemo platform [--json]` through the existing product CLI and expose it in help/explain output.
3. Document the responsibility planes, request lifecycle, authority model, and selective Wildmeerkat lessons.
4. Add focused tests for schema stability, read-only/privacy behavior, authority classification, CLI output,
   and documentation linkage; run the repository's selfcheck and focused verification receipt.

## Read Audit
- `/home/aimer/Project/ClaudeTest/Wildmeerkat/{AGENTS.md,CLAUDE.md,SYSTEM_DESIGN.md,README.md}` — whole files;
  governance constraints and normative architecture model.
- `/home/aimer/Project/ClaudeTest/Wildmeerkat/docs/mid-platform-architecture.html` — lines 80-210;
  ingress/leader/team/policy/gate/record layering and request lifecycle.
- `/home/aimer/Project/ClaudeTest/Wildmeerkat/{spec/law_digest.md,spec/record_spec.md,team/leader.md}` — whole
  files; single-source records, evidence grades, role ownership, and explicit trade-offs.
- `/home/aimer/Project/ClaudeTest/Wildmeerkat/aiigovernance_bridge/{router,config,lifecycle,preflight,verify}.py`
  — symbol/call-site index; route decisions, sticky sessions, preflight, lifecycle, and health verification.
- `README.md`, `docs/{MENTAL_MODEL,ADAPTERS,PRODUCT,FLEET}.md`, `ROADMAP.md`, `bin/vemo`,
  `bin/vemo_product.py`, and `tests/test_product.py` — existing VEMO surfaces and extension points.

## Execution Log
- 2026-08-18T07:27:00Z Task created by `vemo task create`.
- 2026-08-18T07:27:45Z Plan completed: six-plane read-only platform contract; Wildmeerkat comparison and acceptance criteria recorded.
- 2026-08-18T07:33:47Z Implemented six-plane platform topology, local delivery posture probe, CLI routing, focused tests, and architecture documentation.
- 2026-08-18T07:34:37Z Verification passed: full local unittest suite 23/23, selfcheck OK, py_compile OK, platform JSON contract OK.
- 2026-08-18T07:34:37Z Fresh focused vemo verify receipt passed (test=0 lint=0 smoke=0): .vemo/run/T-20260818-executable-ai-platform-topology-20260818T073406Z.log.
- 2026-08-18T07:35:57Z Re-ran focused verification after CLI help parity fix: fresh receipt test=0 lint=0 smoke=0 at .vemo/run/T-20260818-executable-ai-platform-topology-20260818T073549Z.log.
- 2026-08-18T07:36:11Z Process deviation recorded: one smoke command wrote /tmp/vemo-platform-output.json (7,780 bytes) outside repo; file contains platform JSON only and remains because out-of-repo deletion lacks explicit approval.

## Acceptance Result
- [Correctness] PASS — focused tests assert the exact six plane IDs, ordered eight-stage lifecycle,
  per-component presence, and optional-evidence behavior.
- [Authority] PASS — synthetic repositories produced `advisory`, `local_gates`, and
  `ci_backstop_present`; remote branch protection remained `not_locally_verified`.
- [Safety] PASS — the read-only tree snapshot was byte-identical before/after; sentinel secret and absolute
  temporary root were absent from serialized output.
- [CLI] PASS — the real `bin/vemo platform --json` wrapper emitted parseable schema v1 JSON with
  `read_only=true`; smoke exit 0.
- [Documentation] PASS — platform ownership/lifecycle/Wildmeerkat decisions are documented and linked from
  README, adapter reference, and docs index.
- [Build] PASS — focused tests 8/8; full local suite 23/23; py_compile exit 0; selfcheck OK.
- [Ground truth] PASS — fresh receipt evidence
  `.vemo/run/T-20260818-executable-ai-platform-topology-20260818T073549Z.log`, test/lint/smoke all exit 0.

## Conclusion
Outcome: accepted · Decision: stop · Key Evidence: focused receipt test/lint/smoke 0/0/0, full local suite
23/23, selfcheck OK, JSON smoke contract passed · Risk: low (read-only R1 product surface; no enforcement or
policy semantics changed). Process deviation: a smoke command wrote `/tmp/vemo-platform-output.json` (7,780
bytes, platform JSON only) outside the task scope; it remains because deleting an out-of-repo file requires
explicit user approval · Next Action: user may review `vemo platform` / `vemo platform --json`, optionally
authorize deletion of that exact temporary file; no commit or push was requested.
