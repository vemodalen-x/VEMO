# VEMO Skills — catalog & registry

> **How Claude Code uses these:** each `skill/<name>/SKILL.md` has YAML frontmatter; the `description` is what
> the agent matches on to **auto-invoke**, so it's written as "use when …". Deterministic steps live in
> `scripts/` and are loaded on demand (progressive disclosure) — the SKILL.md stays a thin contract.

## Active skills
| Skill | Use it to… | Trigger | Backed by |
|---|---|---|---|
| **call-graph** | who-calls / what-calls / chain / impact | auto (need call info) · "who calls / 调用链" | `scripts/cg.py` |
| **flow-discovery** | generate a flow doc from real call chains | auto (no flow covers the files) · "discover flow" | → call-graph |
| **docs-sync** | keep README / GUIDE / docs in sync | auto (release/contribute) · "update docs" | scans skills + version |
| **governance-sync** | pull template-owned updates from upstream | auto (session start) · "sync governance" | `scripts/govsync.py` + `gh` |
| **governance-contribute** | PR an improvement back upstream | manual · "contribute upstream" | `gh` |
| **governance-release** | cut a versioned release PR | manual · "cut a release" | `gh` + docs-sync |
| **automation-mode** | enter full-auto / unattended mode | manual · "enable auto mode" | `enforcement/automation/vemo-auto` |

## What I optimized vs Wildpanda (Claude Code engineer view)
Source: `wildpanda-seed/skill/` — 7 skills, **~1006 lines** of prose.

1. **Thin contracts, not manuals.** 130–213-line prose procedures → ~35-line SKILL.md (frontmatter · when ·
   steps · notes). A capable model doesn't need every `gh api` call spelled out — it needs *when to use this*
   and *where the deterministic part lives*. (Brevity beats encyclopedia; progressive disclosure.)
2. **Deterministic steps → real scripts.** Inline shell-as-prose became tools: `cg.py` (call-graph engine,
   Q1–Q5) and `govsync.py` (upstream version/commit diff). A tool is verifiable, testable, and "can't
   hallucinate" — the same principle as VEMO's enforcement hooks, applied to skills.
3. **Sharper `description` frontmatter** → better, less accidental auto-invocation (each says *exactly when*).
4. **Composable, single-responsibility.** call-graph is the low-level utility; flow-discovery depends on it;
   **docs-sync is the single owner of doc edits** (release/contribute delegate to it). No duplicated logic.
5. **Capability-aware.** Notes tell the agent to prefer the tool even when a strong model *could* infer
   (ground truth > inference). Governance skills respect the template/instance boundary.
6. **Integrated with VEMO.** Skills reference `vemo`, the validator, and the template-owned boundary; release
   runs docs-sync; all transient output lands in `.vemo/` (gitignored).
7. **Dropped/merged the superseded.** `bootstrap-governance` (PowerShell onboarding) → replaced by
   `vemo init --preset` + `enforcement/install.sh` (one command, cross-platform). `readme-update` →
   generalized into `docs-sync`.

**Net:** same coverage as Wildpanda's 7 skills at roughly a **quarter of the prose**, with the hard parts now
**tools instead of instructions**, and two genuinely runnable scripts where there were none.
