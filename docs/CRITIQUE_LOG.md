# Adopter critique → fix (3 rounds)

> We played our own toughest user across three rounds (skeptic → daily user → would-be contributor). Each
> **质疑 (challenge)** got a **答复 (response)** *and a real change shipped*. This is the honest version of
> "dogfooding our own governance": surface the objections, then fix them.

---

## Round 1 — the skeptic (first 5 minutes)

**质疑**
- Q1. "This is Wildpanda with extra files. How is it not a fork / ripoff?"
- Q2. "Setup wants Python + installing git hooks. I won't pay that tax just to look."
- Q3. "Won't all these gates slow me down on a one-line change?"

**答复**
- A1. We credit Wildpanda loudly (README, CHANGELOG, `governance-contribute` pushes fixes *back*). But the
  load-bearing layer — `enforcement/` (hooks+CI+validator), the `vemo` CLI, the executable eval, and
  capability-monotonic governance — **has no Wildpanda counterpart**. Different architecture (mechanism vs
  prose), full credit. → see [VS_WILDPANDA.md](VS_WILDPANDA.md).
- A2. Fair. **Shipped `vemo init --minimal`**: a no-install, monitor-mode trial — copy 4 things, run it, it
  *observes and logs, blocks nothing*. Zero risk to look. Flip on enforcement only when you're convinced.
- A3. That's the point of **risk tiers**: an R0 change (docs/config) is ~3 steps; the heavy path only appears
  on R2 (core/auth/migrations). Ceremony scales to blast radius.

**Shipped this round:** `vemo init --minimal` · `ANNOUNCEMENT.md` · `VS_WILDPANDA.md`.

---

## Round 2 — the daily user (first real day)

**质疑**
- Q4. "I'm on Windows / no bash — the `.sh` hooks don't run."
- Q5. "I use Cursor / Copilot / Codex, not Claude Code. Is this useless to me?"
- Q6. "A hook blocked a *legit* edit. Now I'm fighting the tool."

**答复**
- A4. **Shipped `enforcement/hooks/run.py`** — a pure-Python, bash-free hook dispatcher; register
  `python enforcement/hooks/run.py scope` on Windows. The decision logic was already stdlib-Python; now the
  runner is too. (Closes the long-standing portability gap.)
- A5. The specs are **plain Markdown any agent reads** — `AGENTS.md` is the cross-tool standard (Cursor/Copilot/
  Codex all read it). The **git pre-commit + CI backstop is agent-independent** and catches what the client
  hooks would; only the *client* hooks are Claude-Code-specific. So you lose fast feedback, not enforcement.
- A6. A false block means your task's `scope_in` was too narrow — fix the *declaration* (one-line replan), not
  the guard. And for onboarding, `enforcement.mode: monitor` lets you tune against real traffic before you ever
  block. (Calibrate, then enforce — the industry-consensus rollout.)

**Shipped this round:** portable `hooks/run.py` · agent-agnostic + monitor-mode guidance.

---

## Round 3 — the would-be contributor (deciding to invest)

**质疑**
- Q7. "Where's the proof it works — not just elaborate scaffolding?"
- Q8. "Can the agent just *disable the hooks* to get its way?"
- Q9. "How do I extend/contribute, and who steers the project?"

**答复**
- A7. Run `vemo eval` — an **executable conformance suite** (9/9; it *found and fixed a real bug* in VEMO on
  its first run). Plus a real dogfood: a skyline-segmentation task where the acceptance gate honestly **failed**
  a model (IoU 0.8453 < 0.85) and an independent judge re-ran the eval. Honest gap: not battle-tested at scale →
  OTel telemetry + a transcript-level eval + a governed-vs-ungoverned benchmark are on the [ROADMAP](ROADMAP.md).
- A8. **Tamper-evidence**: the CI backstop is *authoritative* (survives `git commit --no-verify`), and
  `vemo selfcheck` now flags if the hooks were removed from `.claude/settings.json`. Honest residual: a fully
  adversarial host can bypass *client* hooks — which is exactly why CI, not the client, is the authority. See
  [SECURITY.md](SECURITY.md).
- A9. [CONTRIBUTING.md](../CONTRIBUTING.md) lists good first issues; [ROADMAP.md](ROADMAP.md) shows direction;
  the project governs itself with its own gates (your PR runs through them).

**Shipped this round:** `selfcheck` tamper check · `SECURITY.md` · `ROADMAP.md`.

---

> Net of three rounds: a no-install trial, Windows support, agent-agnostic clarity, monitor-mode onboarding,
> tamper-evidence, a threat model, and a roadmap — each driven by a real objection, not a guess.
