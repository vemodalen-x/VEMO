# Adopter critique to fix log

> We played our own toughest user across three rounds (skeptic → daily user → would-be contributor). Each
> challenge got a response and a real change shipped. This is the honest version of "dogfooding our own
> governance": surface the objections, then fix them.

---

## Round 1 — the skeptic (first 5 minutes)

**Challenge**
- Q1. "Is this just another bundle of Markdown rules and scripts?"
- Q2. "Setup wants Python + installing git hooks. I won't pay that tax just to look."
- Q3. "Won't all these gates slow me down on a one-line change?"

**Response**
- A1. The load-bearing layer is not prose: `enforcement/` (hooks + CI + validator), the `vemo` CLI, executable
  eval, and capability-monotonic governance are concrete mechanisms with runnable checks.
- A2. Fair. **Shipped `vemo init --minimal`**: a no-install, monitor-mode trial — copy 4 things, run it, it
  *observes and logs, blocks nothing*. Zero risk to look. Flip on enforcement only when you're convinced.
- A3. That's the point of **risk tiers**: an R0 change (docs/config) is ~3 steps; the heavy path only appears
  on R2 (core/auth/migrations). Ceremony scales to blast radius.

**Shipped this round:** `vemo init --minimal` · `ANNOUNCEMENT.md`.

---

## Round 2 — the daily user (first real day)

**Challenge**
- Q4. "I'm on Windows / no bash — the `.sh` hooks don't run."
- Q5. "I use Cursor / Copilot / Codex, not Claude Code. Is this useless to me?"
- Q6. "A hook blocked a *legit* edit. Now I'm fighting the tool."

**Response**
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

**Challenge**
- Q7. "Where's the proof it works — not just elaborate scaffolding?"
- Q8. "Can the agent just *disable the hooks* to get its way?"
- Q9. "How do I extend/contribute, and who steers the project?"

**Response**
- A7. Run `vemo eval` — an **executable conformance suite** (9/9; it *found and fixed a real bug* in VEMO on
  its first run). Plus one limited internal trial exercised the gates end-to-end. Honest gap: not battle-tested
  at scale → OTel telemetry + a transcript-level eval + a governed-vs-ungoverned benchmark are on the
  [ROADMAP](ROADMAP.md).
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
