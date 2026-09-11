---
id: T-20260910-reject-empty-judge-snapshots
risk: R2
change_class: security
state: ProcedureCompleted
scope_in: ["enforcement/validators/task_state.py", "enforcement/ci/pre-push", "enforcement/ci/vemo-ci.yml", ".github/workflows/vemo-ci.yml", "tests/test_judge_snapshot.py", "eval/run.py", "tasks/T-*-reject-empty-judge-snapshots*", ".vemo/judge.jsonl", ".vemo/run/**", "CHANGELOG.md"]
scope_out: []
trifecta: []
verification:
  profile: full
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T101527Z.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked: ["tests/test_judge_snapshot.py:1", "eval/run.py:796", "enforcement/validators/task_state.py:573", "enforcement/ci/pre-push:49", "enforcement/ci/vemo-ci.yml:29", ".github/workflows/vemo-ci.yml:29", ".vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T101527Z.log", "/tmp/vemo-judge-ambiguous.PBtAey"]
  confidence: high
approved_commands: []
owning_chat: "01a08a59-6840-7711-a261-141d3e0007ee"
heartbeat: 2026-09-10T10:15:16Z
---

# Reject empty judge snapshots

## Goal
`_judge_snapshot` binds a judge verdict to the patch the judge actually reviewed. When the in-scope
diff was empty it hashed nothing and returned `sha256("")` =
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — a valid-looking digest that
**every** empty diff reproduces. Two consequences, both live:

1. **The gate could be satisfied by nothing.** A judge invoked with an empty index recorded a `pass`
   bound to no code, and `_judge_gate_result` accepted it. 12 of the 68 rows in `.vemo/judge.jsonl`
   carry this hash.
2. **Local and CI disagreed about the same commit.** Locally the index is empty right after a
   commit, so the snapshot was `e3b0c442…`; CI recomputes with `VEMO_DIFF_RANGE=<before>...HEAD` and
   got the real content hash (`6cc45467…` for `005dba5...c814483`). The local pre-push gate went
   green while the identical CI check failed — the observed `✗ 0 / 1` on both pushed commits.

Make an empty in-scope diff unusable as evidence, so a verdict either binds to reviewed code or does
not count.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else. The 12 pre-existing empty-hash rows are NOT rewritten — `.vemo/judge.jsonl`
  is append-only. They are rejected on read instead.

## Pass/Fail Criteria
- [x] Correctness: WHEN the in-scope diff is empty, `_judge_snapshot` SHALL return the sentinel
      `EMPTY_SNAPSHOT` and SHALL NOT return `sha256("")`.
- [x] Correctness: WHEN the in-scope diff is empty, `judge_record(..., "pass")` SHALL refuse, exit
      non-zero, and write NO row to the append-only log.
- [x] Correctness: a `fail` verdict SHALL still be recordable with no staged diff — a judge may fail
      a task precisely because the change is absent.
- [x] Correctness: `_judge_gate_result` SHALL block with `judge-snapshot-unbound` when no in-scope
      change is resolvable, and SHALL NOT count rows carrying `EMPTY_SNAPSHOT`, the legacy
      `sha256("")`, a range sentinel, or no snapshot at all toward the required pass count.
- [x] Correctness: staged mode and `VEMO_DIFF_RANGE` mode SHALL produce the SAME snapshot for the
      same content — the local/CI divergence that caused this bug.
- [x] Safety: a genuine pass bound to the staged diff SHALL still open the gate (no over-block).
- [x] Regression: the new tests SHALL fail if the fix is reverted (negative-tested, not tautological).
- [x] Build: `bin/vemo verify --no-cache` SHALL pass with build_exit=0 and smoke_exit=0.
- [x] Correctness: a snapshot that is NOT a 64-hex content digest — `unresolved-range`,
      `invalid-range`, `""`, or a missing key — SHALL NOT bind a verdict, at write time AND at gate
      time. Sentinels are self-matching, so equality alone cannot reject them.
- [x] Correctness: `enforcement/ci/pre-push` SHALL hand the pushed range to the validator, so the
      local push gate and CI evaluate the SAME diff. WHEN the range is withheld the gate SHALL
      report `judge-snapshot-unbound`; WHEN supplied it SHALL report a real pass count.
