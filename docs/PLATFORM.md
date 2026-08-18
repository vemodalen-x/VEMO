# VEMO platform architecture

VEMO is an AI-governance middle platform: adapters bring requests in, control logic resolves the operating
context, policy defines the boundary, agents and skills do the work, enforcement decides what may proceed,
and evidence makes important claims reviewable. The existing repository-layer diagram explains deployment;
this document explains responsibility and ownership.

The executable view is the source for topology IDs and locally observable installation facts:

```bash
vemo platform
vemo platform --json
vemo platform --check
```

All forms are read-only. The JSON form emits relative component paths, structural relationship outcomes, and
three allowlisted operational values (VEMO version, capability tier, and enforcement mode). It may inspect
allowlisted hook structure and receipt references, but never emits command bodies, source, prompts, evidence
or telemetry payloads, credentials, or the absolute checkout path. `--check` uses the same report and exits
non-zero when its local integration contract fails.

## Responsibility planes

| Plane | Owns | Primary contract | Does not own |
|---|---|---|---|
| `ingress` | Portable agent entry and harness normalization | `AGENTS.md`, `docs/ADAPTERS.md` | Policy decisions or channel-specific business logic |
| `control` | Session orientation, task/risk classification, lifecycle, Fleet orchestration | `bin/vemo`, `task_state.py`, product/Fleet modules | Permission to bypass a gate |
| `policy` | Configuration and just-in-time safety/lifecycle rules | `vemo.config.yaml`, `specs/` | Runtime evidence or enforcement claims |
| `execution` | Bounded agents, skills, and conformance scenarios | `agents/`, `skill/`, `eval/` | Self-authorizing or self-certifying completion |
| `enforcement` | Agent-loop, Git, and CI decisions | `enforcement/` | Product intent or remote branch-protection truth |
| `evidence` | Durable task state, receipts, judge provenance, telemetry | `tasks/`, `.vemo/` evidence files | Granting authority merely because a record exists |

Each component has one primary plane. Other planes may consume it, but ownership does not move. This keeps a
channel adapter from becoming a policy engine and keeps a dashboard from becoming an enforcement authority.

`vemo platform --json` reports each component as `required` or optional and keeps its materialization explicit:

| Materialization | Meaning |
|---|---|
| `source` | A versioned definition or implementation; never confused with proof that it ran |
| `durable_record` | Reviewable task or provenance memory that survives a run |
| `runtime_artifact` | A generated local observation such as a receipt or telemetry file; never source authority |

Missing receipts or telemetry mean “not produced yet,” not “the platform core is broken.” This source/artifact
split prevents a generated file from silently becoming configuration and prevents source presence from being
reported as runtime evidence.

## Capability seams

DeepSeek Harness models replaceable behavior around explicit services and publishes the owner,
implementations, and direct consumers of each service. VEMO adopts the smaller governance equivalent: every
declared seam has a `definition`, `provider`, and `consumer`, while continuing to let the external harness own
its agent loop.

| Seam | Definition | Provider | Consumer | Provider policy |
|---|---|---|---|---|
| `ring1_guard` | Canonical hook map | `.claude/settings.json` or `.codex/hooks.json` | Unified hook dispatcher | Optional until a harness adapter is installed; human-facing adapter docs remain optional |
| `verification_evidence` | Verification spec | `task_state.py` receipt producer | Pre-push or CI backstop | Required core capability |

A ring-1 seam with no installed provider is `available`, not broken. Once a provider file exists, VEMO treats
it as an active claim and validates its relationship to the definition and consumer. A missing required role
is `incomplete`; a complete row still means “the composition is wired,” not “the behavior executed.”

## Relationship invariants

DeepSeek Harness makes an important distinction: runtime invariants should protect observable relationships,
not merely confirm that a package, method, or plugin exists. VEMO applies that rule to the two relationships
it can inspect locally without taking authority from the existing gates:

- `ring1_adapter_binding` derives event/action bindings from the canonical hook map and each installed adapter.
  It passes only when every canonical binding reaches the shared dispatcher. It emits counts and stable failure
  codes, never the commands themselves.
- `verification_receipt_chain` checks that an observed receipt is valid JSON, names a safe task record, and
  points to a non-empty evidence log under `.vemo/run/`. It checks referential integrity without reading log
  content or reimplementing the push gate's fingerprint and acceptance rules.

