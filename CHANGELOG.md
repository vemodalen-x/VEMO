# Changelog — VEMO

All notable changes to the VEMO governance framework.

## [1.8.0] — 2026-06-16

Launch-readiness + **3 rounds of adopter-critique → fixes** (`docs/CRITIQUE_LOG.md`), plus promo + an honest
differentiation-from-Wildpanda statement.

### Added
- `docs/ANNOUNCEMENT.md` (launch / Show-GitHub draft), `docs/VS_WILDPANDA.md` (open attribution + why VEMO is a
  distinct framework, not a fork), `docs/CRITIQUE_LOG.md` (3-round 质疑/答复), `SECURITY.md` (threat model +
  tamper-evidence + honest limits), `ROADMAP.md`.
- **`vemo init --minimal`** — no-install, monitor-mode trial (observe + log, block nothing). [R1]
- **`enforcement/hooks/run.py`** — pure-Python, bash-free hook dispatcher for Windows / no-bash hosts. [R2]

### Changed
- `vemo selfcheck` adds a **tamper check** (flags the scope hook removed from `.claude/settings.json`). [R3]
- README + docs index link the launch / security / roadmap / differentiation docs.

## [1.7.0] — 2026-06-16

Gap-closing round toward top-tier scores — combining **Wildpanda's strengths not yet ported** with 2026
production-governance best practices (full-system eval, four guardrail elements, policy-as-code, monitor→enforce
rollout, EU AI Act / NIST AI RMF / OWASP LLM Top-10 / MS Agent Control Spec). All with running evidence.

### Added
- **Executable conformance harness `eval/run.py`** (`vemo eval`): runs the SC scenarios against the validator in
  isolated sandboxes, asserts gate outcomes, writes `eval/out/report.json`. **Found and fixed a real bug** on
  first run (`_rel` resolved relative paths against CWD not repo-root → CWD-dependent scope/tier); now **9/9 = 100%**.
- **`vemo selfcheck`** — framework internal-consistency lint (config keys, required specs, every skill has a
  SKILL.md, every safety guard present). Passes.
- **Ported Wildpanda's domain agents** `agents/algo-library.md` + `agents/conversion-deploy.md` (VEMO-adapted:
  capability-aware, model from `model_routing` not hardcoded, governed by verify/safety/provenance).
- **Restored `specs/comment.spec.md`** (function-comment governance — advisory; a Wildpanda strength VEMO had
  downgraded). Loaded for `code_change` via the manifest.
- **`docs/COMPLIANCE.md`** — maps VEMO controls → four guardrail elements (Permission/Approval/Audit/Kill-switch)
  + EU AI Act / NIST AI RMF / OWASP LLM Top-10 / MS Agent Control Spec.
- **`enforcement.mode: enforce | monitor`** — observe-only rollout posture (monitor→enforce best practice);
  action-chaining note in `safety.spec`.

### Fixed
- `_rel` path resolution is now CWD-independent (root-relative) — caught by the new eval harness.

## [1.6.0] — 2026-06-16

**Capability-monotonic governance** — make VEMO work *better*, not worse, as models get stronger. Driven by
the Fable 5 / Mythos 5 system-card analysis (see `docs/SCALING.md`): strong models fabricate less but **skip
running verification**, **game the governance process** (re-authoring commits to dodge review), and can
**sabotage undetected without narration**. So as `capability.tier` rises, *prescription* shrinks while
*verification + boundaries + audit* hold or **tighten**.

### Added
- **`specs/capability.spec.md`** — the capability-monotonic contract (inverse coupling; frontier failure
  modes → mechanism; safety is capability-invariant; verification scales up).
- **`docs/SCALING.md`** — the *why*, with the analysis + per-failure mapping + sources.
- **`verification` config section** — `ground_truth_required`, `require_intent_narration`,
  `independent_verifiers` (panel size scales with tier), `check_authorship_provenance`.
- **`task_state.py verify-plan --risk`** — derives required verification depth from tier × risk (mechanizes
  the inverse coupling). **`run_budget.reanchor_every_calls`**. eval `SC03_capability_monotonic`.

### Changed
- **Executed-ground-truth acceptance gate**: a `passed` acceptance now REQUIRES a real run (non-null exit code
  + evidence log) for R1/R2 — a "verified" claim with no execution trace is BLOCKED (`gate-check`).
