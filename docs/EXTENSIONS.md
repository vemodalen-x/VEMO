# VEMO extension composition

VEMO extensions are versioned JSON contracts that add capabilities and platform topology without adding a
second runtime. The resolver is deliberately read-only: it validates manifests, resolves dependencies, and
publishes an inspectable composition report. It never imports an extension module or runs a command from a
manifest.

```bash
vemo extensions
vemo extensions --json
vemo extensions --check
```

`--check` exits `0` only when the activation index, every active manifest, capability ownership, dependency
graph, and contribution set resolve without an issue. It exits `2` on an invalid composition.

## Design contract

### Composition modules

The composition core is split by lifecycle responsibility instead of living behind one registry module:

| Module | Owns | Does not own |
|---|---|---|
| `vemo_composition.contracts` | manifest schema, safe identifiers/paths, typed contribution validation | dependency order or filesystem discovery |
| `vemo_composition.context` | `CompositionContext`, capability resolution, child inheritance, `EffectScope` teardown | JSON/file loading |
| `vemo_composition.loader` | activation-index discovery, bounded reads, `ExtensionLoader` reconciliation | contribution schemas or platform behavior |
| `vemo_extensions.py` | backward-compatible exports and CLI rendering | composition algorithms |

The façade is intentionally thin. A caller can keep using `ExtensionRegistry` and
`build_extension_report()` while new integrations depend on the narrower component they actually need.

### Stable capabilities

An extension declares stable capability keys in `provides` and dependencies in `requires`. Consumers depend
on a key such as `vemo.platform`, not on a Python file or implementation class. VEMO activates an extension
only after every required capability is available, then exposes the deterministic order in `load_order`.

The host currently provides `vemo.platform`. A capability may have exactly one provider. VEMO rejects
duplicates rather than introducing an implicit override order.

`CompositionContext.fork()` creates a child context that inherits the parent's currently active capability
keys, not copies of its registrations. If the parent provider is disposed, the next child resolution reacts
by moving the dependent extension to `waiting`. Parent failures propagate fail-closed through
`parent_context_invalid`.

### Reversible registration

The in-memory `ExtensionRegistry.register()` operation returns an idempotent disposer. Calling it removes
only that registration; resolution then recomputes downstream waiting or failure states. This keeps registry
effects locally reversible and testable even though the user-facing CLI is a short-lived process.

`EffectScope` groups related disposers, runs them once in reverse registration order, and continues teardown
before reporting an error. Scoped teardown never removes registrations owned by another scope. The trusted
internal `CompositionContext.effect()` API accepts an installer that returns a disposer; the declarative
manifest loader never derives or invokes an installer from JSON.

JSON manifests themselves are immutable inputs during a run. Edit the manifest or activation index and run
the command again to reconcile the composition.

`ExtensionLoader.reconcile()` embodies that boundary for long-lived callers. Every valid normalized manifest
has a semantic fingerprint and its own effect scope. A reconciliation retains unchanged registrations by
identity, mounts added or changed scopes, then disposes changed or removed old scopes in reverse prior mount
order. `close()` performs the same reverse teardown while leaving caller-owned registrations intact.

Each loader report includes a `reconciliation` object with `attempt`, successfully applied `revision`,
`status`, and deterministic `added` / `retained` / `changed` / `removed` source lists:

- `applied` means a valid initial set or delta became active;
- `noop` means the valid set was unchanged and no registration was remounted;
- `deferred` means the activation index itself was missing, unreadable, malformed, or used an unsupported
  schema. The loader retains its last valid registrations, reports `applied: false`, and emits
  `reconciliation_deferred`; the overall check still fails.

A bad individual manifest is isolated rather than treated as an index-wide outage: that source's old effect
is removed, other unchanged sources retain identity, and the manifest diagnostic keeps the report failing.
This distinction prevents a transient control-file failure from tearing down a known-valid long-lived
composition while ensuring invalid manifest data never becomes active.

### Typed contribution points

A `ContributionSpec` owns one stable contribution key, item validator, identity function, per-manifest/total
limits, and diagnostic codes. The context aggregates active items generically through registered specs; the
dependency resolver and filesystem loader do not know platform-seam fields. Adding another declarative
contribution kind therefore means registering a trusted spec and implementing its owning consumer, not
editing the composition algorithms.

Contribution specs are normal reviewed VEMO code. Their validators execute because the host explicitly
registers them; a manifest can only select data under already-registered keys and cannot name a validator.

### Activation index

[`extensions/index.json`](../extensions/index.json) is the explicit active set. Each entry is a normalized
path below `extensions/` ending in `/extension.json`:

```json
{
  "schema_version": 1,
  "extensions": [
    "ring1-guard/extension.json",
    "verification-evidence/extension.json"
  ]
}
```

The list enables manifests; it is not the boot order. `requires`/`provides` determine ordering, with extension
ID as the stable tie-breaker. A referenced missing file fails closed, so deleting a manifest cannot silently
erase a required platform contract.

### No code loading

