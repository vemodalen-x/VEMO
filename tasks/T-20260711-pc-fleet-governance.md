---
id: T-20260711-pc-fleet-governance
risk: R1
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_fleet.py", "tests/test_fleet.py", "profiles/*.json", "docs/FLEET.md", "docs/STANDARDS.md", "README.md", "CHANGELOG.md", "eval/run.py", "tasks/T-20260711-pc-fleet-governance.md", ".vemo/run/T-20260711-pc-fleet-governance*.log", ".vemo/run/receipt.json"]
scope_out: ["enforcement/**", "specs/**", "vemo.config.yaml", ".github/**", "../VEMO_SKILLS/**", "../photo_archive*", "../m3u8_*"]
trifecta: ["private_data"]
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260711-pc-fleet-governance-20260711-112756.log"
judge:
  required: false
  verdict: null
approved_commands: ["python bin/vemo fleet install --apply", "python bin/vemo fleet register <discovered-project> --profile solo", "python bin/vemo fleet audit --repair --apply", "append %USERPROFILE%/.vemo/bin to the current-user PATH"]
owning_chat: "chat-20260711-vemo-fleet"
heartbeat: "2026-07-11T11:32+08:00"
---

# PC Fleet Governance

## Goal
Turn VEMO from a per-repository toolkit into a professional local control plane that can inventory, assess, and safely onboard every Git project on one PC.

## Scope (In / Out)
- In: stdlib-only fleet CLI, local project registry, governance profiles, read-only discovery and reporting, explicit dry-run/apply onboarding, tests, and standards/product documentation.
- Out: existing enforcement semantics, risk rules, CI authority, unrelated desktop applications, remote SaaS control plane, and automatic writes to discovered repositories.

## Pass/Fail Criteria
- [Safety] WHEN discovery or fleet status runs, the system SHALL remain read-only and SHALL NOT register or modify projects without an explicit command; metric: filesystem snapshot tests show no target changes.
- [Correctness] WHEN a Git project is registered, the registry SHALL store a canonical path, stable project id, profile, timestamps, and framework health without duplicate entries; metric: unit tests cover duplicate and missing-path cases.
- [Correctness] WHEN fleet status runs, each project SHALL receive deterministic readiness findings for Git, VEMO files, hooks, CI, task health, and profile requirements; metric: text and JSON report tests pass.
- [Safety] WHEN onboarding is requested, the default SHALL be dry-run and `--apply` SHALL refuse dirty targets or conflicting governed files; metric: conflict and dirty-worktree tests pass.
- [Product] Three progressive profiles SHALL map business maturity to enforceable requirements without claiming certification; metric: schema validation tests pass and standards mapping documents evidence/limits.
- [Portability] Fleet operations SHALL run with Python stdlib on Windows and POSIX path conventions; metric: path and launcher-neutral tests pass.
- [Build] `python -m unittest discover -s tests -v` SHALL exit 0.
- [Build] `python eval/run.py` and `python bin/vemo selfcheck` SHALL exit 0.

## Plan
- Add a small, dependency-free fleet module and expose it through `vemo fleet` with register, unregister, discover, status, and onboard verbs; keep discovery/status read-only and onboarding preview-first.
- Define solo, team, and regulated profiles as machine-readable product policy packs, then score project readiness with actionable findings and JSON export.
- Add deterministic unit tests, wire them into the conformance evaluation, and document architecture, operating model, standards mapping, privacy boundaries, and rollout guidance.
- Add a matching VEMO_SKILLS operating skill in its own repository after the core CLI is verified.

## Execution Log
- 2026-07-11T11:10+08:00 task created; machine path classifier returned R1 because no enforcement/spec/CI controls are modified.
- 2026-07-11T11:18+08:00 implemented Fleet CLI, profiles, optional VEMO_SKILLS binding, standards docs, and focused tests.
- 2026-07-11T11:22+08:00 verification preflight passed: unit tests, VEMO conformance 84/84, selfcheck OK, diff-check clean.
- 2026-07-11T11:24+08:00 live parallel registration exposed Windows replace contention; added cross-process locks, concurrent coverage, and preserve-before-restart audit recovery.
- 2026-07-11T11:27+08:00 first verify-run failed 9009 because configured `python3` was absent on Windows; RCA-inline: execution environment alias only, no product/test failure.
- 2026-07-11T11:28+08:00 verify-run repeated with VEMO's existing Windows python3 shim; build_exit=0 smoke_exit=0 evidence `.vemo/run/T-20260711-pc-fleet-governance-20260711-112756.log`.
- 2026-07-11T11:29+08:00 installed the user-local launcher, registered 12 discovered projects at the solo baseline without modifying them, verified the 13-event audit chain, and appended the launcher directory to current-user PATH.

## Acceptance Result
- PASS [Safety] discovery/status remained read-only; nested-repository snapshot and dry-run tests passed.
- PASS [Correctness] canonical registry ids, deduplication, 8-way concurrent registration, missing paths, deterministic checks, text/JSON contracts, and 12-project live registration passed.
- PASS [Safety] onboarding defaults to dry-run, refuses dirty/conflicting targets, protects managed hashes, and binds an explicit VEMO_SKILLS home byte-identically without validation markers.
- PASS [Product] solo/team/regulated profile schemas and standards mappings validated; documentation states readiness is not certification.
- PASS [Portability] Windows launcher, UTF-8 Chinese paths, Git worktree `.git` files, nested repositories, PATH installation, cross-process locks, and audit recovery passed.
- PASS [Build] 15 Fleet unit tests passed; full VEMO conformance passed 84/84; selfcheck passed; VEMO_SKILLS passed 13/13 at 10.00/10.
- PASS [Evidence] machine receipt recorded build_exit=0 and smoke_exit=0 in the evidence log above.

## Conclusion
Outcome: accepted | Decision: stop | Key Evidence: VEMO 84/84, VEMO_SKILLS 13/13 at 10/10, machine receipt 0/0, live registry 12/12 unique, audit chain valid | Risk: low | Next Action: review per-project dry-run plans before any project adoption.
