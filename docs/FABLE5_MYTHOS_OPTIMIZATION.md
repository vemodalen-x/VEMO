# VEMO v1.3 — optimization driven by Fable 5 / Mythos analysis

> Source discipline: model facts below are drawn from vendor + reputable-blog coverage (Anthropic, Azure,
> Databricks, Vellum, CodeRabbit, MindStudio). **GitHub "Mythos protocol" repos are explicitly flagged by
> the search results as "leaked"/speculative/unofficial** — their *ideas* are used as design inspiration,
> never cited as authoritative Anthropic behavior. Verify against your own workload before trusting any number.

## 1. What the analysis says

### Claude Fable 5 (GA 2026-06-09) — first "Mythos-class" model, a tier above Opus 4.8
- **Long-horizon autonomy is the headline**: runs agents for *days* unattended; plans across stages;
  delegates to sub-agents; **writes its own tests and checks its own work**; uses vision to verify outputs.
- Benchmarks: SWE-bench Pro 80.3% vs Opus 4.8 69.2%; "the longer/more complex the task, the larger the lead."
- **Persistent file-based memory** multiplied its gains (~3× vs Opus on a long task) — it improves using notes it keeps.
- **Cost**: $10/$50 per Mtok (≈2× Opus 4.8), ~30% slower, ~2.5× output tokens. "Using a Mythos-class model
  for single-turn chat is like renting a truck to deliver a letter."
- **⚠ Governance-critical caveat**: it "**keeps working until the harness cuts it off**" → it needs **strong
  stop rules**; "workflow design (checkpoints, stop rules, context management) matters as much as model choice."
- **⚠ Documented failure mode**: while monitoring a release it reported "no error movement at all" after
  checking **one** error type — and **undercounted the real incident 20×**. A confident, evidence-incomplete
  self-assessment.

### Claude Mythos / "Mythos-class"
- Mythos = Anthropic's restricted (Project Glasswing) cybersecurity frontier model; "Mythos-class" is the
  capability tier; **Fable 5 is the GA Mythos-class model**.
- Agent-design lesson: "**assign the proper models to the proper positions** — cheap/fast models for most of
  the work, frontier only where scale is needed" is the best cost/capability balance.
- Microsoft's multi-agent **MDASH** (100+ specialized agents, multi-model) *beat* single-model Mythos on
  CyberGym (88.45% vs ~83%) → for hard work, **orchestrated multi-agent > one big model**.

### Community GitHub (inspiration only — provenance uncertain)
- `mythos-router`: "**Strict Write Discipline**" — path validation, **pre/post snapshots, hash verification,
  rollback on failed verification, and receipts**; plus "burn cheap-model tokens for cheap work, frontier
  only for deep reasoning."
- `mythos-agent`: **hypothesis-driven** security review ("what COULD go wrong" — race conditions, timing
  attacks) and CVE-variant analysis.

## 2. How it maps to VEMO changes (v1.3)

| Finding | VEMO v1.3 change | File |
|---|---|---|
| Fable 5 is a tier *above* Opus | **New `frontier` capability tier** (above `high`) — least prescriptive ceremony, lean on the model's own tests/self-checks | `vemo.config.yaml`, `specs/task.spec.md` |
| "Runs until cut off"; needs stop rules | **Run budget / stop rules** (max tool-calls, files, wall-clock, checkpoint cadence), **mechanically enforced** — *hard-stop when unattended (auto mode), advisory when a human is present* | `vemo.config.yaml` `run_budget`, `enforcement/hooks/guard-budget.sh`, `task_state.py budget-tick` |
| Route-by-task; frontier is 2× cost | **Frontier-aware model routing** — `claude-fable-5` for long-horizon/migration/R2 only; cheap models for the rest; cost note | `vemo.config.yaml` `model_routing` |
| 20× undercount blind spot | **Evidence-completeness check** in the judge — verify the evidence covers the *full* claim scope, not a convenient subset | `specs/verify.spec.md`, `agents/governance-judge.md` |
| Multi-agent > single model (MDASH) | Reaffirms VEMO's judge-as-separate-agent; note frontier work *still* gets an independent judge | `specs/verify.spec.md` |
| Strict Write Discipline (inspiration) | Long-horizon auto runs keep a **checkpoint/receipt trail**; budget enforces checkpoint cadence | `run_budget.checkpoint_every_calls`, `.vemo/` |

## 3. The through-line
Stronger autonomous models do **not** mean *less* governance — they shift the risk from "the model can't do
it" to "the model will do too much, confidently, unattended." So v1.3 *removes prescriptive step-by-step
ceremony at the `frontier` tier* (trust the model to plan and self-test) while *adding hard stop rules,
checkpoints, frontier-aware routing, and a completeness-checking judge*. This is the exact pairing the
analysis calls for — and it is most important precisely because VEMO v1.2 added an unattended **auto mode**:
a days-long Fable-5 auto run without a budget is the canonical "runs until the harness cuts it off" failure.

## Sources
- Anthropic — [Claude Fable](https://www.anthropic.com/claude/fable)
- Azure — [Fable 5 in Microsoft Foundry: next era of autonomous agents](https://azure.microsoft.com/en-us/blog/claude-fable-5-is-now-available-in-microsoft-foundry-powering-the-next-era-of-autonomous-agents/)
- Databricks — [Fable 5 on Databricks (Unity AI Gateway)](https://www.databricks.com/blog/claude-fable-5-now-available-databricks-fully-governed-through-unity-ai-gateway)
- Vellum — [Fable 5 & Mythos 5 benchmark breakdown](https://www.vellum.ai/blog/claude-fable-5-and-mythos-5-benchmarks-explained)
- CodeRabbit — [Fable 5 model review (cost / "runs until cut off")](https://www.coderabbit.ai/blog/fable-5-model-review)
- MindStudio — [Fable 5 for long-running agentic coding: real-world results](https://www.mindstudio.ai/blog/claude-fable-5-agentic-coding-real-world-results)
- TrueFoundry — [Fable 5 vs Opus 4.8: when to use each](https://www.truefoundry.com/blog/claude-fable-5-vs-opus-4-8-benchmarks-pricing-when-to-use-each)
- GeekWire — [Microsoft MDASH multi-agent tops Mythos on CyberGym](https://www.geekwire.com/2026/microsofts-multi-agent-ai-system-tops-anthropics-mythos-on-cybersecurity-benchmark/)
- Giskard — [Analyzing Claude Mythos (AI security)](https://www.giskard.ai/knowledge/claude-mythos-analyzing-anthropics-new-frontier-model-for-ai-security)
- ⚠ Inspiration, provenance uncertain: [github topics: mythos](https://github.com/topics/mythos), `mythos-router` (described by search as a "leaked protocol" — treat as community idea only)
