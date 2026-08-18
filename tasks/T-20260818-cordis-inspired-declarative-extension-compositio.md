---
id: T-20260818-cordis-inspired-declarative-extension-compositio
risk: R1
change_class: standard
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_extensions.py", "bin/vemo_composition/**", "bin/vemo_product.py", "extensions/**", "tests/test_extensions.py", "tests/test_product.py", "docs/EXTENSIONS.md", "docs/PLATFORM.md", "docs/INDEX.md", "README.md", "tasks/T-20260818-cordis*"]
scope_out: ["VEMO_SKILLS/**", "enforcement/**", "specs/**", "vemo.config*.yaml", "dynamic extension code execution", "hot reload", "pushes"]
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 -m unittest discover -s tests"
    lint: "bin/vemo selfcheck"
    smoke: "bin/vemo extensions --check --json"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260818-cordis-inspired-declarative-extension-compositio-20260818T090816Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: 2026-08-18T08:58:38Z
---

# Cordis inspired declarative extension composition

## Goal
Refactor VEMO around a safe Cordis-inspired composition core: stable context capabilities, typed contribution
points, scoped reversible effects, and a reconciling declarative loader. Preserve the public CLI/report
contracts without adding an arbitrary-code plugin runtime or weakening existing governance authority.

## Scope (In / Out)
- In: modular composition contracts/context/loader, extension façade and registry/resolver, CLI
  inspection/checking, platform seam contributions, built-in manifests, focused tests, and documentation.
- Out: executable third-party plugins, hot module replacement, event buses, enforcement/config/spec changes,
  the user-owned `VEMO_SKILLS/` tree, and pushes.

## Pass/Fail Criteria
- [x] Correctness — WHEN valid extension manifests provide and require capabilities, the resolver SHALL emit
  each extension exactly once in deterministic dependency order and `vemo extensions --check --json` SHALL
  exit 0.
- [x] Safety — WHEN a manifest is malformed, duplicated, cyclic, missing a provider, or contains an unsafe
  path/symlink, the resolver SHALL emit stable issue codes without reading outside the checkout or executing
  extension code, and `--check` SHALL exit 2.
- [x] Extensibility — WHEN platform seam contributions are declared in manifests, `vemo platform --json`
  SHALL derive the seam topology from the resolved extensions and SHALL fail its check if composition fails.
- [x] Temporal composability — WHEN a registered manifest's disposer is invoked, the registry SHALL remove
  only that registration idempotently and recompute dependent failures.
- [x] Separation — WHEN maintainers inspect the implementation, the CLI façade SHALL remain at most 120 lines
  and contracts, context/effects, and filesystem loading SHALL live in independently importable modules.
- [x] Spatial composability — WHEN a child context requires a capability actively provided by its parent, it
  SHALL resolve without copying the parent registration; removal from the parent SHALL make the child wait.
- [x] Typed contributions — WHEN a new declarative contribution spec is supplied to a context, it SHALL be
  validated and aggregated without editing the dependency resolver or filesystem loader.
- [x] Temporal scope — WHEN an effect scope is disposed, tracked registrations SHALL unwind in reverse order,
  dispose once, and leave unrelated registrations intact.
- [x] Incremental reconciliation — WHEN a long-lived loader reconciles an unchanged or partially changed
  activation set, unchanged registrations SHALL retain identity while only added, changed, and removed
  manifest effects are mounted or disposed, with a deterministic transition report.
- [x] Failure isolation — WHEN the activation index as a whole is unreadable or structurally unsupported,
  the loader SHALL defer the new revision, retain its last valid registrations, emit stable diagnostics, and
  continue to expose a failing check result without executing manifest code.
- [x] Compatibility — WHEN the repository's full test suite, selfcheck, and doctor run, all tests/selfcheck
  SHALL exit 0; doctor SHALL have no new failure introduced by this task.

## Plan
1. Implement a stdlib-only manifest registry with strict schemas, safe local discovery, reversible
   registration, capability resolution, deterministic topological order, and machine-readable diagnostics.
2. Add `vemo extensions [--json] [--check]`; integrate resolved platform-seam contributions into the existing
   platform report while preserving authority and privacy boundaries.
3. Move the two built-in seam declarations into extension manifests and document the extension contract,
   lifecycle, non-goals, and Cordis design mapping.
4. Cover success, teardown, missing/duplicate/cyclic dependency, unsafe path/symlink, CLI, and platform
   integration paths; run focused and repository-wide verification.
5. Extract the accepted single-file implementation into `contracts`, `context`, and `loader` modules; keep
   `bin/vemo_extensions.py` as a compatibility façade and preserve report schema v1/platform schema v3.
6. Add child-context inheritance, grouped LIFO effects, loader reconciliation, and generic typed-contribution
   tests; update architecture documentation and repeat machine acceptance after the refactor.
7. Compare Wildmeerkat `origin/lite` and `origin/dev`; transfer its idempotent lifecycle, explicit degraded
   state, and authoritative evidence ideas into an incremental manifest reconciler without creating branch
   forks, background services, or executable plugins.

## Comment Review
- New and behavior-changing functions: approved — contracts, context/effects, loader, and façade functions
  document inputs, bounded stages, outputs/side effects, teardown behavior, and `@codex-comment` ownership;
  tests use descriptive behavioral names.

## Execution Log
- 2026-08-18T08:04:17Z Task created by `vemo task create`.
- 2026-08-18T08:17:10Z Implemented manifest-only registry, activation index, reversible registration, dependency resolution, extensions CLI, platform integration, docs, and 18 focused tests.
- 2026-08-18T08:17:41Z Acceptance evidence: focused vemo verify PASS (18 tests, py_compile, extensions smoke); full suite 33/33 PASS; selfcheck OK; platform check PASS; doctor OK with historical stale-task/python-alias notes only.
- 2026-08-18T08:20:10Z Re-ran machine acceptance after clarifying waiting/conflict/cycle summary counts: full 33-test suite, selfcheck, and extensions smoke all PASS.
- 2026-08-18T08:28:49Z Reopened accepted task for modular Cordis refactor: split contracts/context/effects/loader behind the existing façade; preserve manifest-only safety and public schemas.
- 2026-08-18T08:36:52Z Refactored 605-line extension monolith into contracts/context/effects/loader package behind an 81-line façade; added child inheritance, LIFO scope, typed contribution, reconcile, identity, and platform-component coverage. Preliminary full suite 36/36 PASS.
- 2026-08-18T08:37:33Z Modular refactor acceptance PASS: machine receipt covers 36/36 tests, selfcheck, and extensions smoke; platform, py_compile, diff check, and doctor also PASS.
- 2026-08-18T08:53:05Z Reopened the accepted R1 task after comparing Wildmeerkat `origin/lite` with its
  34-commit-ahead `origin/dev`: selected incremental lifecycle reconciliation and explicit degraded-state
  reporting; retained VEMO's manifest-only trust boundary and native verification receipts.
- 2026-08-18T08:57:40Z Implemented normalized manifest fingerprints, per-manifest scopes, retained identity,
  reverse delta teardown, `applied`/`noop`/`deferred` transition metadata, and last-valid retention for
  index-level failures. Added unchanged/reorder/change/removal/malformed/unsupported tests; preliminary
  focused 11/11 and full 38/38 suites PASS, plus selfcheck, extension/platform checks, doctor, and diff check.
- 2026-08-18T09:07:34Z User authorized final code review and one local commit; push remains explicitly out
  of scope. Review covers the complete task-owned change set and excludes the user-owned `VEMO_SKILLS/` tree.
- 2026-08-18T09:08:16Z Final review found no blocking correctness, security, or compatibility issues.
  Uncached acceptance regenerated successfully: full 38/38 tests, selfcheck, and extensions smoke exited 0;
  platform check, doctor, and diff check also passed.

## Acceptance Result
- PASS — the uncached machine receipt ran the full 38-test suite, `vemo selfcheck`, and the real extensions
  JSON smoke; all three commands exited `0`.
- PASS — focused tests prove unchanged and reordered indexes are no-ops, only changed manifests remount,
  invalid manifests are isolated, and malformed/unsupported indexes retain the last valid revision while
  returning a failing report with `reconciliation_deferred`.
- PASS — real `vemo extensions --check` and `vemo platform --check` both passed; `py_compile`,
  `git diff --check`, and `vemo doctor` also exited `0`.
- PASS — the report remains schema v1 and manifest-only; its additive `reconciliation` object exposes
  attempts, applied revisions, and deterministic deltas without absolute paths or manifest contents.
- Evidence: `.vemo/run/T-20260818-cordis-inspired-declarative-extension-compositio-20260818T090816Z.log`

## Conclusion
Outcome: accepted · Decision: stop · Key Evidence: uncached 38/38 receipt plus focused lifecycle tests ·
Reference transfer: Wildmeerkat `lite` supplied the compact entry model while `dev` supplied idempotent
lifecycle/degraded-state/evidence patterns · Boundary: VEMO keeps its native receipt system and declarative
manifests, and does not add a governance MCP, background worker, executable plugin loader, or branch fork.
