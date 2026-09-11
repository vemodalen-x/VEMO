# VEMO docs — index (organized by what you're trying to do)

> Organized with the [Diátaxis](https://diataxis.fr/) model: docs are grouped by *user need*
> (learn / do / look-up / understand), not by topic. Find your row, go.

| I want to… | Type | Go to |
|---|---|---|
| **通过 UI 安装、升级、诊断和卸载** | How-to | [INSTALL.md](INSTALL.md) · `python3 bin/vemo ui` |
| **开始第一次任务并验证结果** | Tutorial | [USAGE.md](USAGE.md) |
| **理解 Wildmeerkat lite 设计借鉴与治理取舍** | Explanation | [DESIGN_LITE.md](DESIGN_LITE.md) |
| **See the whole picture (usage + architecture diagrams)** | Visual guide | 🖼️ [GUIDE.html](GUIDE.html) |
| **Understand platform planes, policy decisions, evidence integrity, and request lifecycle** | Explanation + executable reference | [`docs/PLATFORM.md`](PLATFORM.md) · `vemo platform --json` |
| **Add or diagnose declarative capabilities and dependencies** | Reference + how-to | [EXTENSIONS.md](EXTENSIONS.md) · `vemo extensions --check --json` |
| **Get it working in 5 min** | Tutorial | [QUICKSTART.md](QUICKSTART.md) |
| **Migrate an existing agent playbook into VEMO** | How-to | [PLAYBOOK_ADOPTION.md](PLAYBOOK_ADOPTION.md) |
| **Run a Devpost-style hackathon build under a deadline** | How-to | [HACKATHON_PLAYBOOK.md](HACKATHON_PLAYBOOK.md) |
| **Design diagnostic coaching/tutoring agent flows** | How-to | [DIAGNOSTIC_PROMPTING.md](DIAGNOSTIC_PROMPTING.md) |
| **Understand how VEMO thinks** | Explanation | [MENTAL_MODEL.md](MENTAL_MODEL.md) |
| **Know why it works as models get stronger** | Explanation | [SCALING.md](SCALING.md) |
| **Run VEMO under another harness / other model vendors** | Reference | [ADAPTERS.md](ADAPTERS.md) |
| **Map controls to EU AI Act / NIST / OWASP** | Reference | [COMPLIANCE.md](COMPLIANCE.md) |
| **Map controls to the OWASP Agentic Top 10 (ASI01–10) + maturity model** | Reference | [OWASP_AGENTIC_TOP10.md](OWASP_AGENTIC_TOP10.md) |
| **Read the pitch / launch post** | — | [ANNOUNCEMENT.md](ANNOUNCEMENT.md) |
| **Threat model / roadmap** | Reference | [../SECURITY.md](../SECURITY.md) · [../ROADMAP.md](../ROADMAP.md) |
| **Look up a config knob or CLI verb** | Reference | [`vemo.config.yaml`](../vemo.config.yaml) (commented) · `vemo help` · `vemo explain <topic>` |
| **Do a specific thing** (auto mode, presets, blocked commit) | How-to | `vemo explain auto` / `presets` / `gates`; [README](../README.md) |
| **Know what changed between versions** | Reference | [CHANGELOG.md](../CHANGELOG.md) |

## The spec library (loaded just-in-time, not all at once)
`specs/` — `safety` (enforced rules) · `task` (lifecycle/tiers) · `verify` (acceptance + judge) ·
`concurrency` (multi-session) · `coding` (advisory) · `automation` (unattended mode). Routed by `specs/_manifest.yaml`.

## One-liners
```bash
vemo init --preset python   # set up        vemo status     # where am I
vemo explain tiers          # learn a term  vemo doctor     # health check
vemo auto on                # unattended    vemo budget status
```

> Doc-quality rule (Diátaxis): each doc has ONE job — a tutorial teaches, an explanation explains, reference
> describes. If a tutorial starts listing every flag, it's drifting; move that to reference.
