---
id: T-20260910-merge-upstream-and-deliver-windows-supervision-i
risk: R2
change_class: release
state: AcceptancePassed
scope_in: ["AGENTS.md", ".github/**", ".gitignore", ".gitattributes", ".vemo/judge.jsonl", "CHANGELOG.md", "README.md", "agents/**", "bin/**", "docs/**", "enforcement/**", "eval/**", "extensions/**", "skill/**", "tasks/**", "tests/**", "ui/**", "packaging/**", "vemo.config.yaml"]
scope_out: []
trifecta: []
verification:
  profile: release
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260910-merge-upstream-and-deliver-windows-supervision-i-20260910T140833Z.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked:
    - ".vemo/run/T-20260910-merge-upstream-and-deliver-windows-supervision-i-20260910T140833Z.log"
    - "eval/out/report.json"
    - ".vemo/run/windows-package-final-smoke-2.json"
    - "packaging/windows/Install.ps1"
    - "enforcement/ci/pre-push"
  confidence: high
approved_commands: []
owning_chat: "codex-windows-supervision-20260910"
heartbeat: 2026-09-10T14:10:45Z
---

# Merge upstream and deliver Windows supervision installer

## Goal
Merge current upstream with the local gstack delivery loop, review integration, deliver a Windows installation package, and verify local supervision without changing unrelated projects.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else.

## Pass/Fail Criteria
- [ ] Full framework tests, conformance, selfcheck and release scan exit zero.
- [ ] Workflow, platform and extension CLI entries survive the merge.
- [ ] Windows package builds, installs in a user-owned location and passes runtime integrity checks.
- [ ] A throwaway Windows Git project demonstrates installation, blocked unplanned commit, idempotency and uninstall.
- [ ] Two independent judges approve the final scoped snapshot before push.

## Plan
1. Merge origin/main in an isolated worktree, retaining local delivery-loop functionality.
2. Review Windows runtime, packaging and transactional setup; fix defects and add regression tests.
3. Build a user-level package, install on this PC, and verify the real Git guard behavior in a disposable project.
4. Run release verification and independent judges, commit the reviewed merge and push the release branch.

## Authorization
The user requested merge, review, commit and installation on this machine; earlier requests authorize push. User-level package installation may write to the selected local application directory and launcher/shortcut locations. Do not enable auto mode, replace global Git hooks, overwrite unrelated project changes, or claim a Codex pre-tool adapter is installed when only Git gates are available.

## Execution Log
- 2026-09-10T13:43:27Z Task created by `vemo task create`.
- 2026-09-10T14:10:45Z Release acceptance evidence passed: conformance 133/133; release receipt build/smoke/package_scan exit 0; package integrity, browser UI, Windows Git gate, idempotency and uninstall smoke passed.

## Acceptance Result
PASS: full conformance 133/133, selfcheck, release receipt build/smoke/package scan, package checksum
scan, browser installation smoke, Unicode-path install, idempotency, real Git plan-before-commit block,
and uninstall preservation all passed. The Windows ZIP is unsigned and user-level; CI branch protection
and host pre-tool adapter activation remain deployment responsibilities.

## Conclusion
Outcome: accepted | Decision: publish | Key Evidence: release receipt, package smoke, and conformance
report | Risk: R2 release changes reviewed with two independent lenses | Next Action: commit and push.
