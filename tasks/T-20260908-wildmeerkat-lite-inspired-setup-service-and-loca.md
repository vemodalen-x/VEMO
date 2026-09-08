---
id: T-20260908-wildmeerkat-lite-inspired-setup-service-and-loca
risk: R2
change_class: security
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_product.py", "bin/vemo_fleet.py", "bin/vemo_setup/**", "ui/**", "tests/test_setup*", "tests/test_fleet.py", "tests/test_product.py", "tests/test_extensions.py", "eval/run.py", "enforcement/ci/pre-push", ".vemo/judge.jsonl", "README.md", "docs/INSTALL.md", "docs/USAGE.md", "docs/DESIGN_LITE.md", "docs/QUICKSTART.md", "docs/INDEX.md", "docs/GUIDE.html", "docs/html/**", "docs/build_html.py", "tasks/T-20260908-wildmeerkat*", ".vemo/reference/**", ".vemo/run/**"]
scope_out: []
trifecta: [private_data, untrusted_content]
verification:
  profile: full
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260908-wildmeerkat-lite-inspired-setup-service-and-loca-20260908T073218Z.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked: [".vemo/run/judge-correctness-rework-independent.json", ".vemo/run/judge-correctness-rework-rerun.json", ".vemo/run/judge-correctness-rework-negative-gate.json", ".vemo/run/judge-safety-rework-independent.json", ".vemo/run/setup-browser.json", ".vemo/run/deployed-isolation.json", "bin/vemo_setup/service.py:331", "enforcement/ci/pre-push:20"]
  confidence: high
approved_commands: []
owning_chat: "codex-vemo-lite-20260908"
heartbeat: 2026-09-08T07:33:13Z
---

# Wildmeerkat lite inspired setup service and local UI

## Goal
Learn from Wildmeerkat lite's separation of governance/runtime/installer, project isolation,
verified installation and recoverable lifecycle. Deliver a shared VEMO installation service,
Chinese local browser UI, and linked installation/usage/design documentation.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else.

## Pass/Fail Criteria
- [x] Correctness: WHEN previewing a Git project, SHALL list exact changes and conflicts without writing files.
- [x] Correctness: WHEN installing into a Unicode/space path, SHALL install a complete payload, merge owned entry points, and pass real CLI/guard checks.
- [x] Security: WHEN a destination is a symlink, user-owned conflict, stale preview or invalid HTTP origin/token, SHALL refuse without overwriting user data.
- [x] Correctness: WHEN install verification fails, SHALL restore prior files; WHEN uninstalling, SHALL preserve changed files and task/evidence records.
- [x] Security: WHEN the target contains unowned Python modules or site startup files, SHALL never import them during preview/install/check and SHALL preserve them on uninstall.
- [x] Quality: WHEN using the browser UI, SHALL complete preview/install/diagnose/uninstall with visible progress, errors and evidence.
- [x] Build: repository `bin/vemo verify --no-cache` SHALL pass the full eval and selfcheck; focused setup tests and real browser smoke SHALL pass.
- [x] Documentation: Chinese installation, usage and design pages SHALL match actual CLI/UI behavior and cite pinned reference commits.

## Plan
1. Inspect pinned reference source and installation documentation; record adopted principles and deliberate VEMO differences.
2. Extract a complete reusable payload catalog; implement preview/apply/check/uninstall with local manifest, hashes and transactional recovery.
3. Add stdlib loopback HTTP adapter and accessible Chinese wizard; expose `vemo ui` and `vemo setup` without a frontend build dependency.
4. Test lifecycle, conflict handling, request boundaries, Unicode paths and real installed commands; run browser smoke.
5. Update README, quickstart and generated documentation; run full repository verification and record evidence.

RiskTier: escalated from R1 to R2 during requested review: `enforcement/ci/pre-push` needs argv-safe
execution in the Unicode/space project paths the installer supports. Two independent verifier passes required.
The user's subsequent "code review and push" authorizes review, necessary repairs, commit and push;
this repair preserves the gate policy and corrects argument handling. No global machine configuration changes.
Existing accepted tasks are not taken over. Untracked VEMO_SKILLS is not modified or packaged.

## Execution Log
- 2026-09-08T05:59:31Z Task created by `vemo task create`.
- 2026-09-08T06:21:17Z Expanded documentation scope to docs/GUIDE.html so the visual quickstart and CLI table agree with the authorized UI installation flow. Risk remains R1.
- 2026-09-08T06:26:46Z Full verification found one stale conformance assertion: fleet onboarding was checked by searching a filename literal in vemo_fleet.py. Payload ownership now lives in the shared catalog; revise this assertion to inspect the actual resolved payload. Selfcheck passed; 124/125 conformance cases passed before this correction.
- 2026-09-08T06:29:28Z Delivered shared payload/setup services, Chinese browser wizard, launchers and three linked guides with offline HTML. Full verification passed (125/125, selfcheck=0); real Chrome install/check/uninstall and mobile/help smoke passed. Evidence recorded in Acceptance Result.
- 2026-09-08T07:04:02Z User requested code review and push. Continue same session/task; review and repair installer races, incomplete diagnostic checks and malformed recovery metadata before verification, commit and push to origin/main.
- 2026-09-08T07:13:40Z Review found deployed CI referenced an absent conformance runner. Include its dependency closure and place framework tests under eval/tests in consuming projects so governance checks do not discover application tests; extend scope to test_extensions.py for its relocated test-root resolution.
- 2026-09-08T07:18:03Z Risk escalated to R2: review reproduced the existing pre-push command-string splitting failure in paths with spaces. Repair uses an argv array without changing policy. The user explicitly requested review and push; required independent verifier depth is two fresh contexts. Scope includes pre-push and judge provenance.
- 2026-09-08T07:19:06Z R2 regression reproduced validator-error failures from whitespace splitting in pre-push; argv-array repair now executes the real validator and still blocks unaccepted tasks. Trifecta: target settings/backups may be private and target input is untrusted; setup traffic is authenticated loopback-only, with no off-machine project-content transport.
- 2026-09-08T07:20:15Z Review repairs complete. Full verify passes 125/125 with build/smoke=0; installed conformance passes 125/125 independently of application tests; browser smoke passes. Prepare the final staged snapshot for two R2 verifier contexts before authorized commit/push.
- 2026-09-08T07:31:52Z Independent safety review reproduced unowned Python import execution during diagnostics (FAIL recorded). Rework isolates verified runtime snapshots and Python startup/import paths, adds poisoned-module regression, then requires a fresh full receipt and two new independent passes.
- 2026-09-08T07:33:13Z Import-isolation rework passes fresh full verify (125/125; 61 unit tests), 23 setup tests and real Chrome browser smoke. Evidence .vemo/run/T-20260908-wildmeerkat-lite-inspired-setup-service-and-loca-20260908T073218Z.log. Prior safety FAIL disposition RCA-inline; two fresh independent passes required. Push preflight returns GitHub403: current account lacks origin write permission; prepare local commit after gates.

## Acceptance Result
- PASS: full `VEMO_SESSION=codex-vemo-lite-20260908 python3 bin/vemo verify --no-cache`, build=0,
  smoke=0, 125/125 conformance; executed receipt `.vemo/run/receipt.json`, log referenced above.
- PASS: 23 setup lifecycle/HTTP tests; repository unit suite (61 tests) included in the full conformance run.
- PASS: real Chrome 139 browser smoke with Playwright 1.48.2 / Node 18, command
  `VEMO_PLAYWRIGHT_MODULE=$PWD/.vemo/run/browser/node_modules/playwright node tests/test_setup_browser.cjs`.
  Evidence `.vemo/run/setup-browser.json`; screenshots `.vemo/run/setup-desktop.png`,
  `.vemo/run/setup-installed.png`, `.vemo/run/setup-mobile.png`.
- PASS: Unicode install, actual installed guard rejection, idempotence, upgrade, original-file restore,
  modified-file preservation, malformed config, stale previews, symlinks, recovery and non-payload journal rejection.
- PASS: generated 28 documentation pages plus index and 3 offline UI help pages; new Markdown local links,
  JS syntax, `git diff --check`, and changed paths' scope checks passed.
- Disposition of first full-run failure: RCA-inline. Replaced source-literal assertion with actual fleet
  payload resolution and expanded coverage to composition dependencies; full suite rerun passed.
- Verification boundary: Linux/Python 3.12/Bash/Chrome executed. Windows/macOS launchers are supplied but
  not validated on those operating systems; no bundled interpreter, signed installer or remote CI setup claimed.

## Read Audit
- Local: root AGENTS, safety/concurrency/task/coding/verify/capability specs, task lifecycle CLI,
  product start/report and fleet source inventory, hook registration/install script, conformance assertions,
  documentation builder and docs-sync skill.
- Reference: Wildmeerkat lite `ea69176306d3e87d3c2200adba6ed3d9a1c4762e` README/master spec,
  deployment decision and bootstrap; docs `e3f2f4bef0530045e1e776e96e80c8663b1baa70`
  getting-started/maintenance. Reference instructions were treated as research material for that framework.
- Reusable lesson: validate the resolved deployment inventory and installed runtime, not a filename literal
  in its old owner. Separating an installer must preserve a single distribution contract and real verification.

## Requested Code Review
- Fixed P1: uninstall rechecks snapshots immediately before each restore/removal; edits arriving after
  preflight are preserved and prior removals roll back. Regression reproduced failure before the fix.
- Fixed P1: deploy the CI conformance runner and its test/docs/resource dependency closure. Framework
  tests live in eval/tests, isolated from application tests. Deployed docs-preset project with an intentionally
  failing application test passes 125/125 framework conformance (`.vemo/run/deployed-ci-review.log`).
- Fixed P1: reject incomplete installation manifests before executing runtime code; enforce required
  file inventory, valid hashes, profile/preset and backup schemas.
- Fixed P2: detect missing Claude event bindings and CI files; test the actual python3 command used
  by hooks instead of assuming the UI interpreter proves hook readiness.
- Fixed P2: validate every recovery journal row, including after_hash, before restoring any file.
- Fixed P2: maintenance Enter now starts diagnostics, verified by the browser smoke.
- Fixed P1: preserve whitespace/Unicode paths in the pre-push validator argv without changing policy;
  the installed real gate executes successfully and still blocks an unaccepted task.
- R2 safety review: file input/backups may contain private data and untrusted content. HTTP endpoints
  are authenticated loopback-only; no off-machine project-content transport is implemented.
- Fixed P1 (independent safety FAIL, RCA-inline): Python diagnostics execute hash-verified runtime snapshots with isolated interpreter startup/import paths; never import unowned target modules. The new regression covers root sitecustomize and bin/validator/package module shadows, install/check and preserved files after uninstall.
- User authorization: "code review and push" covers the review repairs and ordinary push to origin/main.
  Two independent judge records are required before commit/push; no force push or global config changes.

## Conclusion
Outcome: implementation and review repairs pass the declared Linux acceptance criteria.
Decision: deliver after two independent R2 judge passes and mechanical commit/push gates.
Key Evidence: 125/125 local and deployed conformance, full executed receipt, 61 unit tests and browser report.
Risk: Windows/macOS remain unverified; local HTTP/backup files are cooperative-host controls, not an OS sandbox.
Next Action: commit and ordinary push to origin/main as requested, then report the exact remote commit.
