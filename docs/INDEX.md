# VEMO docs — index (organized by what you're trying to do)

> Organized with the [Diátaxis](https://diataxis.fr/) model: docs are grouped by *user need*
> (learn / do / look-up / understand), not by topic. Find your row, go.

| I want to… | Type | Go to |
|---|---|---|
| **See the whole picture (usage + architecture diagrams)** | Visual guide | 🖼️ [GUIDE.html](GUIDE.html) |
| **Get it working in 5 min** | Tutorial | [QUICKSTART.md](QUICKSTART.md) |
| **Understand how VEMO thinks** | Explanation | [MENTAL_MODEL.md](MENTAL_MODEL.md) |
| **Know why it works as models get stronger** | Explanation | [SCALING.md](SCALING.md) |
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
