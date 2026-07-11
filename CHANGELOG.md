# Changelog

All notable changes to VEMO are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/); versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- `vemo fleet`: a stdlib-only, user-local control plane for registering, discovering, assessing, and preview-first
  onboarding Git projects across one PC. Includes canonical project ids, JSON reports, strict mode, managed-file
  hashes, dirty/conflict refusal, optional byte-identical VEMO_SKILLS binding, and a privacy-minimized hash-chained
  mutation log. Cross-process registry/audit locks prevent lost updates during concurrent Windows sessions.
- Progressive `solo`, `team`, and `regulated` governance profiles plus standards/readiness documentation. Profiles are
  adoption targets and explicitly do not claim certification.
- Fleet unit tests are part of the conformance harness, including nested repositories, Git worktrees, dry-run safety,
  conflict handling, registry deduplication, launcher isolation, JSON contracts, and audit tamper detection.
- `docs/DIAGNOSTIC_PROMPTING.md`: a framework-level pattern for diagnostic coaching/tutoring prompts, abstracting
  intake -> map -> constraint -> plan -> loop -> boundary from Human 3.0 and Mr. Ranedeer-style references without
  copying external prompt text.
- `docs/PLAYBOOK_ADOPTION.md`: migration guidance for converting repo-local agent playbooks into VEMO mechanisms.

### Fixed
- CLI and installer Python dispatch now use the current interpreter or fall back from `python3` to `python`, improving
  Windows compatibility.

## [1.9.0] — 2026-07-09

Version-line realignment onto the public `v1.8.0` tag baseline + destructive-command gate hardening.

### Changed
- **Versioning realigned onto the public `v1.8.0` tag.** VEMO's git tags and VERSION file had drifted
  (the sole tag `v1.8.0` sits above an internal `1.2.0`->`1.4.0` dev line). Releases now continue ABOVE
  `v1.8.0`; `v1.9.0` is the first unified tag/VERSION/CHANGELOG release. Prior internal `[1.4.0]`/`[1.3.0]`/
  `[1.2.0]` entries below are retained as development history; the published `v1.8.0` tag commit is unchanged.

### Fixed
- **DESTRUCTIVE-command gate: closed pre-existing coverage gaps** (`enforcement/hooks/run.py`),
  surfaced by adversarial review, all in the SAFE (tightening) direction:
  - `git push` force is caught with the force flag in ANY short-flag position — `-f` / `-fu` / `-vf`
    (not only trailing) — alongside `--force`; `--force-with-lease` / `--force-if-includes` and a
    force-free `git push -u`/`-v` stay allowed.
  - `rm` recursive-force deletes are caught in ANY flag form — `-rf` / `-Rf` (capital-R synonym) / `-fr` /
    `-r -f` (split) / `--recursive --force` (long) — via two segment-scoped lookaheads (recursive AND force).
  - ANY target is covered, including `./relative` paths (the old pattern only matched `/ ~ * ..`).
  - Non-recursive `rm`, recursive-without-force, and plain `git push` stay allowed (no over-block).

### Verification
- `python3 eval/run.py` 83/83 · `vemo selfcheck` OK · `python3 enforcement/hooks/run.py --selftest` OK
  (two-way) · `vemo verify` receipt (build/smoke exit 0). R2: 2 independent governance-judge passes
  recorded in `.vemo/judge.jsonl` before merge.

## [1.4.0] — 2026-07-08

Ports two improvements reviewed from the sibling Wildmeerkat framework (v2.16.0/v2.17.0).

### Fixed
- **Danger-command gate false-positives** (`enforcement/hooks/run.py`): `guard_command` matched the
  DESTRUCTIVE patterns against the raw command, so a dangerous command that was merely ECHOED
  (`echo 'run git reset --hard to undo'`) was hard-blocked (exit 2). Added `strip_data_regions` to
  reduce an `echo`/`printf` segment to just its command name before matching — but ONLY when the segment
  has no command substitution (`$(`/backtick) and no redirect (`>`/`<`), so the builtin's literal
  arguments are provably pure data. This is the one STRUCTURALLY miss-safe transform: a real command can
  only sit in its own segment (after a `|`/`&`/`&&`/`;`/newline splitter — the full bash command-separator
  set), which is preserved; a `;`/newline inside a quoted echo arg merely over-splits (over-block = the
  safe side). Heredoc-body and comment-line stripping were also tried but REMOVED — reliably telling
  quoted/commented data from live code ACROSS lines needs a real shell parser, not a regex. Adversarial
  review found four bypasses in that heredoc/comment stripping (a `<<'W'` look-alike quoted / commented /
  backslash-escaped; a quote closing on a `#` line) — plus a fifth in the echo strip itself (a missing
  bare-`&` background separator, now added). All are fixed/removed; those forms now simply keep matching
  (a harmless over-block). Fail-safe: any error returns the raw command. Everything except echo/printf
  literal args — real commands, `&`/`&&`/`;` segments, `$()`/backticks, heredocs, comments, and all
  redirect operators/targets — is preserved byte-for-byte -> zero new missed blocks, proven by a two-way
  `run.py --selftest` (incl. all five review carriers) + hook e2e checks.

