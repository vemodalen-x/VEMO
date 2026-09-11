"""Cordis-inspired composition context, dependency resolution, and effect scopes."""

import json

from .contracts import (
    ContributionSpec,
    DEFAULT_CONTRIBUTION_SPECS,
    ExtensionManifestError,
    issue,
    valid_id,
    validate_manifest,
)


class EffectScope:
    """Own reversible effects and tear them down once in reverse registration order. @codex-comment"""

    def __init__(self):
        """Create an open scope with no tracked side effects. @codex-comment"""
        self._disposers = []
        self._closed = False

    @property
    def closed(self):
        """Expose whether teardown has already completed without mutating the scope. @codex-comment"""
        return self._closed

    def track(self, disposer):
        """Track one callable disposer and return it for fluent registration. @codex-comment"""
        if self._closed:
            raise RuntimeError("cannot track an effect in a closed scope")
        if not callable(disposer):
            raise TypeError("effect disposer must be callable")
        self._disposers.append(disposer)
        return disposer

    def dispose(self):
        """Run every tracked disposer LIFO, once, and report the number attempted. @codex-comment"""
        if self._closed:
            return 0
        self._closed = True
        attempted = 0
        errors = []
        while self._disposers:
            disposer = self._disposers.pop()
            attempted += 1
            try:
                disposer()
            except Exception as error:  # teardown must continue so later effects are not leaked
                errors.append(error)
        if errors:
            raise RuntimeError("one or more composition effects failed to dispose") from errors[0]
        return attempted

    def __enter__(self):
        """Return the open scope for grouped registrations. @codex-comment"""
        return self

    def __exit__(self, _type, _value, _traceback):
        """Dispose grouped effects at context-manager exit without suppressing errors. @codex-comment"""
        self.dispose()
        return False


def _cycle_nodes(graph):
    """Return nodes in dependency strongly-connected components, including self-cycles. @codex-comment"""
    index = 0
    indexes = {}
    lowlinks = {}
    stack = []
    on_stack = set()
    cycles = set()

    def visit(node):
        """Run one deterministic Tarjan traversal step over the bounded dependency graph. @codex-comment"""
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for dependency in sorted(graph.get(node, ())):
            if dependency not in indexes:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[dependency])
        if lowlinks[node] != indexes[node]:
            return
        component = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1 or node in graph.get(node, ()):
            cycles.update(component)

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    return cycles


