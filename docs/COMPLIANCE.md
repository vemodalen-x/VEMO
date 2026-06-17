# VEMO controls ↔ 2026 governance standards

> Diátaxis: **reference**. VEMO is not a legal-compliance product, but it provides the *technical control
> substrate* that the 2026 standards require — logging/traceability, human oversight by design, least-privilege,
> and a kill switch. This maps VEMO's mechanisms to those expectations so a consuming team can show its work.

## The four guardrail elements (the canonical 2026 framing)
| Element | VEMO mechanism |
|---|---|
| **Permission** (least-privilege) | `scope_in` containment (hook+CI) · third-party exclusions · forbidden destructive/out-of-repo commands |
| **Approval** (human-in-loop) | plan/review gates by risk tier · human retained for intent + irreversible (`capability.spec`) |
| **Audit trail** | machine-readable task front-matter · `.vemo/telemetry.jsonl` gate events · `auto_decisions.jsonl` · executed-evidence logs |
| **Kill switch** | `vemo auto off` · `run_budget` hard-stop when unattended · `enforcement.mode: monitor` to fall back to observe-only |

## Standards mapping
| Standard (2026) | What it asks | VEMO control |
|---|---|---|
| **EU AI Act** high-risk (Aug 2, 2026) | automatic logging, traceability, human oversight by design, conformity process | telemetry + task audit trail; human gates; `eval/run.py` conformance + `selfcheck` |
| **NIST AI RMF** | risk-tiered controls, measurable governance, documentation | `risk_tiers` (R0/R1/R2) + `capability.tier`; executable eval; specs as docs |
| **OWASP LLM Top-10** | LLM01 prompt-injection · LLM06 excessive agency · LLM08 (gaming) | narration monitoring + sandboxed scope; `run_budget` + scope + kill-switch bound agency; tamper-evident CI + provenance |
| **MS Agent Control Spec (ACS)** | portable runtime control + observability | hooks + CI as policy-as-code; gate-event telemetry; verdicts recorded |
| **Action chaining** (emerging risk) | low-risk + high-risk actions chained autonomously | destructive-command guard + scope guard fire per action; R2 + judge gate the high-risk step |

## Rollout posture (best practice: monitor → enforce)
`enforcement.mode: monitor` runs the guards in **observe-only** (log, don't block) for onboarding/tuning;
flip to `enforce` once the policy is calibrated. Safety-critical guards still log everything in monitor mode,
so you get the audit trail before you commit to blocking — matching the "start in monitoring mode" consensus.

## Honest scope
VEMO gives you the *controls and the evidence*; it does not certify legal compliance, and it is young
(see the analysis docs). For regulated/high-risk deployment, pair it with your org's conformity process.

## Sources
- [Galileo — AI governance framework](https://galileo.ai/blog/ai-governance-framework) · [Arthur — AI governance 10-step](https://www.arthur.ai/column/ai-governance-framework-guide)
- [MS Foundry — Open Trust Stack / Agent Control Specification](https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/) · [GitHub Well-Architected — governing agents](https://wellarchitected.github.com/library/governance/recommendations/governing-agents/)
- [Coderio — guardrails: permission/approval/audit/kill-switch + policy-as-code](https://www.coderio.com/blog/expertise/advanced-technologies/agent-guardrails-101-permissions-tool-scopes-audit-trails-policy-code/) · [MLflow — production-ready agents 2026](https://mlflow.org/articles/building-production-ready-ai-agents-in-2026/)