- [x] Correctness: WHEN Git supplies the current push range on stdin, it SHALL override an inherited
      `VEMO_DIFF_RANGE`, so passes for an older reviewed range cannot authorize a newer push.
- [x] Safety: WHEN a push updates more than one non-deletion ref, `pre-push` SHALL fail closed with
      `multi-ref-push-unsupported`, because one scalar snapshot cannot bind several independent ranges.
- [x] Safety: WHEN a new branch has one known target-remote boundary, `pre-push` SHALL snapshot every
      outgoing commit; WHEN the boundary is missing or ambiguous, it SHALL fail closed rather than review tip only.
- [x] Safety: WHEN an existing ref update is non-fast-forward, local and push-event CI SHALL snapshot
      the exact remote-to-local tree transition with two-dot ranges, including remote-only deletions.
- [x] Regression: the push-gate behavior SHALL be covered by an EXECUTED conformance scenario (a
      grep of the script cannot see a local/CI divergence).

## Plan
Superseded plan (round 1, kept for provenance): blacklist the empty-diff hash via `EMPTY_SNAPSHOT` /
`LEGACY_EMPTY_SNAPSHOT` sentinels. An independent judge showed a blacklist cannot hold — see the
Execution Log — so the delivered design is below.

1. Return `EMPTY_SNAPSHOT` from `_judge_snapshot` when no in-scope path remains, so "the judge saw
   nothing" is a distinguishable value rather than a plausible-looking digest.
2. Decide binding with a WHITELIST, `_binds_to_content`: only a 64-hex digest that is not the digest
   of an empty diff binds a verdict. This covers the empty sentinel, `unresolved-range`,
   `invalid-range`, a git failure (`""`), and legacy rows with no `snapshot` key, and it cannot be
   reopened by adding a new sentinel later.
3. Block in `_judge_gate_result` on any non-binding current snapshot (`judge-snapshot-unbound`), and
   count only rows whose snapshot equals that proven-binding digest.
4. Refuse at write time in `judge_record` for any `pass` that cannot bind, with a non-zero CLI exit,
   so the judge learns its context is wrong while it can still fix it rather than appending noise.
   `fail` stays recordable — a judge may fail a task precisely because the change is absent.
5. Export the derived push range from `enforcement/ci/pre-push` so the local gate and CI evaluate the
   same diff instead of the local one falling back to an empty index. Treat Git's stdin as authoritative
   when present, overriding ambient range state; preserve the environment range only for stdin-free CI.
   Reject multiple non-deletion ref updates rather than silently binding the whole push to only the first.
   For a new branch, derive the full outgoing range from one known target-remote boundary and reject an
   unresolved or ambiguous boundary rather than substituting `tip~1...tip`. For existing refs, use
   `remote..local` locally and `before..HEAD` in push-event CI; keep PR comparison on merge-base triple-dot.
6. Cover with `tests/test_judge_snapshot.py` plus an EXECUTED push-gate conformance scenario;
   negative-test every claim by reverting the corresponding code and confirming failures.

RiskTier: R2 / `change_class: security` because these files ARE the gate engine and the push gate — a
defect here decides whether unreviewed code can ship. The binding rule becomes stricter for empty,
invalid, stale, and ambiguous evidence; range propagation also restores a valid pass when the current
single-ref push matches real review records. The invariant is narrower and testable: no unreviewed diff
is authorized. Repairing six conformance scenarios by giving them real reviewable diffs, rather than
by relaxing the rule, keeps the depth requirements they were written to prove.