The loader accepts JSON data only. There is no `entrypoint`, module name, shell command, hook body, expression,
or dynamic import field. Files are bounded in size, duplicate JSON keys are rejected, and symlinks or paths
outside the checkout are rejected before their contents are read.

A manifest can describe topology; it cannot grant permission, register an enforcement hook, or prove that a
provider executed. Existing scope guards, Git gates, receipts, judge provenance, and CI retain their authority.

## Manifest schema v1

Every manifest has exactly these top-level fields:

```json
{
  "schema_version": 1,
  "id": "example.audit-view",
  "name": "Audit view",
  "version": "1.0.0",
  "provides": ["example.audit-view"],
  "requires": ["vemo.platform"],
  "contributes": {
    "platform_seams": []
  }
}
```

- `id`: stable lowercase identifier; changing it creates a different extension.
- `name`: human label only; dependencies never use it.
- `version`: manifest implementation version. It does not change schema semantics.
- `provides`: one or more uniquely owned capability keys.
- `requires`: capability keys that must be active before this extension.
- `contributes.platform_seams`: optional list handled by the built-in typed contribution spec.

A platform seam has a stable `id`, display `name`, one responsibility-plane `owner`, and exactly the
`definition`, `provider`, and `consumer` roles. Each role declares repository-relative candidate `paths`, a
positive `minimum`, and whether failure to meet that minimum is required or optional. The platform report
checks those paths through its existing checkout-containment logic.

The default schema v1 context registers one contribution type. A specialized context may register another
`ContributionSpec` without changing the manifest envelope. Executable callbacks or opaque payloads remain
invalid: a new declarative type needs a bounded validator, stable item identity, limits, diagnostics, an owning
consumer, and failure-path tests.

## Add an extension

1. Choose a stable, namespaced extension ID and capability keys.
2. Create `extensions/<name>/extension.json` using the schema above.
3. Add `<name>/extension.json` to `extensions/index.json`.
4. Run `vemo extensions --check --json` and inspect `load_order`, `state`, and `issues`.
5. If it contributes a platform seam, run `vemo platform --check --json` and verify all required roles.
6. Add focused tests for activation, dependency failure, teardown, and the contribution's owning consumer.

For a new contribution kind, also create a `ContributionSpec`, pass it to the owning `CompositionContext`, and
test validation, duplicate identity, total limits, reconciliation, and consumer behavior. Do not add a module
or callable field to the JSON schema.

If a capability truly needs executable behavior, implement that behavior in a normal, reviewed VEMO module
and let the manifest describe its stable capability/topology. The manifest is not a shortcut around normal
task scope, review, or verification.

## Resolution states and diagnostics

An extension is:

- `active` when all dependencies resolved;
- `waiting` when a provider is absent or another extension cannot activate;
- `cycle` when it belongs to a dependency cycle;
- `conflict` when its ID or one of its provided capabilities is not unique.

Diagnostics use stable codes instead of parser messages or file contents. Important groups are:

- index/files: `extension_index_*`, `extension_manifest_*`, `manifest_reference_unsafe`;
- manifest schema: `manifest_*`, `platform_seam_*`, `platform_role_*`;
- composition: `missing_required_capability`, `duplicate_extension_id`,
  `duplicate_capability_provider`, `dependency_cycle`, `duplicate_platform_seam`.

The JSON report emits repository-relative manifest paths and validated metadata only. It never emits the
absolute checkout path or the contents of target component files.

## How this maps to Cordis

Cordis describes spatial composability as dependency-aware components reacting to available services and
temporal composability as completely reverting a component's effects when it is removed. Its official
[paper](https://github.com/cordiverse/paper) and [repository](https://github.com/cordiverse/cordis) are the
primary references. DeepSeek Harness's official [Cordis primer](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-primer.md)
shows the practical form: stable context service keys, declared injection dependencies, typed communication,
and a disposer for every registration.

VEMO transfers the parts that fit a governance CLI:

| Cordis concept | VEMO equivalent |
|---|---|
| context service key | stable capability in `CompositionContext` and `provides` / `requires` |
| reactive dependency injection | parent/child context inheritance, deterministic activation, `waiting` state |
| reversible effect | registration disposer and grouped LIFO `EffectScope` |
| loader/config reconciliation | fingerprinted delta, per-manifest scopes, explicit `applied`/`noop`/`deferred` state |
| inspectable plugin tree | `load_order`, extension states, contributions, stable issues |

VEMO does not adopt Cordis's runtime event bus, hot module replacement, or executable plugin loader. Those are
valuable for a long-lived application runtime; in a portable governance layer they would expand the trusted
code surface and compete with the external harness that already owns execution.

The incremental lifecycle also reflects the evolution from Wildmeerkat's
[`lite`](https://github.com/BST-AII/Wildmeerkat/tree/lite) baseline to its
[`dev`](https://github.com/BST-AII/Wildmeerkat/tree/dev) branch: keep the small, explicit entry contract while
adding idempotent lifecycle processing, visible degraded states, and authoritative verification. VEMO keeps
those effects inside its existing task receipts and manifest-only composition model; it does not copy
Wildmeerkat's governance MCP, background worker, or branch-specific runtime.
