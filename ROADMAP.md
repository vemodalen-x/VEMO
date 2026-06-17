# VEMO roadmap

Honest, prioritized. VEMO is young (v1.7); the items below are what stand between it and "battle-tested."
Most are good first contributions — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Near-term (raises the weakest scores)
- **OpenTelemetry telemetry** — export gate events as OTel spans (agent id, intervention/violation rates) so
  observability is production-grade, not just `.vemo/telemetry.jsonl`. *(observability → 10)*
- **Transcript-level eval** — beyond mechanism-conformance (`vemo eval`), run an agent through scenarios and
  judge whether it actually hit the gates; report per-model-tier. A **governed-vs-ungoverned benchmark**.
- **Windows-native hooks** — `enforcement/hooks/run.py` exists; ship a `settings.win.json` and docs so Windows
  is first-class, not a fallback.

## Mid-term
- **More presets** (`go`, `rust`, `java`, monorepo) and a `vemo scope --add <glob>` to relieve false blocks.
- **Hierarchical AGENTS.md** for monorepos (closest-file-wins).
- **MCP integration** — expose VEMO state/gates as MCP tools.
- **Drift detection CI** — flag spec-vs-code divergence automatically.

## Longer-term
- **Multi-agent judge panel** wired as real subagents (the v1.6 design, made runnable end-to-end).
- **EU AI Act / NIST conformity evidence pack** generated from the audit trail (see `docs/COMPLIANCE.md`).
- **Formal-ish verification** of the highest-severity guards.

## Explicitly out of scope
- OS/container sandboxing (use a real sandbox; VEMO is a cooperative-host control surface — see `SECURITY.md`).
- Training-side governance (VEMO covers the *coding/deploy* lane, like Wildpanda).

> Want to move one up? Open an issue. The project governs itself with its own gates, so your PR is dogfood too.
