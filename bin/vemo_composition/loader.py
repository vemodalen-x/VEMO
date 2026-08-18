"""Bounded declarative discovery and incremental reconciliation for extension manifests."""

import hashlib
import json
from pathlib import Path

from .context import CompositionContext, EffectScope, ExtensionRegistry
from .contracts import decode_json, issue, safe_relative_path, validate_manifest


INDEX_SCHEMA_VERSION = 1
INDEX_PATH = "extensions/index.json"
MAX_INDEX_BYTES = 32 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_EXTENSIONS = 64
HOST_CAPABILITIES = ("vemo.platform",)


def _resolve_local_file(root, relative, boundary):
    """Resolve a file while rejecting missing, invalid, or symlink-escaped targets. @codex-comment"""
    try:
        source = Path(root) / relative
        if not source.exists() and not source.is_symlink():
            return "missing", None
        resolved = source.resolve()
        resolved.relative_to(Path(boundary).resolve())
        if not resolved.is_file():
            return "invalid", None
        return "valid", resolved
    except (OSError, RuntimeError, TypeError, ValueError):
        return "unsafe", None


def _read_bounded_json(path, maximum):
    """Read at most maximum+1 bytes, returning stable size, I/O, or JSON codes. @codex-comment"""
    try:
        with Path(path).open("rb") as handle:
            data = handle.read(maximum + 1)
    except OSError:
        return None, "file_unreadable"
    if len(data) > maximum:
        return None, "file_too_large"
    return decode_json(data)


def discover_extension_manifests(root):
    """Read the explicit activation index and bounded local manifests without executing code. @codex-comment"""
    root = Path(root).resolve()
    issues = []
    try:
        extension_root = (root / "extensions").resolve()
        extension_root.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return [], [issue("extension_root_unsafe", source=INDEX_PATH)], 0
    if not extension_root.is_dir():
        return [], [issue("extension_index_missing", source=INDEX_PATH)], 0
    state, index_file = _resolve_local_file(root, INDEX_PATH, extension_root)
    if state != "valid":
        code = "extension_index_missing" if state == "missing" else "extension_index_unsafe"
        return [], [issue(code, source=INDEX_PATH)], 0
    index, error = _read_bounded_json(index_file, MAX_INDEX_BYTES)
    if error:
        return [], [issue("extension_index_" + error, source=INDEX_PATH)], 0
    if not isinstance(index, dict) or set(index) != {"schema_version", "extensions"}:
        return [], [issue("extension_index_fields", source=INDEX_PATH)], 0
    if type(index.get("schema_version")) is not int or index.get("schema_version") != INDEX_SCHEMA_VERSION:
        issues.append(issue("extension_index_schema_version", source=INDEX_PATH))
    references = index.get("extensions")
    if not isinstance(references, list) or len(references) > MAX_EXTENSIONS:
        return [], issues + [issue("extension_index_count", source=INDEX_PATH)], 0
    string_references = [item for item in references if isinstance(item, str)]
    if len(string_references) != len(set(string_references)):
        issues.append(issue("duplicate_manifest_reference", source=INDEX_PATH))

    manifests = []
    seen = set()
    for reference in references:
        if not safe_relative_path(reference) or not reference.endswith("/extension.json"):
            issues.append(issue("manifest_reference_unsafe", source=INDEX_PATH))
            continue
        if reference in seen:
            continue
        seen.add(reference)
        relative = "extensions/" + reference
        state, manifest_file = _resolve_local_file(root, relative, extension_root)
        if state != "valid":
            code = "extension_manifest_missing" if state == "missing" else "extension_manifest_unsafe"
            issues.append(issue(code, source=relative))
            continue
        manifest, error = _read_bounded_json(manifest_file, MAX_MANIFEST_BYTES)
        if error:
            issues.append(issue("extension_manifest_" + error, source=relative))
            continue
        manifests.append((manifest, relative))
    return manifests, issues, len(references)


