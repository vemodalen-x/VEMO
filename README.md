<div align="center">

<img src="assets/logo.svg" alt="VEMO logo" width="128" />

# VEMO

### Velocity-first · Enforced · Model-aware Orchestration

**Governance for AI coding agents that *accelerates* developers — mechanism over prose, and it *proves* its gates fire.**

![version](https://img.shields.io/badge/version-1.8.0-0d9488?style=for-the-badge)
![conformance](https://img.shields.io/badge/conformance-9%2F9-16a34a?style=for-the-badge)
![license](https://img.shields.io/badge/license-MIT-3b82f6?style=for-the-badge)
![deps](https://img.shields.io/badge/core%20deps-none-0891b2?style=for-the-badge)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-7c3aed?style=for-the-badge)](https://github.com/vemodalen-x/VEMO/pulls)
[![Stars](https://img.shields.io/github/stars/vemodalen-x/VEMO?style=for-the-badge&color=f6c915)](https://github.com/vemodalen-x/VEMO/stargazers)

[Why](#-why-vemo) · [Quickstart](#-quickstart) · [Architecture](#-architecture) · [CLI](#-the-vemo-cli) · [Docs](#-documentation) · [The name](#-the-name) · [Credits](#-credits)

<img src="assets/demo.svg" alt="vemo eval → 9/9 conformance; an out-of-scope edit blocked (exit 2)" width="760" />

</div>

---

> **What it is, plainly:** a small set of Markdown specs + thin scripts you drop into any repository. It works
> with any agent harness that can read Markdown and run hooks (Claude Code, etc.). **Core dependencies: none**
> — Markdown + YAML + a little stdlib Python. The governance skills/CLI use the [GitHub CLI](https://cli.github.com/).

## ✨ The name

VEMO is named after **vemödalen** — a word coined by John Koenig in *The Dictionary of Obscure Sorrows*:

> *“the frustration of photographing something amazing when thousands of identical photos already exist — the
> same sunset, the same waterfall — each one a thumbprint in an endless mosaic of indistinguishable snapshots.”*

It's the right name for an era when AI agents generate **oceans of plausible, look-alike, untraceable code**.
VEMO is the layer that makes every change **intentional, verified, and traceable** — so your codebase isn't
just one more indistinguishable snapshot.

And in that same spirit, VEMO is honest about its own originality: it stands on public best practices and its
real contribution is making good, known patterns **mechanical** instead of merely written down. (See [Credits](#-credits).)

## 🤔 Why VEMO

AI coding agents are powerful but **stateless and eager**. Left ungoverned, the failure modes are predictable:

| Problem | Ungoverned | VEMO's answer |
|---|---|---|
| 🔄 Lost context across sessions | repeats work, contradicts past decisions | repo *is* the memory — durable task state in machine-readable front-matter |
| ⚡ Two sessions edit the same file | silent clobber | `chat_id` + heartbeat + takeover protocol (and a CI ownership check) |
| 🚫 Ships unverified | "looks done" merges | acceptance gates + an **independent judge** on critical work |
| 📉 Rule drift | rules live only in someone's head | rules live in the repo; the critical ones are **enforced by hooks/CI** |
| 🏃 Runaway autonomy | a long-horizon model "runs until cut off" | **run-budget stop rules** — hard-stop when unattended |

The thread: **the rules that matter are mechanism, not hope.** A "hard gate" written only as prose is a gate
that fails the moment the model doesn't read it.

## 🚀 What you get — five shifts

| # | Most frameworks | VEMO |
|---|---|---|
| 1 | Gates are **prose** the model may ignore | **Mechanically enforced** (hooks + CI backstop) — they can't be argued with |
| 2 | **Front-load** every spec each session | **Just-in-time** loading — only the specs a task needs |
| 3 | **One** ceremony level for everything | **Risk-tiered**: R0 fast · R1 standard · R2 critical |
| 4 | Ceremony is a **constant** | **Scales with your model** (`capability.tier`: frontier→low) |
| 5 | Agent **self-reports** "done" | An **independent judge** verifies high-risk gates |

## ⚡ Quickstart

```bash
# 1) drop VEMO into your repo
cp -r VEMO/{AGENTS.md,vemo.config.yaml,specs,enforcement,agents,tasks,bin,presets} your-repo/ && cd your-repo

# 2) one command — installs hooks + git pre-commit, preconfigures build/test for your stack
python3 bin/vemo init --preset python        # or: node | cpp | docs   (--dry-run to preview)
export PATH="$PWD/bin:$PATH"                  # so you can just type `vemo`

# 3) start a task, set its scope, then code — out-of-scope edits are now blocked automatically
cp tasks/_TASK_TEMPLATE.md tasks/T-myfeature.md   # set  scope_in: ["src/feature/**"]  risk: R1
vemo status                                       # where am I?    vemo explain gates
```

**The "aha":** ask your agent to edit a file outside `scope_in` — the hook blocks it. You didn't have to police it.

▶ Full walkthrough: **[docs/QUICKSTART.md](docs/QUICKSTART.md)** · the model in 5 ideas: **[docs/MENTAL_MODEL.md](docs/MENTAL_MODEL.md)** · 🖼️ visual guide + diagrams: **[docs/GUIDE.html](docs/GUIDE.html)**

## 🧭 Architecture

Five layers — the lower you go, the more it's *enforced mechanism* rather than *advisory prose*:

<p align="center"><img src="assets/architecture.svg" alt="VEMO layered architecture" width="760" /></p>

```
┌ AGENTS.md ───────────── thin router: loads config + safety, then JIT-loads the rest   (prose)
├ vemo.config.yaml ────── the ONE file you edit: tier · routing · risk_tiers · budget    (config)
├ specs/ ──────────────── safety · task · verify · concurrency · coding · automation     (prose, JIT)
├ enforcement/ ────────── ⛨ hooks (client) + CI pre-commit (server) + validator      ◀── MECHANISM
└ agents/ · eval/ · bin/  governance-judge · conformance scenarios · the `vemo` CLI      (verify · tooling)
```

Enforcement is **defense-in-depth** — a gate never depends on the agent's goodwill:

```
agent → ⛨ PreToolUse hook → action runs → git commit/push → ⛨ CI / pre-commit → ✓ main
         scope·cmd·secret·budget            (if allowed)        tier·R2 judge·acceptance
         (fast, client-side)                                    (authoritative; --no-verify can't pass it)
```

🖼️ **Rich, color diagrams** (layered stack, request lifecycle, the two-walls pipeline, and a risk×capability
ceremony matrix) are in **[docs/GUIDE.html](docs/GUIDE.html)**.

## 🔧 The `vemo` CLI

One verb-based entry point (run `vemo` for the map, `vemo explain <topic>` to learn a concept in one line):

| Command | Does |
|---|---|
| `vemo init [--preset python\|node\|cpp\|docs]` | set up VEMO in this repo (preset + hooks + tasks/) |
| `vemo status` | plain-language dashboard: tier · enforcement · budget · auto mode · active task |
| `vemo doctor` | health check (config, hooks, tools) |
| `vemo selfcheck` | framework internal-consistency lint |
| `vemo eval` | run the executable conformance harness (writes `eval/out/report.json`) |
| `vemo explain <topic>` | `tiers · gates · auto · budget · judge · capability · presets` |
| `vemo auto on\|off\|status` | full-auto (unattended) mode — records every decision; OFF by default |
| `vemo budget status\|reset` | run-budget / stop rules |
| `vemo tier <paths…>` / `vemo check <path>` | required risk tier / is a path in scope? |

## 🧩 Skills

Reusable, script-backed procedures the agent auto-invokes by their frontmatter `description` (catalog: [skill/_catalog.md](skill/_catalog.md)):

| Skill | For |
|---|---|
| `call-graph` | who-calls / what-calls / chains / impact (tool-backed: `cg.py`) |
| `flow-discovery` | generate a flow doc from real call chains |
| `docs-sync` | keep README / GUIDE / docs in sync |
| `governance-sync` · `-contribute` · `-release` | pull upstream updates · PR improvements back · cut a release |
| `automation-mode` | enter full-auto (unattended) mode |

> Skills are intentionally thin: contracts stay readable, deterministic work lives in scripts, and release-time
> documentation updates are routed through `docs-sync`.

## 📚 Documentation

Organized by need ([Diátaxis](https://diataxis.fr/)): **learn → do → look-up → understand.**

| I want to… | Go to |
|---|---|
| See the whole picture (usage + architecture diagrams) | 🖼️ [docs/GUIDE.html](docs/GUIDE.html) |
| Get working in 5 minutes | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| Understand how VEMO thinks | [docs/MENTAL_MODEL.md](docs/MENTAL_MODEL.md) |
| Find the right doc fast | [docs/INDEX.md](docs/INDEX.md) |
| Threat model · roadmap · the 3-round critique | [SECURITY.md](SECURITY.md) · [ROADMAP.md](ROADMAP.md) · [docs/CRITIQUE_LOG.md](docs/CRITIQUE_LOG.md) |
| Look up config / changes | [vemo.config.yaml](vemo.config.yaml) · [CHANGELOG.md](CHANGELOG.md) |

## 🌱 Credits

VEMO combines public patterns from agent governance, spec-driven development, documentation architecture, and
long-horizon model safety. It openly credits the best practices it stands on:

- **[GitHub Spec Kit](https://github.com/github/spec-kit)** — `init` + preset ergonomics, spec-driven workflow.
- **[12-Factor Agents](https://github.com/humanlayer/12-factor-agents)** — own-your-context, stateless reducer.
- **[AGENTS.md](https://agents.md/)** + Anthropic's *context engineering* — thin, just-in-time entry.
- **[Diátaxis](https://diataxis.fr/)** — docs organized by user need.
- Fable 5 / Mythos analysis (2026) — the run-budget stop rules and the evidence-completeness judge check.

> See [docs/FABLE5_MYTHOS_OPTIMIZATION.md](docs/FABLE5_MYTHOS_OPTIMIZATION.md) for the model-scaling trail, including notes on which sources are speculative.

## 🤝 Contributing

PRs welcome. VEMO **governs itself** — changes flow through its own task lifecycle, and the same hooks/CI that
protect consumers protect this repo. See **[CONTRIBUTING.md](CONTRIBUTING.md)**. Good first contributions:
a new `presets/<stack>.yaml`, a new `eval/` scenario, or a Windows hook runner.

## ⭐ Star history

<a href="https://star-history.com/#vemodalen-x/VEMO&Date"><img src="https://api.star-history.com/svg?repos=vemodalen-x/VEMO&type=Date" width="560" alt="Star history chart" /></a>

If a governance framework that *proves* it works (and tells you where it doesn't) is what you've been missing — a ⭐ helps others find it.

## 📄 License

[MIT](LICENSE) © 2026 The VEMO Authors.

## ⚠️ Status

**v1.8.0 — active.** VEMO is a framework of specs + thin scripts; treat it as a starting skeleton you tune via
`vemo.config.yaml`. Model names referenced in defaults (Opus 4.8, Fable 5, Mythos) reflect 2026 Anthropic
releases — swap them freely for whatever you run.

<div align="center"><sub>governance that gets out of your way — until it shouldn't.</sub></div>
