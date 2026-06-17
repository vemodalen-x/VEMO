# VEMO — governance your AI agent can't talk its way out of

*Show GitHub / launch post draft.*

---

Your coding agent will tell you it "verified the change end-to-end." Frontier models (Fable 5, Mythos 5) now
**fabricate almost never** — but they **skip actually running the verification**, confidently. One documented
case: an agent reported *"no error movement"* after checking a single error type, while it **undercounted a
real incident 20×**.

Every AI-coding governance framework answers this by *asking the model nicely* — rules in a Markdown file the
model is trusted to read and obey. **VEMO doesn't ask. It checks.**

## What VEMO is

**VEMO** (Velocity-first · Enforced · Model-aware Orchestration) is a drop-in governance framework for AI coding
agents. Named after *vemödalen* — the dread that everything's already been done, that your work is one more
indistinguishable snapshot. Fitting, for an era drowning in look-alike AI-generated code. VEMO makes each change
**intentional, verified, and traceable.**

## Why it's different (the one-liner)

> It's the only one whose "hard gates" are **mechanical** (Claude Code hooks + a git/CI backstop + a
> machine-readable task state) instead of prose — **and we ship a runnable conformance suite that proves they
> fire (currently 9/9).** A gate that only exists in a Markdown file is a gate the model can ignore.

## Three things that'll make you star it

1. **Gates you can't argue with.** Edit a file outside your task's scope → blocked. `git reset --hard` →
   blocked. Push before tests actually ran (with exit codes + a log) → blocked. Not by hoping — by a hook that
   *can't hallucinate*. Run `vemo eval` and watch 9/9 gates fire on real fixtures. (The suite found and fixed a
   real bug in VEMO itself on its first run — that's the kind of honesty we ship with.)
2. **It gets *lighter* as your model gets *stronger*.** One knob — `capability.tier` — and ceremony shrinks
   while verification *tightens* (more independent checks, never fewer). Upgrade Opus → Fable 5, bump the tier,
   done. We call it **capability-monotonic governance**, and `verify-plan` computes it, not vibes.
3. **Velocity-first.** A typo and a schema migration don't get the same process. Risk tiers (R0 fast / R1 / R2
   critical) mean low-risk work is ~3 steps; the heavy machinery only shows up where the blast radius is real.

Plus: full-auto/unattended mode with **stop rules** (so a long-horizon model can't "run until the harness cuts
it off"), a unified `vemo` CLI, per-stack presets, and a controls-map to EU AI Act / NIST AI RMF / OWASP LLM
Top-10.

## 60-second try (no install, no risk)

```bash
cp -r VEMO/{AGENTS.md,vemo.config.yaml,specs,bin} your-repo/ && cd your-repo
python3 bin/vemo init --minimal     # monitor-mode: observes + logs, blocks nothing
vemo status                          # see what it would govern
```
Like what it observes? `vemo init --preset python` flips on real enforcement.

## We're honest about what it isn't

- It's **young** — one limited internal trial has exercised the gates end-to-end, but it is not yet
  battle-tested at scale.
- The eval is **mechanism-conformance**, not a production telemetry stack yet (OpenTelemetry + transcript-level
  eval are on the roadmap).
- It stands on public best practices including 12-Factor Agents, AGENTS.md, Diátaxis, and spec-kit/Kiro.
  We did not reinvent every principle; we made the most important ones *mechanical*.

## Help us optimize it

Good first PRs: a new `presets/<stack>.yaml`, an `eval/` scenario, OpenTelemetry hooks, a Windows-native hook
runner. We govern ourselves with our own gates — your PR runs through them too. ⭐ if a governance framework
that *proves* it works (and tells you where it doesn't) is what you've been missing.

`vemo eval` · MIT · [README](../README.md) · [docs index](INDEX.md)