### Added
- **`vemo skill-roster`** + a one-line skills listing in the `vemo context` session brief
  (`skill_check.py roster`, reusing `collect()`), so the agent sees which skills exist at session start
  and under-invokes them less. Read-only, additive.
- eval `hook`/`skill` groups gain 8 checks -> conformance 71 -> 79/79.

### Verification
- `python3 eval/run.py` 79/79 · `vemo selfcheck` OK · `python3 enforcement/hooks/run.py --selftest` OK ·
  `vemo verify` receipt (build/smoke exit 0). R2: 2 independent governance-judge passes recorded in
  `.vemo/judge.jsonl` before merge.

## [1.3.0] — skill quality bar + registry consistency audit

Ports the sibling skill-home's transparent skill scorer into VEMO and adds a catalog<->disk consistency
audit, closing the gap where `selfcheck` only asserted a SKILL.md *exists*. Additive and self-contained:
the verdict engine (`task_state.py`) is untouched; the conformance eval grows 68->71 and stays green.

### Added
- **`enforcement/validators/skill_check.py`** — a transparent, gating skill quality bar (frontmatter
  present, name==dir, description well-formed, `_catalog.md`<->disk parity, cited backing scripts resolve,
  no duplicate names) plus a **consistency audit** (orphan catalog rows / unlisted skills / dangling
  backing scripts / mis-placed names). Description-quality cues are advisory, never gating — VEMO skills
  are noun-named (no gerund rule). Hermetic `selftest`; fail-closed.
- **`vemo skill-score` / `vemo skill-audit`** verbs.
- **eval `skill` group** (3 checks: score, audit, selftest) — conformance now 71/71.

### Notes
- No new `vemo.config.yaml` key: `selfcheck`'s every-key-has-a-consumer contract is unchanged.
- `docs/html/` regeneration via `docs/build_html.py` is a docs-sync follow-up (needs the `markdown` pkg).

## [1.2.0] — agent-loop economy ("overhead scales with risk, not activity")

A 2026 peer-benchmark review (Anthropic long-horizon harnesses, OpenAI Codex guardrails/AGENTS.md,
OWASP Agentic Top 10) plus a first-principles token-economy audit. The dominant cost was the judge
re-exploring the repo to reconstruct state; the fix is to hand judgment context to the gate's own code
and keep raw config out of the loop.

### Added — token economy (context is for judgment, subprocesses are for facts)
- **`vemo context`**: a ≤20-line machine-read session brief (tier · mode · task · gate status · budget ·
  rules). The SessionStart hook prints it, and `AGENTS.md` step 1 now runs it — replacing "bulk-read
  `vemo.config.yaml` + specs" at the start of every session.
- **`vemo judge-brief [--lens <l>]`**: an evidence dossier for a judge pass — claims, machine-computed
  gate results, receipt, per-file scope verdicts, and a lens-specific checklist — so judge tokens go to
  what machines cannot check (claims-vs-evidence semantics, completeness, gaming) instead of re-exploring.
- **`vemo heartbeat`**: stamps the active task's `heartbeat:` in place, so liveness costs no agent context.
- **Execution Log one-line discipline** (`specs/task.spec.md`): the log is a flight recorder, not a diary.

### Added — 2026 peer-practice guardrails
- **Stuck-loop detection**: the same Bash command 3× in a row = no progress (Codex "duplicate-call"
  practice). Advisory when a human is present; a hard stop under unattended auto mode.
- **`.gitignore` / `.gitattributes` are now R2** (audit-visibility files: one ignore line can hide judge
  provenance or receipts from git + CI).

### Fixed
- **Multi-task push gate**: `acceptance-before-push` and `required-judge` now evaluate **every** task file
  in the pushed range (the pre-push hook reads git's stdin refs; CI shares one `VEMO_DIFF_RANGE`), closing
  a gap where a multi-task push was gated on only the first task.
- **`vemo selfcheck` propagates its real exit code** (was always exit 0 through the CLI wrapper).
- **Acceptance gate is now clean-checkout-correct**: when `paths.build/smoke` are configured, the gate's
  evidence anchor is the machine receipt's **own** log (executed ground truth produced by `verify-run`
  this run), not the front-matter `evidence:` path — which is a human cache that points at a gitignored /
  rotated log absent on a fresh CI checkout, exactly where the guarantee must hold. (With no build
  configured, the front-matter evidence file is still required.)