## Execution Log
- 2026-09-10T05:17:26Z Task created by `vemo task create`.
- 2026-09-10 Diagnosed the CI `✗ 0 / 1` on `c814483` and `005dba5`. Failing step: "Governance
  backstop on the change range"; message `✗ required judge: judge-pass-count=0 (requires 1
  contiguous pass record(s))`. Reproduced verbatim with
  `VEMO_DIFF_RANGE="005dba5...HEAD" bash enforcement/ci/pre-commit` (exit 1). Confirmed the
  staged-mode snapshot `e3b0c442…` is exactly `hashlib.sha256(b"").hexdigest()`, while range mode
  computed `6cc45467…`. CI has been red since 2026-08-18, not only on these commits — pre-existing
  and systemic, not introduced by this session's pushes.
- 2026-09-10 Implemented the 5 plan steps. Added `tests/test_judge_snapshot.py` (9 tests) — the
  regression coverage whose absence let this survive.
- 2026-09-10 Negative test: removed `if not paths: return EMPTY_SNAPSHOT`; 4 tests failed showing the
  `e3b0c442…` hash. Restored the fix; suite green again. The tests are load-bearing.
- 2026-09-10 Correction to an earlier report in this session: the claim that the wildmeerkat task had
  "two independent judge passes and all gates green" was WRONG. Those local gates were opened by an
  empty snapshot, not by a real match. Recorded here because the erroneous claim was already
  delivered to the user.
- 2026-09-10 **Independent judge recorded FAIL** (`judge-correctness-20260910`, snapshot `d4de023c…`).
  Three findings reproduced and confirmed by the implementer before acting:
  (a) the sentinel blacklist left `unresolved-range`, `invalid-range` and `""` open. Sentinels are
      SELF-MATCHING strings, so recording and re-reading both yield the same value and equality
      passes: two `pass` rows against a nonexistent range opened the R2 gate (`ok`, exit 0).
  (b) `test_gate_rejects_legacy_empty_hash_records` was VACUOUS — deleting the legacy clause left
      9/9 green, because a real diff's digest already differs from the injected value. It was
      reported as coverage in error.
  (c) the "local/CI divergence closed" claim was over-stated: only `_judge_snapshot` was shown to
      agree across modes, not the GATE. The honest flow (stage → commit → push) still diverged.
- 2026-09-10 **Replan** (this is the reason `enforcement/ci/pre-push` joined `scope_in`): finding (c)
  is rooted in `pre-push`, which already derives the pushed range for task selection but never
  exports it, so `_judge_snapshot` fell back to `git diff --cached` — empty right after a commit.
  Fixing the reject mechanism itself was explicitly authorized by the user after the scope gate
  blocked the edit. `pre-push` IS the push gate, so this keeps the task at R2/security.
- 2026-09-10 Reworked the fix from a blacklist to a WHITELIST (`_binds_to_content`): only a 64-hex
  content digest binds a verdict. Adding a new sentinel can no longer silently reopen the hole.
  Removed a redundant `_binds_to_content(recorded)` call from the counting loop: the guard above
  proves the current snapshot binds and equality then forces the recorded one to bind, so the check
  was UNREACHABLE by construction — an unreachable check reads as coverage it cannot provide.
  Rescoped the former vacuous test's docstring to the outcome it genuinely asserts.
- 2026-09-10 Six conformance scenarios broke under the stricter rule because they recorded passes in
  git-less sandboxes. Fixed by giving them a REAL staged in-scope diff (`stage_reviewable_change`)
  so depth scenarios exercise content-bound passes, rather than by relaxing the rule. The UTC
  timestamp scenario switched to `--verdict fail`, which stamps `ts` identically and is still legal
  with no diff.
- 2026-09-10T08:09:30Z Codex takeover from Claude session 93f7da52-af55-4bb8-b1d1-36b8599c620b explicitly requested by the user; review, required independent judges, verification, and commit remain in scope.
- 2026-09-10T08:12:19Z Codex review found and fixed a coverage gap: the empty-pass test now invokes the CLI and asserts exit 1, so the main() refusal exit path is load-bearing; corrected the stale acceptance block reason to judge-snapshot-unbound=empty-diff.
- 2026-09-10T08:15:01Z Codex review verification: focused judge snapshot tests 13/13 PASS; CLI exit-code mutation failed the strengthened test as expected (.vemo/run/negative-cli-exit.qTQ40F/result.log); full unittest 77/77 PASS; bash -n and git diff --check PASS; fresh vemo verify --no-cache PASS (126/126 conformance, selfcheck OK), evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T081400Z.log.
- 2026-09-10T08:32:57Z Independent correctness judge recorded FAIL: inherited VEMO_DIFF_RANGE could override Git stdin and replay an older reviewed snapshot for a newer push; prior conformance explicitly unset the variable. Reworked pre-push precedence so stdin is authoritative, reset verdict pending re-review, and added an executed stale-environment replay scenario.
- 2026-09-10T08:35:17Z Round-3 rework verified: stale-range replay scenarios 2/2 PASS; reverting stdin precedence in an isolated copy fails 0/1 (.vemo/run/negative-prepush-precedence.ZyvkPu/result.log); full unittest 77/77 PASS; fresh vemo verify --no-cache PASS with conformance 127/127 and selfcheck OK, evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T083413Z.log.
- 2026-09-10T08:58:48Z Independent safety judge recorded FAIL: a two-ref push could bind only the first reviewed range and authorize an unreviewed second ref, falsifying the claimed over-block-only limitation. Reworked fail-closed behavior to reject multiple non-deletion refs with multi-ref-push-unsupported, reset verdict pending re-review, and added an executed two-ref replay scenario.
- 2026-09-10T09:00:53Z Round-4 rework verified: all push-gate scenarios 3/3 PASS; disabling multi-ref refusal in an isolated copy fails 0/1 (.vemo/run/negative-prepush-multiref.jtMmUU/result.log); full unittest 77/77 PASS; fresh vemo verify --no-cache PASS with conformance 128/128 and selfcheck OK, evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T085941Z.log.
- 2026-09-10T09:02:17Z Refreshed full-profile receipt after correcting the pre-push multi-ref comment: vemo verify --no-cache PASS, conformance 128/128 and selfcheck OK, evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T090134Z.log.
- 2026-09-10T09:14:31Z Fresh correctness judge recorded FAIL on a stale CHANGELOG coverage note that still claimed multi-ref pushes snapshot the first range, contradicting round-4 fail-closed behavior. Corrected the release note; functional review otherwise passed 13/13 focused, 77/77 unit, 128/128 conformance, CI 5/5, selfcheck, and stdin-free CI negative mutation.
- 2026-09-10T09:15:19Z Refreshed full-profile receipt after correcting the stale CHANGELOG note: vemo verify --no-cache PASS, conformance 128/128 and selfcheck OK, evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T091436Z.log.
- 2026-09-10T09:28:59Z Fresh correctness judge recorded FAIL on an overbroad risk claim that the change could only turn passes into blocks. Reworded the invariant precisely: unbound/stale/ambiguous evidence blocks, while a current single-ref range with enough matching content-bound passes may proceed; reset verdict pending re-review. Functional checks and receipt remained valid.
- 2026-09-10T09:47:14Z Independent safety judge recorded FAIL: a new-branch push used tip~1...tip, so passes for the reviewed tip could authorize an earlier persistent unreviewed commit. Reworked new-branch range derivation to cover all commits after exactly one named-remote boundary and fail closed if absent/ambiguous; reset verdict and added unresolved/full-history scenarios.
- 2026-09-10T09:49:19Z Round-5 rework verified: push-gate scenarios 5/5 PASS; reverting new-branch coverage to tip~1...tip fails the full-history scenario 0/1 (.vemo/run/negative-prepush-newbranch.cLtbio/result.log); full unittest 77/77 PASS; fresh vemo verify --no-cache PASS with conformance 130/130 and selfcheck OK, evidence .vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T094813Z.log.
- 2026-09-10T10:07:46Z Scope expanded to enforcement/ci/vemo-ci.yml and .github/workflows/vemo-ci.yml: the non-fast-forward finding proves local rsha...lsha and CI push-event BEFORE...HEAD share the same remote-only deletion omission, so parity requires both workflow copies; R2/security classification unchanged.
- 2026-09-10T10:10:31Z Independent safety judge recorded FAIL: three-dot existing-ref ranges omitted remote-only deletions on non-fast-forward updates and allowed local-side passes to authorize a larger tree transition. Expanded scope with user-authorized task objective, changed local and push-event CI to exact two-dot tree ranges (PR stays triple-dot), reset verdict, and added executed non-fast-forward plus workflow-parity checks.
- 2026-09-10T10:14:46Z Round-6 rework verified: the executed non-fast-forward fixture and both workflow-parity checks PASS; reverting the local gate to triple-dot fails 0/1 and reverting both push workflows fails 0/2 (`.vemo/run/negative-prepush-nonff.jfesS1/{local-result.log,workflow-result.log}`); full unittest 77/77 PASS; fresh `vemo verify --no-cache` PASS with conformance 133/133 and selfcheck OK, evidence `.vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T101359Z.log`.
- 2026-09-10T10:15:16Z Round-6 verification complete: 77/77 unit, 133/133 conformance, exact non-fast-forward tree-transition coverage and both workflow parity checks pass; final independent review pending.

## Acceptance Result
- PASS: `_judge_snapshot` on an empty in-scope diff returns `EMPTY_SNAPSHOT`, and asserts it is not
  `sha256("")` — `test_empty_diff_is_not_a_content_hash`.
- PASS: `judge_record(..., "pass")` with nothing staged returns `refused:…`, exits 1, and the
  append-only log is never created — `test_judge_record_refuses_a_pass_bound_to_nothing`.
- PASS: `judge_record(..., "fail")` with nothing staged still returns `recorded:…` — no over-block on
  the legitimate "the change is missing" verdict — `test_judge_record_still_accepts_a_fail_with_no_staged_diff`.
- PASS: the gate returns `block:judge-snapshot-unbound=empty-diff` once a real pass's diff is no longer visible,
  and `block:judge-pass-count=0` for a legacy `sha256("")` row —
  `test_gate_blocks_when_no_in_scope_change_is_visible`, `test_gate_rejects_legacy_empty_hash_records`.
- PASS: staged mode and `VEMO_DIFF_RANGE` mode yield an identical snapshot for identical content —
  `test_staged_and_range_modes_agree_for_the_same_content`. This is the local/CI divergence closed.
- PASS: a genuine pass bound to the staged diff still returns `ok` —
  `test_gate_accepts_a_pass_bound_to_the_staged_diff`.
- PASS: negative test — deleting `if not paths: return EMPTY_SNAPSHOT` fails 4 of the 9 tests with the
  `e3b0c442…` hash in the assertion output. The tests fail when the fix is absent.
- PASS: full unit suite `python3 -m unittest discover -s tests` = 77 tests OK (64 pre-existing + 13 new).
- PASS: `python3 eval/run.py` conformance 133/133 = 100%.
- PASS: `python3 enforcement/validators/task_state.py selfcheck` = OK.
- PASS: `python3 bin/vemo verify --no-cache` build_exit=0 smoke_exit=0, receipt `.vemo/run/receipt.json`,
  log `.vemo/run/T-20260910-reject-empty-judge-snapshots-20260910T101527Z.log`.
- PASS (round 2): the sentinel bypass an independent judge demonstrated is closed at BOTH layers.
  `VEMO_DIFF_RANGE=deadbeef…...HEAD judge-record --verdict pass` → `refused:… snapshot
  'unresolved-range' binds to no code`, exit 1; `--output=/tmp/pwn` → same via `invalid-range`.
  Rows injected DIRECTLY into the log (bypassing the refusal) are still blocked at the gate with
  `judge-snapshot-unbound`. Covered by `test_unresolvable_range_cannot_mint_a_pass` and
  `test_injected_option_like_range_cannot_mint_a_pass`, which FAIL against the old blacklist.
- PASS (round 2): `_binds_to_content` pinned directly by `test_binds_to_content_accepts_only_real_digests`
  (rejects `None`, `""`, all three sentinels, 63/65-char, uppercase, and non-hex input).
- PASS (round 2): the push-gate divergence is closed and the fix is proven load-bearing. In a real
  repository, after a commit (empty index) the gate reports `judge-snapshot-unbound=empty-diff`
  without the export and `judge-provenance-mismatch (log says 'fail')` with it — i.e. it went from
  seeing nothing to reading the actual recorded verdict. Covered by the EXECUTED conformance
  scenario "push gate: hands the pushed range to the validator", which fails (125/126) when the two
  export lines are removed.
- PASS (round 3): an inherited range for an older, fully reviewed commit cannot replace Git's stdin
  range for a newer unreviewed push. The executed scenario records two valid passes for the old
  range, then pushes a newer commit with that range still in the environment; the gate blocks with
  `judge-pass-count=0`. Changing the precedence back makes the scenario fail 0/1 — evidence
  `.vemo/run/negative-prepush-precedence.ZyvkPu/result.log`.
- PASS (round 4): a two-ref push with two passes for the first range and an unreviewed second range
  now fails with `multi-ref-push-unsupported`. Disabling the multi-ref refusal makes the targeted
  scenario fail 0/1 — evidence `.vemo/run/negative-prepush-multiref.jtMmUU/result.log`.
- PASS (round 5): a new branch with no target-remote boundary fails closed; with one boundary, its
  snapshot covers both an earlier unreviewed persistent commit and the reviewed tip, so tip-only
  passes do not count. Reverting to `tip~1...tip` makes the full-history scenario fail 0/1 — evidence
  `.vemo/run/negative-prepush-newbranch.cLtbio/result.log`.
- Verification boundary: this fixes which snapshots the gate ACCEPTS. It does not re-verify the three
  historical tasks whose passes were opened by an empty snapshot; their rows are rejected on read but
  their already-merged code was never re-judged under the stricter rule. Recorded as a known gap in
  CHANGELOG rather than silently repaired, because `.vemo/judge.jsonl` is append-only.
- Compatibility boundary (round 4): multi-ref pushes are intentionally rejected locally and must be
  split into one non-deletion ref per push. This is fail-closed because the provenance schema carries
  one scalar snapshot; silently using the first range was proven to authorize unreviewed later refs.
- Compatibility boundary (round 5): a new branch push requires exactly one boundary reachable from
  the named remote's tracking refs. Fetch the target remote first; histories with no or several
  boundaries are rejected because one scalar range cannot prove what the remote already knows.
- Compatibility boundary (round 6): a non-fast-forward update must be judged against the exact
  `remote..local` transition; passes recorded only against the local-side merge-base diff do not count.
- Verification boundary (round 2): the conformance scenario copies `pre-push` and the validator into
  its fixture because `pre-push` exports `VEMO_ROOT` from its own location. It therefore exercises
  the script's logic, not a real `.git/hooks/pre-push` installation.

## Conclusion
Outcome: a judge verdict binds to reviewed code or does not count. Only a 64-hex content digest
binds — a whitelist, so a newly added sentinel cannot silently reopen the hole the way the first
attempt's blacklist did. The push gate now hands the pushed range to the validator, so the local
gate and CI evaluate the same diff instead of disagreeing about one commit.
Decision: commit after two independent R2 judge passes and the mechanical commit gates; pushing remains
a separate user action. The
failed correctness and safety rounds are why this task exists in its current form; every FAIL row
stays in the append-only log as provenance.
Key Evidence: 13-test regression suite (2 bypass tests fail against the old blacklist), EXECUTED
push-gate conformance scenarios that fail when range export, stdin precedence, multi-ref refusal, or
new-branch history coverage, non-fast-forward exactness, or workflow parity is removed, 77/77 unit,
133/133 conformance, verify receipt (build=0 smoke=0).
Risk: unbound, stale, and ambiguous snapshots now block, while a single-ref push with enough matching
content-bound passes can proceed. The main compatibility cost is intentional rejection of multi-ref
pushes; the security risk is selecting the wrong range, covered by executed empty-index, stale-environment,
and multi-ref scenarios. The `fail`-still-recordable and pass-bound-to-staged-diff criteria check against
over-blocking, and the six repaired conformance scenarios use real reviewable diffs rather than relaxed rules.
Honest note: this task's own history is the case study. The first fix passed 73 tests, 125/125
conformance and a full verify receipt while leaving three equivalent bypasses open and shipping one
vacuous test — mechanical green is not evidence of correctness, and the independent judge is what
caught it.