class CompositionContext:
    """Hold stable capabilities, typed contributions, child contexts, and reversible effects. @codex-comment"""

    def __init__(self, host_capabilities=(), contribution_specs=None, parent=None):
        """Create an isolated context inheriting only resolved capabilities from its parent. @codex-comment"""
        host_capabilities = tuple(host_capabilities)
        if any(not valid_id(capability) for capability in host_capabilities):
            raise ValueError("host capabilities must be stable identifiers")
        specs = tuple(DEFAULT_CONTRIBUTION_SPECS if contribution_specs is None else contribution_specs)
        if any(not isinstance(spec, ContributionSpec) for spec in specs):
            raise TypeError("contribution specs must be ContributionSpec instances")
        if len({spec.key for spec in specs}) != len(specs):
            raise ValueError("contribution spec keys must be unique")
        if parent is not None and not isinstance(parent, CompositionContext):
            raise TypeError("parent must be a CompositionContext")
        self.host_capabilities = tuple(sorted(set(host_capabilities)))
        self.contribution_specs = specs
        self.parent = parent
        self._registrations = []

    def fork(self, host_capabilities=()):
        """Create a child that reacts to this context's currently active capabilities. @codex-comment"""
        return CompositionContext(host_capabilities, self.contribution_specs, parent=self)

    def effect(self, installer, scope=None):
        """Run one trusted internal installer and optionally bind its disposer to a scope. @codex-comment"""
        if not callable(installer):
            raise TypeError("effect installer must be callable")
        disposer = installer(self)
        if not callable(disposer):
            raise TypeError("effect installer must return a callable disposer")
        if scope is not None:
            if not isinstance(scope, EffectScope):
                raise TypeError("effect scope must be an EffectScope")
            scope.track(disposer)
        return disposer

    def register(self, manifest, source, scope=None):
        """Validate/register one manifest and return an idempotent disposer for that exact effect. @codex-comment"""
        if scope is not None and not isinstance(scope, EffectScope):
            raise TypeError("effect scope must be an EffectScope")
        normalized, issues = validate_manifest(manifest, source, self.contribution_specs)
        if issues:
            raise ExtensionManifestError(issues)
        record = {"manifest": normalized, "source": source, "token": object()}
        self._registrations.append(record)
        disposed = False

        def dispose():
            """Remove only the captured registration; repeated teardown is a no-op. @codex-comment"""
            nonlocal disposed
            if disposed:
                return False
            disposed = True
            for index, candidate in enumerate(self._registrations):
                if candidate["token"] is record["token"]:
                    self._registrations.pop(index)
                    return True
            return False

        if scope is not None:
            scope.track(dispose)
        return dispose

    @staticmethod
    def _resolved_capabilities(report):
        """Derive safe active capability keys from a resolved report for child inheritance. @codex-comment"""
        capabilities = set(report["host_capabilities"])
        for extension in report["extensions"]:
            if extension["state"] == "active":
                capabilities.update(extension["provides"])
        return capabilities

    def _parent_context(self):
        """Return inherited active capabilities plus a fail-closed parent diagnostic. @codex-comment"""
        if self.parent is None:
            return set(), []
        report = self.parent.resolve()
        issues = [] if report["summary"]["status"] == "pass" else [issue("parent_context_invalid")]
        return self._resolved_capabilities(report), issues

    def _aggregate_contributions(self, load_order, records, issues):
        """Aggregate active typed contributions without coupling the resolver to item schemas. @codex-comment"""
        output = {}
        for spec in self.contribution_specs:
            groups = {}
            for extension_id in load_order:
                for item in records[extension_id]["manifest"]["contributes"][spec.key]:
                    groups.setdefault(spec.identity(item), []).append((extension_id, item))
            if sum(len(group) for group in groups.values()) > spec.max_total:
                issues.append(issue(spec.total_code, contribution=spec.key))
                output[spec.key] = []
                continue
            for item_id, group in sorted(groups.items()):
                if len(group) > 1:
                    details = {
                        spec.diagnostic_field: item_id,
                        "extensions": sorted(extension_id for extension_id, _ in group),
                    }
                    issues.append(issue(spec.duplicate_code, **details))
            output[spec.key] = [
                item
                for item_id, group in sorted(groups.items())
                if len(group) == 1
                for _, item in group
            ]
        return output

    def resolve(self, additional_issues=None, discovered=None):
        """Compute deterministic activation, context inheritance, conflicts, cycles, and contributions. @codex-comment"""
        inherited, parent_issues = self._parent_context()
        effective_host = set(self.host_capabilities) | inherited
        issues = list(additional_issues or []) + parent_issues
        records = sorted(self._registrations, key=lambda row: (row["manifest"]["id"], row["source"]))
        id_groups = {}
        for record in records:
            id_groups.setdefault(record["manifest"]["id"], []).append(record)
        conflicted_ids = set()
        for extension_id, group in sorted(id_groups.items()):
            if len(group) > 1:
                conflicted_ids.add(extension_id)
                issues.append(issue("duplicate_extension_id", extension=extension_id))

        unique_records = {extension_id: group[0] for extension_id, group in id_groups.items() if len(group) == 1}
        capability_groups = {}
        for extension_id, record in sorted(unique_records.items()):
            for capability in record["manifest"]["provides"]:
                capability_groups.setdefault(capability, []).append(extension_id)
        for capability, providers in sorted(capability_groups.items()):
            if capability in effective_host or len(providers) > 1:
                conflicted_ids.update(providers)
                issues.append(issue(
                    "duplicate_capability_provider", capability=capability, extensions=sorted(providers)
                ))

        provider_for = {
            capability: providers[0]
            for capability, providers in capability_groups.items()
            if len(providers) == 1 and providers[0] not in conflicted_ids
        }
        missing_pairs = set()
        for extension_id, record in sorted(unique_records.items()):
            for capability in record["manifest"]["requires"]:
                if capability not in effective_host and capability not in capability_groups:
                    missing_pairs.add((extension_id, capability))
        for extension_id, capability in sorted(missing_pairs):
            issues.append(issue("missing_required_capability", extension=extension_id, capability=capability))

        available = set(effective_host)
        pending = set(unique_records) - conflicted_ids
        load_order = []
        while pending:
            ready = sorted(
                extension_id for extension_id in pending
                if set(unique_records[extension_id]["manifest"]["requires"]) <= available
            )
            if not ready:
                break
            for extension_id in ready:
                pending.remove(extension_id)
                load_order.append(extension_id)
                available.update(unique_records[extension_id]["manifest"]["provides"])

        dependency_graph = {extension_id: set() for extension_id in pending}
        for extension_id in pending:
            for capability in unique_records[extension_id]["manifest"]["requires"]:
                provider = provider_for.get(capability)
                if provider in pending:
                    dependency_graph[extension_id].add(provider)
        cycle_ids = _cycle_nodes(dependency_graph)
        if cycle_ids:
            issues.append(issue("dependency_cycle", extensions=sorted(cycle_ids)))

        active_ids = set(load_order)
        state_by_token = {}
        for record in records:
            extension_id = record["manifest"]["id"]
            if extension_id in conflicted_ids or len(id_groups[extension_id]) > 1:
                state = "conflict"
            elif extension_id in active_ids:
                state = "active"
            elif extension_id in cycle_ids:
                state = "cycle"
            else:
                state = "waiting"
            state_by_token[record["token"]] = state

        contributions = self._aggregate_contributions(load_order, unique_records, issues)
        issue_rows = sorted(
            issues,
            key=lambda row: (
                row.get("code", ""), row.get("extension", ""), row.get("capability", ""),
                row.get("contribution", ""), row.get("seam", ""), row.get("item", ""),
                row.get("source", ""), json.dumps(row, sort_keys=True),
            ),
        )
        extension_rows = []
        for record in records:
            manifest = record["manifest"]
            waiting_on = sorted(capability for capability in manifest["requires"] if capability not in available)
            extension_rows.append({
                "id": manifest["id"],
                "name": manifest["name"],
                "version": manifest["version"],
                "source": record["source"],
                "state": state_by_token[record["token"]],
                "provides": list(manifest["provides"]),
                "requires": list(manifest["requires"]),
                "permissions": list(manifest.get("permissions", [])),
                "compatibility": dict(manifest.get("compatibility", {})),
                "waiting_on": waiting_on,
            })
        states = list(state_by_token.values())
        return {
            "schema_version": 1,
            "command": "vemo extensions",
            "read_only": True,
            "execution_model": "declarative_manifests_only",
            "summary": {
                "status": "pass" if not issue_rows else "fail",
                "discovered": len(records) if discovered is None else discovered,
                "registered": len(records),
                "active": len(load_order),
                "waiting": states.count("waiting"),
                "conflicts": states.count("conflict"),
                "cycles": states.count("cycle"),
                "issues": len(issue_rows),
            },
            "host_capabilities": sorted(effective_host),
            "load_order": load_order,
            "extensions": extension_rows,
            "contributions": contributions,
            "issues": issue_rows,
            "boundaries": [
                "Only extensions/index.json and its repository-local extension.json files are read.",
                "Manifests are data: no Python, JavaScript, shell, entry point, or hook is executed.",
                "Duplicate providers fail instead of relying on hidden override order.",
                "A resolved contribution is topology, not proof that its provider executed.",
            ],
        }


class ExtensionRegistry(CompositionContext):
    """Backward-compatible name for the root VEMO composition context. @codex-comment"""


__all__ = ["CompositionContext", "EffectScope", "ExtensionRegistry"]
