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

**Evidence completeness (anti-blind-spot, v1.3).** A PASS is valid only if its evidence covers the **full
scope of the claim**. Checking one case / one error type / one file and declaring a global "PASS" is itself
a FAIL. (This guards the documented Fable-5 failure: it reported "no error movement" after checking a single
error type and undercounted a real incident 20×.) The judge enforces this on R2 — see `agents/governance-judge.md`.

## 3. Independent judge (agent-as-judge)
When `risk_tiers[...].judge` resolves true (always R2; R1 only at `capability.tier<=medium` or critical paths),
the gate is flipped by `agents/governance-judge.md` running on `model_routing.judge` (Opus) — a **separate
context** from the implementer, prompted to *refute*. It returns a structured verdict:

```yaml
verdict: pass | fail
violations: []           # rule ids + evidence
evidence_checked: ["...:line", ".vemo/run/123.log"]
confidence: high|med|low
```

- The judge's verdict — not the implementer's claim — sets `judge.verdict` in the task front-matter.
- A `fail` verdict blocks `AcceptancePassed`. The judge cannot be the same session that did the work.
- Cost control: judge runs once per gate, only on tiers that require it. At `tier=high` most R1 work
  self-verifies (the model is trusted to check its own measurable criteria), keeping the loop fast.

## 4. Why this beats prose-only gates
A prose-only "hard gate" can degrade into an assertion the implementer makes about itself. A judge with its own
context, told to look for failure, catches the plausible-but-wrong "done" that a self-report waves through, and
it gets cheaper and more reliable as models improve, so it *replaces* ceremony rather than adding it.

## 5. Verification scales with capability (capability-monotonic — see `capability.spec.md`)
As `capability.tier` rises, prescription shrinks but verification **tightens** — never the reverse:
- `tier=low/medium`: judge on R1(critical)+R2; smaller steps; fuller prescription.
- `tier=high`: less hand-holding; R1 self-verifies measurable criteria; **judge panel of 2** on R2.
- `tier=frontier`: minimal prescription; **judge panel of 3, diverse lenses** on R2 (a single same-class judge
  shares the worker's blind spots).

Across all tiers, a `passed` acceptance must show **executed ground truth** — a real run with exit codes + an
evidence log. A "verified" claim with no execution trace is a **FAIL** (strong models skip running checks more
than they fabricate). The CI gate enforces this mechanically; `task_state.py verify-plan --risk <Rn>` returns
the required depth.