- **Conformance eval is hermetic**: it clears an inherited `VEMO_DIFF_RANGE` at startup, so its throwaway
  `git init` sandboxes are never handed a range that only resolves in the real repo (surfaced when eval
  runs as `paths.build` inside `vemo verify` after CI exports the range).

### Governance / release hygiene
- Desensitized internal references from the tracked task records; added editor/IDE state to `.gitignore`.
- Conformance eval grown to **68 checks** (from 60), all green.

## [1.1.0] — trust-chain rework ("the labels are now checked")

Driven by a first-principles audit (`doc/vemo-first-principles-critique.md` in the parent workspace):
every `ENFORCED-BY` claim must map to a real mechanism, and every gate's input must be an artifact the
governed agent did not simply type.

### Fixed — claims that now match mechanisms
- **Server-side authority shipped**: `enforcement/ci/vemo-ci.yml` (+ installed for VEMO itself under
  `.github/workflows/`) re-runs selfcheck, the full eval, the commit backstop on the change range, the
  push gate, and the configured build/smoke. Previously "CI is the authority" had no CI file.
- **`acceptance-before-push` is now mechanical**: new `enforcement/ci/pre-push` (installed by
  `install.sh`), mirrored in CI. R0 is exempt (that is the point of R0).
- **Executed ground truth is now executed**: the gate requires the evidence file to exist, and — when
  `paths.build/smoke` are configured — the machine receipt written by the new `vemo verify`
  (`task_state.py verify-run`). Exit codes typed into front-matter no longer open any gate.
- **Judge verdicts need provenance**: the judge records via `task_state.py judge-record` into
  append-only `.vemo/judge.jsonl`; front-matter `pass` without a matching record blocks (forged-verdict
  defense). `SubagentStop`/`record-judge` telemetry now captures sessions.
- **The governance layer protects itself**: `enforcement/**`, `.claude/**`, `.github/**`,
  `vemo.config*.yaml`, `specs/**` are R2 by default; unmatched paths default to R1
  (`risk_tiers.unmatched`) instead of silently R0.
- **`enforcement.mode: monitor` now actually observes-without-blocking** in every guard (it was honored
  by one dispatcher and ignored by the bash guards).
- **safety.spec#6 (binary/model blobs) is now enforced** (`blob-check` in the edit guard;
  `exclusions.third_party` exempt) — it was labeled `ENFORCED-BY: hook` with no hook.
