# Changelog

All notable changes to VEMO are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/); versioning: [SemVer](https://semver.org/).

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
