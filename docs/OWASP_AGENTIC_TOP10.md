# VEMO ↔ OWASP Top 10 for Agentic Security (ASI01–ASI10)

> Diátaxis: **reference**. Maps VEMO's controls to the canonical agentic risk taxonomy — the OWASP **Top 10 for
> Agentic Security** (Dec 2025), as framed in OWASP GenAI's *State of Agentic AI Security and Governance v2*
> (Jun 2026). Honest about partial coverage: VEMO is a deployment-layer control surface, not a sandbox or an
> MCP/registry scanner.

## ASI mapping
| ASI | Risk | VEMO control | Coverage |
|---|---|---|---|
| **ASI01** | Agent Goal Hijack (prompt injection) | **Rule-of-Two / lethal-trifecta gate** (v1.9) · scope containment · intent-narration monitoring · independent judge | strong |
| **ASI02** | Tool Misuse & Exploitation | destructive-command guard · scope · self-containment (agent can't auto-approve its own allowlist) | strong |
| **ASI03** | Identity & Privilege Abuse | `owning_chat` identity · least-privilege `scope_in` · CI ownership check | **partial** → cryptographic agent identity (L4) on roadmap |
| **ASI04** | Agentic Supply Chain | artifact provenance (`coding.spec`: content-hash + source commit) | **partial** → AIBOM/CycloneDX + MCP/skill-registry scanning on roadmap |
| **ASI05** | Unexpected Code Execution (RCE) | destructive-command guard · executed-ground-truth gate · self-containment | **partial** → VEMO is a cooperative-host control, *pair with OS/container sandbox* (`SECURITY.md`) |
| **ASI06** | Memory & Context Poisoning | repo-as-truth (durable, machine-readable task state) · provenance · narration | **partial** → persistent-memory-file integrity not fully solved |
| **ASI07** | Insecure Inter-Agent Communication | independent judge (separate context) · provenance | **partial** → A2A/MCP message auth on roadmap |
| **ASI08** | Cascading Failures | `run_budget` stop rules (bound blast radius) · scope · judge | **partial** |
| **ASI09** | Human-Agent Trust Exploitation | executed-ground-truth + evidence-completeness checks (catch "looks done" / metric-gaming) · judge prompted to *refute* · narration | strong |
| **ASI10** | Rogue Agents | kill switch (`vemo auto off` + `run_budget` hard-stop) · tamper-evident CI · identity | strong |

> Prioritization (per the report): lower adoption tiers focus on **ASI01 · ASI05 · ASI06**; AT6+ (external/multi-agent)
> must address the full surface with focus on **ASI04 · ASI07 · ASI08**. VEMO is strongest on ASI01/02/09/10 and
> explicitly partial on the multi-agent/supply-chain frontier — stated, not hidden.

## Where VEMO puts you on the Governance Maturity Model (L0–L4)
VEMO is, by design, the toolset for **Level 3 — Integrated, Continuous Oversight**, and a stepping stone to L4:

| Maturity action (report) | VEMO |
|---|---|
| Real-time monitoring / anomaly detection | telemetry (`.vemo/telemetry.jsonl`, gate events) — *baseline; OTel on roadmap* |
| Kill switches / autonomy controls | `vemo auto off` · `run_budget` hard-stop · capability/risk tiers ✅ |
| **Enforce governance via machine-readable policies** | hooks + CI + the validator reading machine-readable task state ✅ (this is VEMO's core) |
| Telemetry → observability platforms | gate-event log → OTel export (roadmap) |
| **L4: cryptographic agent identity / trust** | `owning_chat` today → cryptographic NHI identity (roadmap) |
| **L4: automated audit evidence / certification** | `vemo eval` conformance + `COMPLIANCE.md` mapping → auto evidence pack (roadmap) |
| **L4: self-adjusting policy/risk engines** | capability-monotonic governance (`capability.tier` derives ceremony/verification) — a concrete step toward adaptive |

## The two questions the report says decide your readiness
1. **"How fast can you see and stop a misaligned agent?"** → VEMO: `run_budget` hard-stop fires *in-loop* (seconds), `vemo auto off` kill switch, gate-event telemetry. (Regulators now assume seconds-to-minutes: DORA 4h notify, NIS2 24h, NY RAISE 72h, CA SB 53 15-day — all premised on continuous oversight, not periodic audit.)
2. **"How explicitly are autonomy and accountability coded into your systems?"** → VEMO: `capability.tier` + `risk_tiers` + `auto_mode` + machine-readable task front-matter + `owning_chat` = autonomy and accountability **as code**, not as a policy PDF.

> Net: VEMO is a Level-3 enabler today (machine-readable policy enforcement + kill switches + continuous gates),
> with a clear, honest path to Level 4 (cryptographic identity, automated audit evidence). Source: OWASP GenAI,
> *State of Agentic AI Security and Governance v2.01* (Jun 2026) — genai.owasp.org.