- **`install.sh` is actually idempotent** (dedupes hook registrations; migrates legacy `.sh` entries).
- **Honest labels elsewhere**: concurrency takeover is labeled advisory+audit (git cannot know "the
  committing session"); Bash-write scope bypass is warned client-side and contained at commit/CI;
  judge "panel" is labeled N sequential independent passes until a real panel ships.

### Changed — one dispatcher, fewer entities (Occam)
- The six `.sh` guards are **deleted**; `enforcement/hooks/run.py` is the single dispatcher
  (scope+blob+secret / command / budget / stop / subagent-stop / session-start). Every `.sh` already
  shelled out to python3, so bash bought no portability — only a second copy of the logic to drift.
- Hook registration uses `$CLAUDE_PROJECT_DIR` (CWD-independent) and adds `SessionStart`
  (telemetry heartbeat + one-line agent orientation; `vemo doctor` flags hooks that never fire).
- **Every config key now has a consumer or was deleted** — `selfcheck` enforces this and also verifies
  `ENFORCED-BY` labels point at existing mechanisms. Wired: `block_on`, `fail_closed`, `mode`,
  `enforce_risk_tier`, `require_judge_on_R2`, `rule_of_two`, `auto_mode.*` defaults,
  `observability.telemetry` levels, `stale_threshold_hours` (doctor), checkpoint/reanchor advisories,
  `exclusions.third_party` (blob guard). Deleted: `check_authorship_provenance` (ROADMAP).
  `model_routing` is explicitly labeled ADVISORY.
- Front-matter parser supports inline `{ }` maps (the `task.spec §2` example no longer crashes the
  validator); validator errors are uniform `error:*`/exit 3 and **fail closed** at safety gates.

### Added — oversight and concurrency primitives
- **Auto mode can no longer be enabled by the agent**: `vemo auto on` requires an interactive TTY +
  typed confirmation; the automation-mode skill exposes status/off only. Config defaults
  (`default_max_auto_tier`, `default_ttl_hours`, `record_to`, `preauthorized_commands`) are wired.
  Unattended R1+ pushes additionally require judge pass + provenance (`auto_mode.require_judge`).
- **Session binding** (`task_state.py bind`): hooks pass the harness `session_id`, so concurrent
  sessions are checked against *their own* task instead of "freshest heartbeat wins".
- **Budget semantics**: only write-touched files count toward `max_files_touched`; per-session
  counters; checkpoint/re-anchor advisory notes.
- **Destructive-command escape hatch** made real: task-file `approved_commands:` +
  `auto_mode.preauthorized_commands` (both logged).
- **Eval more than doubled**: 60 checks incl. hook end-to-end (payload → dispatcher → exit code), receipt
  flow, judge provenance, session binding, monitor mode, budget hard-stop, and agent-cannot-enable-auto.

### Hardened during release review (independent judge rounds + multi-model portability review)
The pre-release R2 task was reviewed by independent governance-judge passes; every FAIL round below left a
record in the (now tracked) `.vemo/judge.jsonl`. Fixed as a result:
- **Judge depth is capability-scaled and mechanical**: `required-judge` enforces
  `verification.independent_verifiers[capability.tier]` contiguous pass records for R2 (high=2, frontier=3;
  a later fail resets the suffix), and one pass for low/medium-tier R1; high/frontier R1 keeps the
  self-verify fast path.
- **Judge provenance is CI-visible**: `.vemo/judge.jsonl` is tracked by git (`.gitignore` un-ignores it;
  `.gitattributes` union-merges it; `selfcheck` fails if it is ignored). Server-side CI can now actually
  verify the required-judge gate — an ignored audit log was invisible to the authority layer.
- **Git-gate evasion blocked client-side**: the command guard now blocks `--no-verify` on
  commit/push/merge, `core.hooksPath` redirection, and writes into `.git/` (CI re-runs the same gates
  regardless).
- **Pre-commit secret scan SIGPIPE fix**: no more `git diff | grep -q` under `pipefail` (a real match
  could exit 141 and pass); scans a temp diff file, with an eval e2e check.
- **CI step order**: `verify-run` executes build/smoke and writes the receipt *before* the push gate
  reads it.
- **VEMO dogfoods its own receipt rule**: `paths.build` = the conformance eval, `paths.smoke` = selfcheck,
  so VEMO's own pushes require a machine receipt.
- **Multi-model / multi-harness portability made explicit**: `docs/ADAPTERS.md` documents the three-ring
  model and the ring-1 adapter contract (stdin JSON → dispatcher, exit 2 = block; minimal foreign payloads
  are eval-tested); `capability.spec §1.5` adds a vendor-neutral behavioral rubric for classifying any
  model into a tier; cross-family judge preference documented; `AGENTS.md` tells hookless agents what
  still binds them (git+CI rings).

## [1.0.0]

First public release.

### Governance model
- **Mechanism over prose** — safety-critical rules are enforced by Claude Code hooks (client-side) with a git
  pre-commit / CI backstop (authoritative; survives `--no-verify`), not merely written in Markdown.
- **Machine-readable task state** — durable front-matter (risk, scope, acceptance, judge, owner) that hooks and
  CI parse with a stdlib-only validator (`enforcement/validators/task_state.py`).
- **Risk tiers** R0/R1/R2 derived from the diff (no agent self-classification); ceremony scales per tier.
- **Capability-monotonic governance** — `capability.tier` (frontier→low) drives prescription *down* and
  verification *up* as the model strengthens; the safety invariants never relax.
- **Independent judge** (`agents/governance-judge.md`) on high-risk work, with a panel at frontier tiers.
- **Executed-ground-truth gate** — a "passed" acceptance requires a real run trace, not a claim.
- **Full-auto (unattended) mode** — records every decision; off by default; bounded by **run-budget stop rules**.
- **Rule-of-Two / lethal-trifecta gate** (OWASP ASI01) — a task touching all three of {private_data,
  untrusted_content, external_comms} requires explicit human approval; unattended auto must stop.

### Tooling & docs
- **`vemo` CLI** — `init` (presets: python/node/cpp/docs) · `status` · `doctor` · `selfcheck` · `eval` ·
  `explain` · `auto` · `budget` · `tier` · `check`.
- **Executable conformance harness** (`vemo eval`) — sandboxed fixtures assert real gate outcomes (**11/11**).
- Portable pure-Python hook dispatcher (Windows-friendly).
- Docs (Diátaxis): quickstart, mental model, scaling, compliance mapping (EU AI Act / NIST / OWASP), the
  OWASP Agentic Top 10 mapping, a visual HTML guide, and an architecture / threat overview.
