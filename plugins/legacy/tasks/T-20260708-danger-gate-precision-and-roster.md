---
# ── Machine-readable state (hooks & CI parse THIS; keep it accurate) ──
id: T-20260708-danger-gate-precision-and-roster
risk: R2                        # touches enforcement/hooks + validators + vemo.config.yaml
state: AcceptancePassed         # PlanCreated|ReviewApproved|ImplementationDone|AcceptancePassed|ProcedureCompleted|Archived
scope_in:
  - "enforcement/hooks/run.py"
  - "enforcement/validators/skill_check.py"
  - "enforcement/validators/task_state.py"
  - "eval/run.py"
  - "bin/vemo"
  - "vemo.config.yaml"
  - "VERSION"
  - "CHANGELOG.md"
  - "README.md"
  - "docs/html/**"
  - "tasks/T-20260708-danger-gate-precision-and-roster.md"
  - ".vemo/judge.jsonl"
scope_out:
  - "the DESTRUCTIVE pattern set + all other guards (unchanged — only what they match against changes)"
  - "the verdict engine's gate logic (only context_brief gains one additive read-only line)"
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260708-danger-gate-precision-and-roster-20260708-162946.log"
judge:
  required: true                # R2 + capability.tier=high -> 2 independent judge passes; this LOOSENS a gate
  verdict: pass
approved_commands: []
owning_chat: local-improvement
heartbeat: 2026-07-08T13:00
---

# Danger-gate data-region precision + skill roster (ports from Wildmeerkat v2.16/2.17)

## Goal
Fix a confirmed false-positive in the command guard (a dangerous command merely QUOTED in a file the
agent is writing was hard-blocked) WITHOUT weakening real enforcement, and give the agent visibility of
which skills exist at session start.

## Scope (In / Out)
- In: `strip_data_regions` in `guard_command`; a `roster` in `skill_check.py` + `vemo skill-roster` +
  one context-brief line; eval checks; the version/docs the release obliges.
- Out: the DESTRUCTIVE pattern set and every other guard stay as-is (only the *string matched against*
  changes); the verdict engine's gate logic is untouched bar one additive read-only brief line.

## Pass/Fail Criteria  (EARS-style, measurable)
- [Fix] WHEN a dangerous command appears only as an `echo`/`printf` literal argument (segment with no
  command substitution and no redirect), the command guard SHALL NOT block (exit 0).
- [No regression / zero new missed blocks] WHEN a dangerous command is actually executed (bare, in an
  `&&`/`;` segment, via `$()`, in an unquoted heredoc), OR a redirect writes out-of-repo / into `.git/`,
  the guard SHALL still block (exit 2). Proven by `run.py --selftest` (two-way) + hook e2e checks.
- [Fail-safe] WHEN `strip_data_regions` errors, it SHALL return the raw command (block more, never less).
- [Additive] `python3 eval/run.py` SHALL be 79/79 (71 + 8 new); `vemo selfcheck` SHALL stay OK (no new
  config key); the verdict engine's gate outcomes SHALL be unchanged.
- [Roster] `vemo skill-roster` SHALL list the on-disk skills; the `vemo context` brief SHALL stay <=20 lines.

## Plan
- Port `strip_data_regions` into `run.py`; match DESTRUCTIVE + redirect checks against the stripped
  string; keep echo/printf segments that carry a redirect (VEMO matches redirect targets).
- Add a two-way hermetic `run.py --selftest` + hook e2e checks (data-region allow-cases +
  block-cases: heredoc/comment/backslash/cross-line-quote/bare-& carriers) + a roster check
  (8 new eval checks: 7 hook + 1 skill).
- Add `roster` to `skill_check.py` + `vemo skill-roster` + one context-brief line (guarded on `skill/`).

## Execution Log
- 2026-07-08: added strip_data_regions (echo/printf literal args only) + two-way selftest; live-fire: echoed
  dangers no longer block; real commands, out-of-repo, .git tamper, and all heredoc `<<` / comment `#`
  look-alikes still exit 2.
- 2026-07-08: added skill roster (CLI + context brief); eval 71 -> 79/79; selfcheck OK.
- 2026-07-08: adversarial review found + fixed 5 bypasses — 3 heredoc + 1 cross-line-quote comment
  (removed heredoc AND comment stripping), + 1 missing bare-`&` background separator in the echo strip
  (added). Only the echo/printf strip with the full bash separator set is kept (structurally miss-safe).
- 2026-07-08: bumped 1.3.0 -> 1.4.0 + regenerated docs/html; `vemo verify` receipt; 2 independent
  governance-judge passes recorded in `.vemo/judge.jsonl` before merge (see Acceptance Result).

## Acceptance Result
- [Fix] PASS — echoed danger `echo 'run git reset --hard'` exit 0; real command still exit 2.
- [No regression / zero new missed blocks] PASS — all 5 review carriers (heredoc x3 / cross-line-quote
  comment / bare-&) exit 2; safety judge ran 726 carrier combos, no bash-executing danger slips through.
- [Fail-safe] PASS — strip_data_regions returns raw command on exception.
- [Additive] PASS — eval 71 -> 79/79; DESTRUCTIVE + other guards byte-identical; selfcheck OK (no new key).
- [Roster] PASS — `vemo skill-roster` lists 7 skills; `vemo context` 9 lines (<=20).
- Judge: 2 independent passes (safety + additivity/docs lenses) in `.vemo/judge.jsonl`; required-judge +
  acceptance-before-push gates return ok.
- Note (out of scope, pre-existing): safety judge flagged DESTRUCTIVE-regex gaps unrelated to this change
  (`git push -f` short flag; `rm -r -f` split flags; `rm -rf ./rel`) — follow-up, not part of this task.

## Conclusion
Outcome: accepted · Decision: continue -> PR · Key Evidence: eval 79/79, selfcheck OK, receipt 0/0, 2 judge
passes, 726-combo safety sweep · Risk: R2 (gate loosened but proven miss-safe: only echo/printf literal args
blanked; heredoc/comment stripping removed) · Next Action: branch -> commit -> push -> PR (PR-only).
