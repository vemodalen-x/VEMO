---
id: T-20260909-ignore-nested-vemo-skills-repository
risk: R2
change_class: ci-narrow
state: AcceptancePassed
scope_in: [".gitignore", "tasks/T-*-ignore-nested-vemo-skills*", ".vemo/judge.jsonl", ".vemo/run/**"]
scope_out: []
trifecta: []
verification:
  profile: full
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260909-ignore-nested-vemo-skills-repository-20260909T024423Z.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked: [".gitignore:1-21", ".vemo/judge.jsonl:67", ".vemo/run/T-20260909-ignore-nested-vemo-skills-repository-20260909T024423Z.log", "git check-ignore -v $(git ls-files) = 0 hits/162 tracked", "git -C VEMO_SKILLS remote -v = github.com/vemodalen-x/VEMO_SKILLS @ 5a73aad, 0 modified"]
  confidence: high
approved_commands: []
owning_chat: "358118fc-0f6d-4c4e-bbbd-c037c38b13aa"
heartbeat: 2026-09-09T02:51:24Z
---

# Ignore nested VEMO_SKILLS repository

## Goal
`VEMO_SKILLS/` is a separate repository (`github.com/vemodalen-x/VEMO_SKILLS`, own `.git`, own
branches and release flow) that happens to sit inside this working tree. Staging it produces a bare
gitlink (`mode 160000`) with no `.gitmodules`, so a clone of VEMO gets an empty directory it cannot
populate. Ignore the path so the main repository never records that broken reference and
`git status` stays clean.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else. VEMO_SKILLS' own contents and history are not modified.

## Pass/Fail Criteria
- [x] Correctness: WHEN `VEMO_SKILLS/` is present on disk, `git status --porcelain` SHALL report nothing for it.
- [x] Correctness: WHEN `git add VEMO_SKILLS/` is attempted, git SHALL refuse without `-f` and the index SHALL contain no `160000` entry.
- [x] Safety: the ignore rule SHALL match only `VEMO_SKILLS/` and SHALL NOT hide any currently tracked file — `git ls-files` output SHALL be byte-identical before and after.
- [x] Safety: VEMO_SKILLS' own repository (111 tracked files, its `.git`, its branches) SHALL remain untouched on disk.
- [x] Build: `bin/vemo verify --no-cache` SHALL pass with build_exit=0 and smoke_exit=0.

## Plan
1. Append a commented `VEMO_SKILLS/` rule to `.gitignore`, alongside the existing runtime/editor rules.
2. Verify `git check-ignore`, a forced-add negative test, and `git ls-files` invariance.
3. Run full verification; obtain two independent judge passes (R2 at capability.tier=high).

RiskTier: `.gitignore` is R2 because an ignore rule can remove files from the governed surface.
This change adds exactly one path that is a foreign repository, never a VEMO source file; the
`git ls-files` invariance criterion is the mechanical check that nothing tracked was hidden.

## Execution Log
- 2026-09-09T02:43:26Z Task created by `vemo task create`.
- 2026-09-09T02:44:10Z Diagnosis of the reported commit failure: `git add VEMO_SKILLS/` warns "adding embedded git repository" and stages a `160000` gitlink with no `.gitmodules`. A commit does succeed mechanically, so the failure surfaces later as an unusable reference for anyone cloning VEMO. Reproduced and reverted (`reset --soft` + `rm --cached`); all 311 VEMO_SKILLS files verified intact. User chose the ignore approach over submodule registration.

## Acceptance Result
- PASS: `git status --porcelain | grep VEMO_SKILLS` returns nothing; `git check-ignore -v VEMO_SKILLS/README.md`
  attributes the match to `.gitignore:21:VEMO_SKILLS/`.
- PASS: `git add VEMO_SKILLS/` exits 1 ("paths are ignored by one of your .gitignore files"); `git ls-files --stage`
  contains no `160000` entry.
- PASS: `git ls-files` (162 entries) is byte-identical before and after the rule — `diff` exits 0. No tracked
  file was removed from the governed surface.
- PASS: VEMO_SKILLS still holds 111 tracked files (311 counting `.git` internals), its own HEAD `5a73aad`,
  and a clean working tree (0 modified).
- PASS: full `python3 bin/vemo verify --no-cache`, build_exit=0, smoke_exit=0, receipt `.vemo/run/receipt.json`,
  log `.vemo/run/T-20260909-ignore-nested-vemo-skills-repository-20260909T024423Z.log`.
- Verification boundary: the rule is verified against the current tree only. If VEMO_SKILLS is ever intended to
  ship as part of VEMO, this ignore must be revisited — registering it as a real submodule is the alternative
  the user considered and declined.

## Conclusion
Outcome: the main repository no longer records a gitlink it cannot resolve, and `git status` is clean.
Decision: deliver after two independent R2 judge passes and the mechanical commit/push gates.
Key Evidence: forced-add negative test, `git ls-files` invariance, full verify receipt (build=0 smoke=0).
Risk: an ignore rule is a governed-surface reduction by nature; scoped to one foreign repository path and
checked by the ls-files invariance criterion.
