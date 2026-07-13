# verify.spec — Acceptance + independent verification

> Two ideas: (1) acceptance criteria must be **measurable and falsifiable** (EARS-style), and
> (2) high-risk gates are flipped by an **independent judge**, not the implementer's self-report.
> "Verify, don't trust."

## 1. Acceptance criteria (EARS-style)
Every R1/R2 task declares criteria *before* execution, each:
- **Measurable**: a metric/exit-code/observable (`fusion_ms < 500`, `ExitCode=0`, `PSNR_drop < 0.1dB`).
- **Falsifiable**: a threshold that can objectively PASS/FAIL.
- **Attributed**: a category (`Build|Correctness|Performance|Quality|Security`).

EARS phrasing keeps them testable: *"WHEN `<trigger>`, the system SHALL `<measurable response>`."*
Vague criteria ("faster", "looks better") are rejected by the plan gate.

## 2. Evaluation
After execution, each criterion is marked PASS/FAIL with the command, exit code, and an evidence path
(`.vemo/run/<id>.log`). Any FAIL takes a disposition before the task can advance:
`RCA-inline | RCA-subtask | Criterion-revision | Known-limitation` (+ user approval for the last two).

**Run `vemo verify`, don't type numbers.** When `paths.build`/`paths.smoke` are configured, the push gate
trusts only the **machine receipt** (`.vemo/run/receipt.json`) written by `vemo verify` — it executes the
build/smoke itself and records the exit codes. Front-matter `acceptance:` fields are a human-readable cache
of that receipt, not the source of truth; a `passed` whose evidence file does not exist is **blocked**.

Verification profiles keep cost proportional:
- `focused` (R1 default): run exactly the task's `test`, `lint`, and one real `smoke` command.
- `full`: run repository-wide `paths.build` and `paths.smoke`.
- `release`: run the full profile plus `paths.package_scan`; release-class tasks must use this profile.
  The commit and acceptance gates enforce that contract; declaring `release` with `full` is blocked.

Successful runs are cached by a SHA-256 fingerprint of the profile, commands, and files matching the
task's `scope_in`. `tasks/**`, `.vemo/**`, ignored files, and unrelated concurrent-task files are excluded.
An in-scope content or command change invalidates the receipt; `vemo verify --no-cache` forces execution.

For a push range containing multiple accepted tasks, run `vemo verify --all-tasks`. The command writes the
current compatibility receipt plus one task-scoped receipt under `.vemo/run/receipts/` for each task in the
staged or CI range. The acceptance gate selects the receipt matching the task id, so one task cannot overwrite
another task's executed evidence.

**Evidence completeness (anti-blind-spot).** A PASS is valid only if its evidence covers the **full
scope of the claim**. Checking one case / one error type / one file and declaring a global "PASS" is itself
a FAIL. (This guards the documented Fable-5 failure: it reported "no error movement" after checking a single
error type and undercounted a real incident 20×.) The judge enforces this on R2 — see `agents/governance-judge.md`.

## 3. Independent judge (agent-as-judge)
When the capability/risk matrix requires a judge, the gate is flipped by `agents/governance-judge.md` — a
**separate context** from the implementer, prompted to *refute*. The actual model/provider is harness-specific:
`model_routing.judge` and the judge agent front-matter are advisory records, while the enforced invariant is
"separate verifier context + provenance record(s)." It returns a structured verdict:

```yaml
verdict: pass | fail
violations: []           # rule ids + evidence
evidence_checked: ["...:line", ".vemo/run/123.log"]
confidence: high|med|low
```

- **Provenance, not paste:** the judge records its verdict with
  `task_state.py judge-record --task <id> --verdict pass|fail` (append-only `.vemo/judge.jsonl`), *then*
  mirrors it into the task front-matter. The commit/push gates require the front-matter `pass` plus enough
  contiguous pass records for the required verifier depth. A `pass` typed into front-matter with no provenance
  record is treated as forged and blocks. A later `fail` resets the contiguous pass count until rework earns
  the required pass suffix again. Each pass is bound to a task-scoped staged/range snapshot (excluding the
  provenance log and only the active task's normalized `judge:` verdict cache); changing task criteria, a task
  template/sibling task, or another in-scope file
  invalidates old passes, while mirroring the verdict and sibling-task files do not.
- A `fail` verdict blocks `AcceptancePassed`. The judge cannot be the same session that did the work.
- Cost control: judge runs only on tiers that require it. At `tier=high`/`frontier`, most R1 work
  self-verifies; at `tier=medium`/`low`, R1 needs one judge pass. R2 requires
  `verification.independent_verifiers[capability.tier]` pass records, except `ci-narrow` R2 uses one.
  `security`, `permissions`, and `release` retain full depth.

## 4. Why this beats prose-only gates
A prose-only "hard gate" can degrade into an assertion the implementer makes about itself. A judge with its own
context, told to look for failure, catches the plausible-but-wrong "done" that a self-report waves through, and
it gets cheaper and more reliable as models improve, so it *replaces* ceremony rather than adding it.

## 5. Verification scales with capability (capability-monotonic — see `capability.spec.md`)
As `capability.tier` rises, prescription shrinks but verification **tightens** — never the reverse:
- `tier=low/medium`: judge on R1+R2; smaller steps; fuller prescription.
- `tier=high`: less hand-holding; R1 self-verifies measurable criteria; **2 independent judge passes** on R2.
- `tier=frontier`: minimal prescription; **3 independent judge passes, diverse lenses** on R2 (a single
  same-class judge shares the worker's blind spots).

"N passes" today means invoking the judge agent N times with fresh context, each recording via `judge-record`
(`verification.independent_verifiers` sets N; `verify-plan` reports it; `gate-check required-judge` enforces
the contiguous pass count). A true concurrent multi-agent panel is ROADMAP — the spec does not pretend otherwise.

Across all tiers, a `passed` acceptance must show **executed ground truth** — a real run with exit codes + an
evidence log that exists (and, when build/smoke are configured, the `vemo verify` receipt). The pre-push/CI
gates enforce this mechanically; `task_state.py verify-plan --risk <Rn>` returns the required depth.