An absent optional adapter or receipt is `not_observed`. A present but malformed, incomplete, unsafe, or
dangling relationship is `fail`. `vemo platform --check` exits non-zero when a required component or seam is
incomplete, or when one of these observed relationships fails. It does not fail merely because local Git hooks
are absent or remote branch protection cannot be observed.

These checks deliberately remain narrower than behavioral proof. `doctor`, the conformance eval, `vemo
verify`, Git gates, and CI still own execution health and acceptance; the platform command owns only the
composition and artifact relationships it reports.

## Request lifecycle

The machine-readable lifecycle is ordered and names the plane responsible for each outcome:

1. `ingest` — ingress normalizes the request into a portable envelope.
2. `orient` — control returns the session brief and continuity state.
3. `classify` — control resolves task type, risk tier, and capability posture.
4. `resolve_policy` — policy supplies the just-in-time rules and allowed scope.
5. `authorize` — enforcement allows the action or blocks it fail-closed.
6. `execute` — an agent, skill, or tool produces bounded work.
7. `prove` — evidence records task state, receipts, telemetry, and judge provenance.
8. `deliver` — Git and CI enforcement decide whether the change may advance.

This is a control loop, not a one-way conveyor. A blocked action returns to control for a scoped correction;
a failed verification returns to execution with the failure preserved in evidence.

## Authority boundaries

VEMO reports only what the local checkout can prove:

| Ring | Local observation | Authority claim |
|---|---|---|
| Agent loop | Adapter config exists and its canonical bindings resolve to the shared dispatcher | Static wiring is valid; `doctor`/eval still prove execution health |
| Git | both local pre-commit and pre-push gate files exist | Local gate files are present; their execution remains a separate fact |
| CI | `.github/workflows/vemo-ci.yml` exists | A server-backstop workflow is present in the repository |

The resulting delivery posture is `advisory`, `local_gates`, or `ci_backstop_present`. Even the last value does
not claim that a remote host requires the check: branch protection is always reported as
`not_locally_verified`. VEMO becomes authoritative only when the repository host actually requires the CI
check on protected branches.

The platform command is therefore a preflight and integration contract, not a compliance certificate. It is
safe for local dashboards and adapter diagnostics. Schema version `2` adds materialization, capability seams,
relationship invariants, and check status; the version must change again when field meaning or stable IDs
change incompatibly.

## What was learned from DeepSeek Harness

The comparison used DeepSeek Harness's official [architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md),
[capability seam map](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/capability-seams.md),
and [invariant service](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/runtime-diagnostics/invariants).
Four patterns transfer cleanly to VEMO:

- make extension roles explicit as Definition/Provider/Consumer instead of calling a directory an integration;
- expose the composition that actually binds a capability, not only the intended architecture;
- assign each invariant to the relationship its owner can authoritatively observe;
- keep source definitions, durable records, and generated runtime artifacts distinct.

VEMO does not import Cordis or turn every governance module into a plugin. DeepSeek Harness is an execution
harness whose reversible effects and typed events support hot composition; VEMO is a lightweight,
model-neutral governance layer that must work beside several external harnesses. Its existing adapters, task
state, Git gates, and CI backstop are the right extension points. The optimization is therefore stronger
contracts and executable relationship checks, not a second agent runtime.

## What was learned from Wildmeerkat

The comparison with Wildmeerkat's AIIGovernance architecture contributed four useful patterns:

- make ingress, orchestration, normative policy, hard gates, and records visibly separate;
- route and preflight before launching domain execution;
- treat health and verification as read-only observable facts, not optimistic claims;
- make records/evidence a first-class plane instead of a by-product.

VEMO deliberately retains different choices where its operating model needs them:

- no mandatory central leader or single shared-file writer; session binding, scoped tasks, and Git handle
  concurrent coding work without introducing an orchestration bottleneck;
- no channel-specific bridge in Core; adapters implement the portable contract and must carry executable
  conformance checks before VEMO claims support;
- no prose-only judicial layer; critical claims use receipts and independent judge provenance enforced by
  Git/CI;
- no inference of remote authority, secret safety, or runtime health from a diagram or a local config file.

The result keeps Wildmeerkat's architectural clarity while preserving VEMO's model-neutral, multi-session,
mechanism-first design.