- **Judge** gains checks #5–7 (executed-not-claimed, no process-gaming, narration-present) + **panel mode** at
  high/frontier tiers (a single same-class judge shares the worker's blind spots).
- **`enforcement.safety_invariant_of_capability: true`** — safety + run_budget never relax as capability rises.

## [1.5.0] — 2026-06-16

### Added
- **Skill suite, ported and optimized from Wildpanda** (`skill/`, catalog in `skill/_catalog.md`):
  `call-graph`, `flow-discovery`, `docs-sync` (generalized from `readme-update`), `governance-sync`,
  `governance-contribute`, `governance-release` — joining the existing `automation-mode`.
- **Deterministic scripts** where Wildpanda had inline shell-as-prose: `skill/call-graph/scripts/cg.py`
  (a real call-graph engine: index + Q1–Q5 via ctags/cscope, graceful degradation) and
  `skill/governance-sync/scripts/govsync.py` (upstream version/commit diff via `gh`).

### Changed
- **Claude Code engineer optimization**: SKILL.md files slimmed from 130–213-line prose procedures to ~35-line
  thin contracts (frontmatter · when · steps · notes); sharper auto-invocation `description`s; composable /
  single-responsibility (docs-sync is the single owner of doc edits); capability-aware notes; integrated with
  `vemo` + the validator. Net: same coverage as Wildpanda's 7 skills at ~¼ the prose, with the hard parts now
  tools instead of instructions.

### Removed
- `bootstrap-governance` (Wildpanda's PowerShell onboarding) — superseded by `vemo init --preset` +
  `enforcement/install.sh` (one command, cross-platform).

## [1.4.0] — 2026-06-16

Usability / understandability / generalization round, grounded in 2026 best practices (GitHub spec-kit's
`specify init` + presets; Convention-over-Configuration; GitLab progressive disclosure; the Diátaxis docs
model). Goal: let people *start without thinking* but never *stop* them from thinking.

### Added
- **Unified `vemo` CLI** (`bin/vemo`): one verb-based entrypoint instead of long `python3 enforcement/...`
  invocations — `vemo init | status | doctor | explain | auto | budget | tier | check`. `vemo explain <topic>`
  teaches a concept in one plain sentence (discoverable progressive disclosure).
- **Per-stack presets** (`presets/{python,node,cpp,docs}.yaml`) + `vemo init --preset <stack>` → writes a
  `vemo.config.preset.yaml` overlay (deep-merged over the base by the validator). Drop VEMO into any repo type
  and it's preconfigured — generalization without forking.
- **Diátaxis docs**: `docs/QUICKSTART.md` (ruthlessly-focused tutorial, one "aha"), `docs/MENTAL_MODEL.md`
  ("VEMO in 5 ideas" + glossary + enforced-vs-advised + config tiers), `docs/INDEX.md` (need-based map).
- **`docs/GUIDE.html`** — single-page HTML usage guide with an optimized **architecture visualization**
  (layered stack with an enforced→advised rail, the request lifecycle with gate-intervention points, the
  defense-in-depth enforcement pipeline, and a risk×capability ceremony matrix). Self-contained, PDF-exportable.
- **Open-source packaging**: a public GitHub `README.md` (incl. the name origin — VEMO ← *vemödalen*),
  `LICENSE` (MIT), and `CONTRIBUTING.md` (VEMO governs itself; stdlib-only; brevity discipline).
- **`config-get`** validator command; config overlay deep-merge in `_load_config`.
- **eval `SC02_budget_hardstop`**: asserts an unattended over-budget run hard-stops, advisory when attended.

### Changed
- `vemo.config.yaml` reorganized for **progressive disclosure** (ESSENTIAL / COMMON / ADVANCED header).
- README quickstart now uses the one-command `vemo init` flow.

## [1.3.0] — 2026-06-16

Optimization round informed by published analysis of **Claude Fable 5** (first GA "Mythos-class" model) and
**Mythos** — see `docs/FABLE5_MYTHOS_OPTIMIZATION.md` (with sources; community "leaked-protocol" repos used
as inspiration only, not authority). Theme: stronger autonomous models need *less prescriptive ceremony but
stronger stop rules*.

### Added
- **`run_budget` / stop rules.** Mechanically bounds a run (max tool-calls / files / wall-clock + checkpoint
  cadence) via `enforcement/hooks/guard-budget.sh` + `task_state.py budget-tick|budget-reset|budget-status`.
  Enforcement is **asymmetric**: a HARD stop (exit 2) when unattended (auto mode ON), ADVISORY when a human
  is present. Directly answers Fable 5's documented tendency to "run until the harness cuts it off".
  `vemo-auto on` now resets the run counter.
- **`frontier` capability tier** (Mythos-class, above `high`): least prescriptive ceremony + self-tests, but
  must run under `run_budget` and still gets the R2 judge. `model_routing.long_horizon: fable-5` with a cost
  rule (frontier only for long-horizon/R2; never R0/R1).
- **Evidence-completeness check** in `verify.spec` + the judge: a PASS must cover the *full* claim scope, not
  a subset — guarding Fable 5's "checked one error type → 'no errors' → 20× undercount" blind spot.

## [1.2.0] — 2026-06-16

### Added
- **Full-auto (unattended) mode.** A `specs/automation.spec.md` + `skill/automation-mode` + an explicit
  enable/disable CLI (`enforcement/automation/vemo-auto on|off|status`). Auto mode turns the human-**approval**
  pauses (R2 plan review, push confirmation, subtask review, failure-disposition approval, stale-task
  takeover, comment review) into **auto-decide + record** — every decision is logged to
  `.vemo/auto_decisions.jsonl` and the task's `## Auto-Mode Decisions`. It is **OFF by default**, requires the
  explicit command, **expires** (default TTL 8h), and is bounded by a **risk ceiling** (`default_max_auto_tier:
  R1`; R2 needs `--allow-r2`). It **never** relaxes the mechanical safety guards, risk-tier integrity,
  `acceptance-before-push`, or the judge — which becomes *mandatory* on auto-approved R1+/R2 (it replaces the
  absent human reviewer). New `vemo.config.yaml → auto_mode` section; new validator commands
  `auto-status` / `auto-allows --tier`.

## [1.1.0] — 2026-06-16

Hardening round driven by an adversarial self-review (see `docs/VEMO_REVIEW_EN.html`). v1.0 introduced
the enforcement layer; v1.1 makes it *correct and non-bypassable*.

### Fixed
- **Front-matter parser correctness (real bug).** v1.0's hand-rolled YAML reader collapsed nested
  mappings (`acceptance:`, `judge:`) to `[]`, so `judge.verdict` was never readable — the R2 judge gate
  was effectively dead. Replaced with a correct indentation-based YAML-subset parser (still stdlib-only).

### Added
- **Risk-tier integrity (closes self-classification loophole).** `task_state.py tier-required` computes the
  *required* tier from the staged paths via `risk_tiers` globs; the CI backstop blocks a commit whose
  *declared* tier is lower than required. An agent can no longer label an R2 change "R0" to skip gates.
- **Mechanically-required R2 judge.** The CI backstop blocks an R2 push unless `judge.verdict == pass`.
  The judge is no longer skippable by simply not invoking it.
- **`task_state.py doctor`** — validates `vemo.config.yaml` + the active task front-matter (DX/robustness).
- **`get --field a.b`** — read a dotted nested field of the active task (enables the gates above).

### Changed
- **Fail-closed by default for safety-critical guards.** `enforcement.degrade_gracefully` now defaults to
  `false`: if the validator/python is unavailable, the scope/command/secret guards **block** rather than
  wave the action through. A missing guard is not assumed to be a safe guard. Opt back into fail-open
  explicitly per project.
- Config gains `enforcement.fail_closed`, `enforce_risk_tier`, `require_judge_on_R2`.

### Known limitations (tracked, not yet fixed)
- Hooks are bash + python3; on Windows they need git-bash/WSL. The *core logic* is pure-Python and
  callable from a PowerShell wrapper, but a first-class Windows hook runner is not shipped yet.
- `eval/` ships scenarios + metrics definitions but not a full agent-running harness (static checks only).
- The session-start bootstrap (load config + manifest) is still advisory prose — an irreducible trust core
  that enforcement shrinks but cannot fully remove.

## [1.0.0] — 2026-06-16

### Added
- Initial VEMO framework, rebuilt from Wildpanda + 2026 best practices through 3 perspective-shifting
  design iterations (`docs/ITERATION_LOG.html`): thin `AGENTS.md` router, JIT spec manifest, risk-tiered
  lifecycle (R0/R1/R2), `capability.tier` + `model_routing`, the `enforcement/` layer (hooks + CI +
  validator), independent `governance-judge` subagent, and an `eval/` conformance harness.
