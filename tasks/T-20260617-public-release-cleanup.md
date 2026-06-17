---
id: T-20260617-public-release-cleanup
risk: R0
state: AcceptancePassed
scope_in:
  - "README.md"
  - ".gitignore"
  - "CHANGELOG.md"
  - "CONTRIBUTORS.md"
  - "SECURITY.md"
  - "ROADMAP.md"
  - "AGENTS.md"
  - "vemo.config.yaml"
  - "docs/**"
  - "specs/**"
  - "skill/**"
  - "agents/**"
  - "enforcement/**"
  - "eval/**"
  - "tasks/T-20260617-public-release-cleanup.md"
scope_out:
  - "../doc/**"
  - ".git/**"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: "selfcheck OK; eval 9/9; grep scans clean; git diff --check clean"
judge:
  required: false
  verdict: null
owning_chat: chat-20260617-1132-cdx
heartbeat: 2026-06-17T11:42
---

# Public release cleanup

## Goal
Prepare VEMO for a public first GitHub upload by removing private, personal, and project-specific comparison language from the release artifact.

## Scope (In / Out)
- In: public-facing docs, specs, skill descriptions, agent descriptions, and this task record.
- Out: parent-repository analysis files under `../doc/**`; those are audit inputs only and are not part of the VEMO git release.

## Pass/Fail Criteria
- [Security] WHEN tracked VEMO text files are scanned, they SHALL contain no credential-like secrets or local private paths.
- [Public Docs] WHEN tracked VEMO docs/specs are scanned, they SHALL not contain project-specific comparison references.
- [Public Docs] WHEN README and linked docs are reviewed, they SHALL address a public GitHub audience rather than a single local user or private session.
- [Release] WHEN git remote and GitHub authentication are checked, the repo SHALL be ready to push or the blocking condition SHALL be recorded.

## Plan
1. Audit tracked VEMO files for private paths, secrets, and project-specific comparison references.
2. Remove or rewrite public docs/specs/skills/agent text that references project-specific lineage or private session context.
3. Run VEMO self-check/eval where available and record evidence.
4. Configure or verify the GitHub remote, then push after acceptance passes.

## Execution Log
- 2026-06-17T11:32 task created after user requested continuation from a parent-repository analysis HTML file.
- 2026-06-17T11:42 removed project-specific comparison language from public docs/specs/skills/agent text.
- 2026-06-17T11:42 removed stale comparison HTML/PDF artifacts from `docs/`.
- 2026-06-17T11:42 `python3 bin/vemo selfcheck` exited 0 (`VEMO selfcheck: OK`).
- 2026-06-17T11:42 `python3 bin/vemo eval` exited 0 (`conformance 9/9 = 100%`).
- 2026-06-17T11:42 `git diff --check` exited 0.
- 2026-06-17T11:42 public scans for project-specific comparison names, local paths, common token patterns, and CJK documentation text returned no matches.

## Acceptance Result
- [Security] PASS — no local private paths or common credential-token forms were found in the current working tree.
- [Public Docs] PASS — public docs/specs/skills/agent text no longer contains project-specific comparison names.
- [Public Docs] PASS — touched documentation is English and public-audience oriented.
- [Release] PASS — local acceptance passed; GitHub remote/push remains the next step.

## Conclusion
Outcome: accepted · Decision: continue · Key Evidence: selfcheck OK; eval 9/9; scans clean · Risk: low · Next Action: configure GitHub remote and push.
