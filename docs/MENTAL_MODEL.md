# VEMO in 5 ideas (the mental model)

> Diátaxis: this is **explanation** — understanding, not steps. It exists so the whole framework fits in
> your head. If you only read one doc, read this one.

## The 5 ideas
1. **Mechanism over prose.** The rules that matter (scope, no destructive cmd, no secrets, verify-before-push)
   are *enforced by hooks/CI* — they can't be argued out of. Prose specs hold the *advice*. (`vemo explain gates`)
2. **Ceremony scales — two ways.** Down by **risk** (R0 trivial → R2 critical) and down by **model strength**
   (`capability.tier`). A typo and a migration don't get the same process; Opus and Fable 5 don't get the same hand-holding.
3. **The repo is the memory.** Durable state lives in `tasks/<id>.md` front-matter (machine-readable), not in chat.
   Any session can resume from it; hooks read it.
4. **Verify, don't trust.** High-risk gates are flipped by an *independent judge* subagent, not the worker's
   self-report. Autonomy raises the value of verification, so stronger/auto modes lean on it *more*.
5. **Bounded autonomy.** Unattended runs have *stop rules* (`run_budget`) and *recording* (auto mode logs every
   decision). Freedom from approval pauses, never freedom from limits or the audit trail.

## Glossary (the only terms you need)
| Term | One line |
|---|---|
| **risk tier** R0/R1/R2 | how much process a change gets, by blast radius |
| **capability.tier** | how much hand-holding the *model* gets (frontier/high/medium/low) |
| **gate** | a checkpoint; *enforced* (mechanical) or *advised* (judgment) |
| **judge** | independent verifier subagent for R2 |
| **auto mode** | unattended: decide + record instead of asking; safety unchanged |
| **run budget** | stop rules for long runs (calls/files/time) |
| **scope_in** | globs a task may edit; edits outside are blocked |

## Enforced vs Advised (know which is which)
- **Enforced (cannot bypass):** scope containment · no destructive/out-of-repo cmd · no secrets ·
  acceptance-before-push · risk-tier integrity (no self-downgrade) · R2 judge pass · run budget (hard when unattended).
- **Advised (your judgment, judge may flag):** coding style · comments · decomposition depth · doc quality.

## Configure by tiers (progressive disclosure)
`vemo.config.yaml` is grouped so you can stop reading early:
- **ESSENTIAL** (set these): `capability.tier`, `paths.build`/`smoke`, `risk_tiers.*.match_paths`. A `--preset` fills most.
- **COMMON** (sometimes): `model_routing`, `auto_mode` defaults, `run_budget` limits.
- **ADVANCED** (defaults are fine): `enforcement.*`, `concurrency`, `observability`.

> The rule (from convention-over-configuration): VEMO should let you *start without thinking*, but never
> *stop* you from thinking. Presets are the "start without thinking"; this file is the "think when you need to."
