---
# ── Machine-readable state (hooks & CI parse THIS; keep it accurate) ──
id: T-20260709-destructive-gate-hardening
risk: R2                        # touches enforcement/hooks/run.py + vemo.config.yaml
state: AcceptancePassed         # PlanCreated|ReviewApproved|ImplementationDone|AcceptancePassed|ProcedureCompleted|Archived
scope_in:
  - "enforcement/hooks/run.py"
  - "eval/run.py"
  - "VERSION"
  - "vemo.config.yaml"
  - "CHANGELOG.md"
  - "README.md"
  - "docs/html/**"
  - "tasks/T-20260709-destructive-gate-hardening.md"
  - ".vemo/judge.jsonl"
scope_out:
  - "strip_data_regions + guard_command control flow (unchanged); only the DESTRUCTIVE rm/push patterns broadened"
  - "all other guards + the verdict engine task_state.py (untouched)"
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260709-destructive-gate-hardening-20260709-132926.log"
judge:
  required: true                # R2 + capability.tier=high -> 2 independent judge passes
  verdict: pass
approved_commands: []
owning_chat: local-improvement
heartbeat: 2026-07-09T13:31
---

# DESTRUCTIVE-gate flag/target coverage hardening + version realignment (v1.9.0)

## Goal
Close pre-existing DESTRUCTIVE-regex gaps (adversarial judges found them) — `git push` force in any
short-flag position (`-f`/`-fu`/`-vf`), `rm` split/long/capital-`R` recursive-force flags, `rm`
`./relative` targets — tightening only, no over-block; and
realign the VERSION line onto the public `v1.8.0` tag baseline as `v1.9.0`.

## Scope (In / Out)
- In: the two broadened DESTRUCTIVE patterns (rm, git push), a two-way selftest + 4 hook e2e checks, and
  the version/docs the release obliges.
- Out: `strip_data_regions` / `guard_command` flow, every other guard, and the verdict engine — unchanged.

## Pass/Fail Criteria  (EARS-style)
- [Coverage] WHEN a recursive-force `rm` (`-rf`/`-Rf`/`-fr`/`-r -f`/`--recursive --force`, ANY target incl. `./x`)
  or a `git push` with force in any short-flag position (`-f`/`-fu`/`-vf`) or `--force` runs, the guard SHALL block (exit 2).
- [No over-block] WHEN `--force-with-lease`/`--force-if-includes`, a plain `git push` (incl. `-u`/`-v` without
  force), a non-recursive `rm`, or a recursive `rm` WITHOUT force runs, the guard SHALL allow (exit 0).
- [Additive] `python3 eval/run.py` SHALL be 83/83; DESTRUCTIVE only broadened (never narrowed); all other
  guards + `strip_data_regions` byte-identical; `selfcheck` OK.
- [Unified] VERSION == vemo.config.yaml version == README badge == CHANGELOG top == (post-merge) tag = 1.9.0.

## Plan
- Broaden the `rm` pattern to two segment-scoped lookaheads (has-recursive incl. `-R` AND has-force, any
  target) and `git push` to catch force in any short-flag position; add a two-way `run.py --selftest` +
  4 hook e2e conformance checks.
- Realign VERSION 1.4.0 -> 1.9.0 (above the `v1.8.0` public tag) + a CHANGELOG `[1.9.0]` note; regen docs/html.

## Execution Log
- 2026-07-09: broadened DESTRUCTIVE `rm` + `git push`; selftest two-way (4 new-coverage + 4 no-over-block
  asserts); live-fire 12/12; eval 79 -> 83/83; selfcheck OK.
- 2026-07-09: final adversarial judges closed two more in-category gaps — capital `-R` (rm) and force in
  any short-flag position (`git push -fu`/`-fvn`); patterns now positionally complete. Re-verified 83/83;
  selftest + live-fire cover these (and keep `rm -R` no-force / `git push -u`/`-v` allowed); ReDoS-linear.
- 2026-07-09: realigned VERSION 1.4.0 -> 1.9.0 onto the `v1.8.0` baseline + CHANGELOG `[1.9.0]`; regen docs.
- 2026-07-09: `vemo verify` receipt; 2 independent governance-judge passes recorded in `.vemo/judge.jsonl`
  before merge (see Acceptance Result).

## Acceptance Result
- [Coverage] PASS — force+recursive caught in ANY flag position; live-fire blocks rm `-rf`/`-fr`/`-Rf`/`-fR`/
  `-r -f`/`--recursive --force` (targets `/ ~ ./x`) and git push `-f`/`-fu`/`-uf`/`-vf`/`-fvn`/`--force` (all exit 2).
- [No over-block] PASS — rm `-R`/`-r` no-force, `rm file`, git push `-u`/`-v`/`--force-with-lease`/`--force-if-includes`,
  refspec `feature-fix`, and non-rm `grep -Rf`/`tar -rf`/`chmod -R`/`docker rm -f` + substrings all exit 0.
- [Additive] PASS — eval 79 -> 83/83 (add-only, non-vacuous: reverting the regexes drops it to 79); DESTRUCTIVE
  only broadened; `strip_data_regions`/`guard_command`/other guards + `task_state.py` byte-identical; selfcheck OK (no new key).
- [Unified] PASS — VERSION == config == README badge == CHANGELOG top == 1.9.0; docs/html regenerated (no stale current); tag v1.9.0 post-merge.
- Judge: 2 independent passes (final completeness/safety + additivity/docs/version lenses) in `.vemo/judge.jsonl`;
  ReDoS-linear (single-star, <0.1ms/4k). `vemo verify` receipt build_exit=0 smoke_exit=0.

## Conclusion
Outcome: accepted · Decision: continue -> PR · Key Evidence: eval 83/83, selfcheck OK, receipt 0/0, 2 judge passes,
positional-completeness sweep (no bypass / no over-block / no narrowing / no ReDoS) · Risk: R2 (tightens the gate —
safe direction, proven by the selftest's negative asserts) · Next: branch release/v1.9.0 -> commit -> push -> PR -> tag v1.9.0.
