---
id: T-20260818-vemo-skills-plugin-contract-adaptation
risk: R1
change_class: standard
state: AcceptancePassed
scope_in: ["VEMO_SKILLS/**", "tasks/T-20260818-vemo-skills-plugin-contract-adaptation*"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "cd VEMO_SKILLS && python3 bin/vemo-skills eval && python3 bin/vemo-skills author-selftest"
    lint: "cd VEMO_SKILLS && python3 bin/vemo-skills selfcheck"
    smoke: "cd VEMO_SKILLS && python3 bin/vemo-skills catalog"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260818-vemo-skills-plugin-contract-adaptation-20260818T102305Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: 2026-08-18T10:23:17Z
---

# VEMO_SKILLS plugin contract adaptation

## Goal
Adapt the standalone VEMO_SKILLS repository to the current skill contract and VEMO's declarative
everything-is-a-plugin architecture: standard source frontmatter, an explicit activation index, portable UI
metadata, index-driven binding, and executable compatibility checks. Preserve existing skill behavior and
cross-harness boundaries, then commit and push through each repository's permitted workflow.

## Scope (In / Out)
- In: `VEMO_SKILLS` skill metadata/bodies, activation index, checker/authoring/eval tools, public conventions,
  release metadata, tests/evidence, and its task record; this parent task record; local commits and authorized
  pushes for both repositories.
- Out: executable third-party plugin loading, personal/repo marketplace installation, plugin cache mutation,
  consumer `.claude/skills` artifacts, VEMO core/enforcement/spec changes, tags/releases, and direct pushes to
  the VEMO_SKILLS default branch.

## Pass/Fail Criteria
- [x] WHEN every registered `SKILL.md` is validated by the current official `quick_validate.py`, THEN all 30
  SHALL pass without the legacy `category` key or another unsupported frontmatter field.
- [x] WHEN the repository catalog is loaded, THEN `skills/index.json`, the filesystem skill tree, and both
  README catalogs SHALL contain the same 30 unique skill identities with safe local paths.
- [x] WHEN a consumer binds skills, THEN only index-activated skills SHALL be copied, with all bundled
  resources and `agents/openai.yaml` metadata preserved byte-for-byte.
- [x] WHEN UI metadata is inspected, THEN every registered skill SHALL have a quoted display name, 25–64
  character short description, and a default prompt explicitly naming `$<skill-name>`.
- [x] WHEN repository checks run, THEN selfcheck SHALL score at least 9.5/10, eval and author-selftest SHALL
  pass, a temporary bind SHALL contain 30 skills, and no generated validation markers SHALL be tracked.
- [x] WHEN changes are published, THEN VEMO_SKILLS SHALL be committed on a feature branch, pass PR checks, and
  merge without a direct push to `main`; the parent VEMO follow-up task SHALL reach AcceptancePassed before push.

## Plan
1. Establish the baseline with the repository checker and current official skill validator; record contract
   drift and preserve existing allowed-tool/license behavior where the executable validator supports it.
2. Add a bounded schema-v1 activation index and make catalog, bind, scoring, and eval consume it as their
   single registration surface; derive category from its normalized path rather than SKILL frontmatter.
3. Remove legacy category metadata, generate `agents/openai.yaml` with the official generator, and update the
   naming/publishing/authoring procedures plus bilingual public docs.
4. Stop tracking generated `.skill-validated.json` markers, make marker writes opt-in, bump release metadata,
   and add a task record explaining migration/compatibility boundaries.
5. Run all official per-skill validators, selfcheck/eval/author-selftest, temporary bind checks, parent VEMO
   verification and Git gates; review the diff, commit/push the feature branch, then commit/push the parent task.

## Execution Log
- 2026-08-18T09:13:21Z Task created by `vemo task create`.
- 2026-08-18T09:16:00Z Baseline: repository selfcheck reports 10/10, but the current official validator rejects
  representative skills because legacy `category` is unsupported; 30/30 skills lack `agents/openai.yaml`.
- 2026-08-18T09:29:00Z Code review resolved invalid-index partial binding, duplicate catalog-row masking, and
  duplicate flattened-name overwrite; regression eval now covers all three failure paths.
- 2026-08-18T09:29:00Z Official `quick_validate.py` passed 30/30; package/index/UI-metadata/catalog counts are
  30/30/30/30; selfcheck scored 10.00/10.0; eval passed 16/16; author-selftest passed 11/11.
- 2026-08-18T09:29:00Z VEMO_SKILLS commit `45e82bc` pushed to
  `origin/feat/plugin-contract-adaptation`; its protected default branch was not touched.
- 2026-08-18T09:29:36Z Parent focused verification passed uncached with test/lint/smoke exit 0; receipt
  `.vemo/run/receipt.json`, log `.vemo/run/T-20260818-vemo-skills-plugin-contract-adaptation-20260818T092935Z.log`.
- 2026-08-18T10:22:21Z VEMO_SKILLS PR #4 passed its `verify` check and was squash-merged to `main` as
  `5a73aad`; the merged tree exactly matches the previously verified feature tree. Local `main` was fast-forwarded
  to the same remote commit. PR: `https://github.com/vemodalen-x/VEMO_SKILLS/pull/4`.
- 2026-08-18T10:23:05Z Parent focused verification was rerun against merged VEMO_SKILLS `main`; uncached
  test/lint/smoke all exited 0.

## Acceptance Result
Passed and merged. The declarative source catalog is adapted without introducing a monolithic executable plugin runtime.

## Conclusion
VEMO_SKILLS now exposes explicit bounded activation, standard model/UI metadata separation, index-only binding,
and fail-closed ambiguity checks. Consumers retain installation, permissions, and adoption policy.
