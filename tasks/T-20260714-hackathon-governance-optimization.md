---
id: T-20260714-hackathon-governance-optimization
risk: R0
state: AcceptancePassed
scope_in:
  - "docs/HACKATHON_PLAYBOOK.md"
  - "docs/ADAPTERS.md"
  - "docs/INDEX.md"
  - "skill/hackathon-submission/**"
  - "skill/_catalog.md"
  - "README.md"
  - "CHANGELOG.md"
  - "tasks/T-20260714-hackathon-governance-optimization.md"
scope_out: ["specs/**", "enforcement/**", "vemo.config.yaml", "src/**", ".github/**"]
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260714-hackathon-governance-optimization-20260714-111627.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: 2026-07-14T11:12
---

# Hackathon-ready governance: OpenAI Build Week playbook + Codex adapter + submission skill

## Goal
Give a solo/small team a VEMO-native path to build and submit an OpenAI Build Week (Codex + GPT-5.6) entry:
a playbook mapping the official judging criteria to concrete practices, a verified Codex CLI ring-1 adapter
recipe (the contest mandates Codex; VEMO ships Claude Code hook wiring by default), and a thin submission-
readiness skill — without touching core enforcement mechanism.

## Scope (In / Out)
- In: `docs/HACKATHON_PLAYBOOK.md` (new), `docs/ADAPTERS.md` (add Codex CLI section), `docs/INDEX.md` +
  `README.md` (pointers), `skill/hackathon-submission/` (new skill), `skill/_catalog.md` (register),
  `CHANGELOG.md`.
- Out: `specs/**`, `enforcement/**`, `vemo.config.yaml`, `src/**`, `.github/**` — this is guidance +
  a thin skill, not a change to the mechanism itself.

## Pass/Fail Criteria (EARS-style)
- [Correctness] WHEN a reader opens `docs/HACKATHON_PLAYBOOK.md`, the doc SHALL enumerate all 4 official
  Devpost judging criteria and all hard submission requirements (demo video, Codex Session ID, README
  AI-usage section, public/testable repo, category selection).
- [Correctness] WHEN `skill/hackathon-submission/SKILL.md` is added, `vemo skill-audit` SHALL
  report it catalog-consistent (registered in `skill/_catalog.md`, frontmatter present).
- [Build] `python3 eval/run.py` SHALL exit 0 (no regression to the conformance harness).
- [Build] `python3 enforcement/validators/task_state.py selfcheck` SHALL exit 0.

## Plan
1. `docs/HACKATHON_PLAYBOOK.md` — rules digest, judging-criteria -> VEMO-practice map, task decomposition
   for a FE+BE+AI-core web app, submission-readiness checklist, pre-submission judge-lens review.
2. `docs/ADAPTERS.md` — add a verified Codex CLI ring-1 adapter section (hooks.json / config.toml schema,
   PreToolUse/PermissionRequest -> the existing dispatcher contract).
3. `skill/hackathon-submission/SKILL.md` — thin contract; register in `skill/_catalog.md`.
4. Wire `docs/INDEX.md` + `README.md` pointers + `CHANGELOG.md` entry.
5. `vemo verify`; mark AcceptancePassed.

## Execution Log
- 2026-07-14T10:30 task created; scope bootstrapped via Bash per the documented quickstart pattern (active
  task T-20260711 pc-fleet-governance's scope_in does not cover these paths).
- 2026-07-14T11:00 wrote docs/HACKATHON_PLAYBOOK.md, docs/ADAPTERS.md Codex CLI section,
  skill/hackathon-submission/SKILL.md (renamed from an initial gerund name to match this repo's
  noun/verb-noun skill-naming convention per enforcement/validators/skill_check.py), catalog + README/INDEX/
  CHANGELOG pointers.
- 2026-07-14T11:16 `python3 eval/run.py` -> 84/84 = 100%. `task_state.py selfcheck` -> OK.
  `vemo skill-audit`/`skill-score` -> 8/8 skills clean, 6/6 gating dims pass.
- 2026-07-14T11:16 `vemo verify` -> pass build_exit=0 smoke_exit=0,
  evidence=.vemo/run/T-20260714-hackathon-governance-optimization-20260714-111627.log,
  receipt=.vemo/run/receipt.json.

## Acceptance Result
- [Correctness] HACKATHON_PLAYBOOK.md enumerates the 4 criteria + all hard submission artifacts — PASS (§1, §3
  tables; §6 checklist).
- [Correctness] hackathon-submission skill registered + catalog-consistent — PASS (`vemo skill-audit`: 8
  skills, catalog<->disk consistent; `skill-score`: 6/6 gating dims).
- [Build] `python3 eval/run.py` exit 0 — PASS (84/84 = 100%, no regression from the pre-existing 84).
- [Build] `task_state.py selfcheck` exit 0 — PASS.
No FAILs; no disposition needed.

## Conclusion
Outcome: accepted · Decision: continue · Key Evidence:
`.vemo/run/T-20260714-hackathon-governance-optimization-20260714-111627.log`,
`.vemo/run/receipt.json`, `eval/out/report.json` (84/84) · Risk: low · Next Action: the user reviews
`docs/HACKATHON_PLAYBOOK.md` + the Codex CLI adapter section, decides whether `hackathon-submission` should
later graduate into VEMO_SKILLS for cross-project reuse (deferred per in-conversation discussion — the
7-day contest window does not fit VEMO_SKILLS' PR + Friday release-train cadence), then starts the actual
frontend/backend/AI-core project tasks per §5 of the playbook.
