---
id: T-20260911-minimal-governance-kernel-and-plugin-extraction
risk: R2
change_class: security
state: AcceptancePassed
scope_in: ["AGENTS.md", "README.md", "SECURITY.md", "CHANGELOG.md", "ROADMAP.md", "CONTRIBUTING.md", "assets/**", "VERSION", ".gitignore", ".claude/**", "vemo.json", "vemo.task.json", "vemo.task.example.json", "vemo.config.yaml", "bin/**", "enforcement/**", "specs/**", "plugins/**", "extensions/**", "skill/**", "agents/**", "ui/**", "profiles/**", "presets/**", "eval/**", "tests/**", "docs/**", "tasks/**", ".vemo/judge.jsonl", ".vemo/run/**", ".vemo/evidence/**", ".github/**"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "python3 -m unittest discover -s tests"
    lint: "python3 bin/vemo check --self"
    smoke: "python3 eval/run.py"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260911-minimal-governance-kernel-and-plugin-extraction-20260911T100335Z.log"
judge:
  required: true
  verdict: pass
approved_commands: []
owning_chat: ""
heartbeat: 2026-09-11T09:56:28Z
---

# minimal governance kernel and plugin extraction

## Goal
Replace the accumulated platform-shaped architecture with a small repository governance kernel whose only
mandatory concepts are Policy, Task, Gate, Verify, and Evidence. Preserve non-core product capabilities as
explicitly enabled plugins, not default runtime dependencies or default operator concepts.

## Scope (In / Out)
- In: the core policy/task/gate/verification/evidence path; hook and CI adapters; default installation payload;
  migration of product, fleet, setup UI, extension inspection, skill tooling, automation, long-run budgeting,
  reports, presets, and profiles into optional plugins; focused tests, conformance, and synchronized docs.
- Out: `.governance/**`, `vemo-ai-agent-governance-report.html`, remote repository settings, branch-protection
  mutation, pushing, external services, third-party plugin registries, and unrelated project history.

## Pass/Fail Criteria
- [x] **Core boundary:** WHEN the default payload is enumerated, it SHALL contain only the CLI/core evaluator,
  one policy file, task template, hook/CI adapters, and core tests; it SHALL NOT contain Fleet, UI, product
  reporting, extension composition, skills, auto mode, presets, profiles, or their implementation modules.
- [x] **Concept reduction:** WHEN `vemo --help` is run without plugins enabled, it SHALL expose no more than six
  top-level concepts: `task`, `check`, `verify`, `status`, `init`, and `plugin`; task state SHALL be derived from
  authorization/evidence rather than a manually advanced six-state lifecycle.
- [x] **Single decision path:** WHEN a pre-action adapter and CI evaluate the same scope, destructive-action,
  verification, or approval case, both SHALL call the same policy evaluator and return the same stable
  `allow|deny|approval_required` reason; adapters SHALL contain no duplicate policy classification logic.
- [x] **Evidence binding:** WHEN verification succeeds, evidence SHALL record the task id, exact diff snapshot,
  commands, exits, and timestamp; changing an in-scope file or verification command SHALL make the evidence
  stale and SHALL block the merge check.
- [x] **Critical approval:** WHEN a change touches configured critical paths or destructive/outward actions,
  merge/action checks SHALL require approval injected by the CI/Harness environment, independent of model name
  or capability tier and impossible to self-grant by modifying a repository task file.
- [x] **Plugin isolation:** WHEN a bundled optional feature is disabled, it SHALL add no core command, policy,
  import, installation file, or gate behavior; WHEN explicitly enabled, its declared commands SHALL work through
  a small data-only manifest with safe relative entrypoints and deterministic collision/error handling.
- [x] **Migration:** WHEN an existing VEMO 1.x task/config/install is encountered, `vemo init` or a documented
  migration command SHALL produce the minimal format or fail closed for explicit policy mapping, without silently
  weakening scope, verification, critical path, destructive-action, secret, or CI enforcement; rollback SHALL be
  documented and locally testable.
- [x] **Reduction:** WHEN measured on shipped runtime code and mandatory policy documentation, the new default
  core SHALL be materially smaller than the current baseline (9,891 Python/Shell/test/eval LOC and 8,264
  docs/spec LOC), with the final evidence reporting exact before/after counts and explaining every retained file.
- [x] **Regression:** core unit tests, negative gate tests, packaged-install fixture, core selfcheck, hook selftest,
  conformance eval, shell syntax, Python compilation, and `git diff --check` SHALL pass against the final staged
  snapshot; the existing R2 transition gate separately requires two independent judge passes before commit.

## Plan
1. Specify the minimal machine contract first: one canonical policy schema, one minimal task authorization,
   one derived decision model, and one snapshot-bound evidence record. Retain a compatibility reader only where
   it enables safe migration; do not retain old concepts merely to preserve their names.
2. Consolidate governance logic into one dependency-free evaluator. Convert the CLI, hook, Git, and CI files
   into thin adapters around it; remove manual lifecycle transitions, capability-tier-dependent safety, local
   platform topology, and duplicated gate implementations.
3. Define the smallest useful plugin contract: data-only manifest, explicit enablement, safe local relative
   command entrypoints, no dependency graph, capability seams, implicit activation, or policy authority.
4. Move non-core capabilities into bundled plugins. Delete superseded composition/platform abstractions and
   ensure the default installer does not ship or import plugin code unless requested.
5. Replace the broad legacy test/eval surface with focused contract tests that prove positive and negative
   behavior at the shared evaluator, adapter, CI, evidence-staleness, approval, migration, and plugin boundaries.
6. Rewrite the entry documentation around the five core concepts and a short migration guide. Record exact
   deletion/LOC/payload reductions, run uncached verification, obtain two independent R2 judge passes, and
   commit only after every existing mechanical gate accepts the final range.

## Architecture decisions
- Risk is `normal|critical`; criticality is derived from paths/actions and may be raised explicitly, never
  lowered by model capability. Model routing belongs to the calling harness or an optional plugin.
- Local pre-action interception and server-side merge checking are mandatory enforcement moments. Git hooks are
  optional fast feedback adapters calling the same evaluator, not a third policy implementation.
- CI logs and a compact repository evidence record are authoritative enough for the core. Hash-linked judge
  history, multi-judge orchestration, telemetry analytics, and long-run budgets are optional plugin concerns.
- Plugin code is trusted local code invoked only after explicit enablement. The core validates its manifest and
  path boundary but does not pretend to sandbox plugins.

## Execution Log
- 2026-09-11T09:16:39Z Task created by `vemo task create`.
- 2026-09-11T09:19:01Z Human direction approved: rebuild the framework end-to-end for minimum complexity and retain other functions only as explicitly enabled plugins.
- Core rewritten around one evaluator and six CLI commands; optional features moved under six disabled plugins;
  the redundant extension-composition subsystem and generated documentation surface were deleted.
- Final core measurements: 14 payload files, 1,071 runtime/test/eval LOC, 234 mandatory policy/documentation LOC;
  reductions versus recorded baseline are 89.3% and 97.2% respectively.

## Acceptance Result
Worker verification and two independent R2 reviews PASS.

- Core unit tests: 14/14 PASS.
- Minimal conformance: 7/7 PASS.
- Packaged core fixture and optional setup-plugin install/check fixture: PASS.
- Core selfcheck, hook selftest, Python compilation, shell syntax, and `git diff --check`: PASS.
- Snapshot-bound evidence: `.vemo/evidence/T-20260911-minimal-governance-kernel-and-plugin-extraction.json`.
- Legacy transition receipt: `.vemo/run/T-20260911-minimal-governance-kernel-and-plugin-extraction-20260911T100335Z.log`.

## Conclusion
Implementation accepted by worker checks and two independent R2 review passes. Rollback point is `a63e256`;
the 1.x implementation and task history remain under `plugins/legacy/` and Git history.