def _manifest_fingerprint(manifest):
    """Hash normalized manifest semantics without retaining or reporting raw file bytes. @codex-comment"""
    payload = json.dumps(
        manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _activation_index_usable(issues):
    """Reject an index-level revision atomically while allowing per-manifest isolation. @codex-comment"""
    return not any(
        row.get("code") == "extension_root_unsafe"
        or str(row.get("code", "")).startswith("extension_index_")
        for row in issues
    )


class ExtensionLoader:
    """Incrementally reconcile one activation index into a composition context. @codex-comment"""

    def __init__(self, root, context=None):
        """Bind a repository root and optional caller-owned composition context. @codex-comment"""
        if context is not None and not isinstance(context, CompositionContext):
            raise TypeError("loader context must be a CompositionContext")
        self.root = Path(root).resolve()
        self.context = context or ExtensionRegistry(HOST_CAPABILITIES)
        self._mounted = {}
        self._order = []
        self._attempt = 0
        self._revision = 0
        self._initialized = False

    def _transition_report(self, status, applied, *, added=(), retained=(), changed=(), removed=()):
        """Build deterministic, content-minimized lifecycle metadata for one attempt. @codex-comment"""
        return {
            "status": status,
            "applied": applied,
            "attempt": self._attempt,
            "revision": self._revision,
            "added": list(added),
            "retained": list(retained),
            "changed": list(changed),
            "removed": list(removed),
        }

    def _dispose_sources(self, sources):
        """Dispose selected loader-owned scopes in reverse prior mount order. @codex-comment"""
        selected = set(sources)
        attempted = 0
        errors = []
        for source in reversed(self._order):
            if source not in selected:
                continue
            scope = self._mounted[source]["scope"]
            was_open = not scope.closed
            try:
                attempted += scope.dispose()
            except Exception as error:  # finish every selected inverse before surfacing teardown failure
                attempted += int(was_open)
                errors.append(error)
        if errors:
            raise RuntimeError("one or more extension mounts failed to dispose") from errors[0]
        return attempted

    def reconcile(self):
        """Apply only a valid manifest delta, retaining unchanged registrations by identity. @codex-comment"""
        self._attempt += 1
        manifests, issues, discovered = discover_extension_manifests(self.root)
        if not _activation_index_usable(issues):
            issues.append(issue("reconciliation_deferred", reason="activation_index_invalid"))
            report = self.context.resolve(issues, discovered=discovered)
            report["reconciliation"] = self._transition_report(
                "deferred", False, retained=self._order
            )
            return report

        desired = {}
        for manifest, source in manifests:
            normalized, manifest_issues = validate_manifest(
                manifest, source, self.context.contribution_specs
            )
            issues.extend(manifest_issues)
            if normalized is None:
                continue
            desired[source] = {
                "id": normalized["id"],
                "manifest": normalized,
                "fingerprint": _manifest_fingerprint(normalized),
            }

        retained = [
            source for source, record in desired.items()
            if source in self._mounted
            and self._mounted[source]["fingerprint"] == record["fingerprint"]
        ]
        changed = [
            source for source, record in desired.items()
            if source in self._mounted
            and self._mounted[source]["fingerprint"] != record["fingerprint"]
        ]
        added = [source for source in desired if source not in self._mounted]
        removed = [source for source in self._order if source not in desired]

        next_mounted = {}
        newly_mounted = []
        try:
            for source, record in desired.items():
                if source in retained:
                    next_mounted[source] = self._mounted[source]
                    continue
                scope = EffectScope()
                self.context.register(record["manifest"], source, scope=scope)
                next_mounted[source] = {**record, "scope": scope}
                newly_mounted.append(source)
        except Exception:
            for source in reversed(newly_mounted):
                next_mounted[source]["scope"].dispose()
            raise

        self._dispose_sources(changed + removed)
        self._mounted = next_mounted
        retained_mount_order = [source for source in self._order if source in retained]
        self._order = retained_mount_order + newly_mounted
        lifecycle_changed = bool(added or changed or removed) or not self._initialized
        if lifecycle_changed:
            self._revision += 1
        self._initialized = True
        report = self.context.resolve(issues, discovered=discovered)
        report["reconciliation"] = self._transition_report(
            "applied" if lifecycle_changed else "noop",
            True,
            added=added,
            retained=retained,
            changed=changed,
            removed=removed,
        )
        return report

    def close(self):
        """Dispose manifests mounted by this loader without touching caller registrations. @codex-comment"""
        if not self._mounted:
            self._order = []
            self._initialized = False
            return 0
        disposed = self._dispose_sources(self._order)
        self._mounted = {}
        self._order = []
        self._initialized = False
        return disposed


def build_extension_report(root):
    """Resolve a one-shot report and tear down all temporary manifest registrations. @codex-comment"""
    loader = ExtensionLoader(root)
    try:
        return loader.reconcile()
    finally:
        loader.close()


__all__ = [
    "ExtensionLoader",
    "HOST_CAPABILITIES",
    "build_extension_report",
    "discover_extension_manifests",
]
