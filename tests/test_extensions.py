import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vemo_extensions", ROOT / "bin" / "vemo_extensions.py")
extensions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extensions)


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vemo_extensions_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    @staticmethod
    def _manifest(extension_id, provides, requires=(), seams=(), contributes=None):
        return {
            "schema_version": 1,
            "id": extension_id,
            "name": extension_id,
            "version": "1.0.0",
            "provides": list(provides),
            "requires": list(requires),
            "contributes": {"platform_seams": list(seams)} if contributes is None else contributes,
        }

    def _write_index(self, references):
        path = self.temp / "extensions" / "index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "extensions": references}), encoding="utf-8")
        return path

    def _write_manifest(self, reference, manifest):
        path = self.temp / "extensions" / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_dependency_order_is_deterministic_and_registration_is_reversible(self):
        registry = extensions.ExtensionRegistry(("vemo.platform",))
        dependent = self._manifest("demo.consumer", ("demo.consumer",), ("demo.provider",))
        provider = self._manifest("demo.provider", ("demo.provider",), ("vemo.platform",))
        registry.register(dependent, "memory/consumer.json")
        dispose_provider = registry.register(provider, "memory/provider.json")

        resolved = registry.resolve()

        self.assertEqual("pass", resolved["summary"]["status"])
        self.assertEqual(["demo.provider", "demo.consumer"], resolved["load_order"])
        self.assertEqual(2, resolved["summary"]["active"])
        self.assertTrue(dispose_provider())
        self.assertFalse(dispose_provider())

        after_teardown = registry.resolve()
        self.assertEqual("fail", after_teardown["summary"]["status"])
        self.assertEqual(["demo.consumer"], [item["id"] for item in after_teardown["extensions"]])
        self.assertEqual("waiting", after_teardown["extensions"][0]["state"])
        self.assertEqual(1, after_teardown["summary"]["waiting"])
        self.assertEqual(0, after_teardown["summary"]["conflicts"])
        self.assertEqual(["demo.provider"], after_teardown["extensions"][0]["waiting_on"])
        self.assertIn("missing_required_capability", {item["code"] for item in after_teardown["issues"]})

    def test_child_context_reacts_to_parent_capability_removal(self):
        parent = extensions.CompositionContext(("vemo.platform",))
        provider = self._manifest("demo.parent", ("demo.parent",), ("vemo.platform",))
        dispose_provider = parent.register(provider, "memory/parent.json")
        child = parent.fork()
        child.register(
            self._manifest("demo.child", ("demo.child",), ("demo.parent",)),
            "memory/child.json",
        )

        inherited = child.resolve()

        self.assertEqual("pass", inherited["summary"]["status"])
        self.assertEqual(["demo.child"], inherited["load_order"])
        self.assertIn("demo.parent", inherited["host_capabilities"])
        self.assertTrue(dispose_provider())

        detached = child.resolve()
        self.assertEqual("fail", detached["summary"]["status"])
        self.assertEqual("waiting", detached["extensions"][0]["state"])
        self.assertEqual(["demo.parent"], detached["extensions"][0]["waiting_on"])

    def test_effect_scope_is_lifo_idempotent_and_leaves_untracked_registration(self):
        context = extensions.CompositionContext(("vemo.platform",))
        context.register(
            self._manifest("demo.untracked", ("demo.untracked",), ("vemo.platform",)),
            "memory/untracked.json",
        )
        events = []

        def installer(label):
            def install(_context):
                events.append("install:" + label)
                return lambda: events.append("dispose:" + label)
            return install

        scope = extensions.EffectScope()
        context.effect(installer("first"), scope)
        context.effect(installer("second"), scope)

        self.assertEqual(2, scope.dispose())
        self.assertEqual(0, scope.dispose())
        self.assertEqual(
            ["install:first", "install:second", "dispose:second", "dispose:first"], events
        )
        remaining = context.resolve()
        self.assertEqual(["demo.untracked"], remaining["load_order"])

    def test_typed_contribution_and_loader_reconcile_without_core_changes(self):
        def validate_item(value, extension_id, source):
            if not isinstance(value, dict) or set(value) != {"id", "value"}:
                return None, [{"code": "demo_item_invalid", "extension": extension_id, "source": source}]
            if not isinstance(value["id"], str) or not isinstance(value["value"], str):
                return None, [{"code": "demo_item_invalid", "extension": extension_id, "source": source}]
            return {"id": value["id"], "value": value["value"]}, []

        spec = extensions.ContributionSpec(
            "demo_items", validate_item, lambda item: item["id"],
            max_per_manifest=4, max_total=8,
            count_code="demo_item_count", duplicate_code="demo_item_duplicate",
            total_code="demo_item_total", diagnostic_field="item",
        )
        context = extensions.CompositionContext(("vemo.platform",), (spec,))
        invalid = self._manifest(
            "demo.invalid-item", ("demo.invalid-item",), ("vemo.platform",),
            contributes={"demo_items": [{"id": "NOT VALID", "value": "rejected"}]},
        )
        with self.assertRaises(extensions.ExtensionManifestError) as captured:
            context.register(invalid, "memory/invalid-item.json")
        self.assertIn("contribution_identity_invalid", {row["code"] for row in captured.exception.issues})
        context.register(
            self._manifest(
                "demo.caller", ("demo.caller",), ("vemo.platform",),
                contributes={"demo_items": []},
            ),
            "memory/caller.json",
        )
        reference = "demo/extension.json"
        self._write_index([reference])
        manifest = self._manifest(
            "demo.typed", ("demo.typed",), ("vemo.platform",),
            contributes={"demo_items": [{"id": "demo.one", "value": "first"}]},
        )
        manifest_path = self._write_manifest(reference, manifest)
        loader = extensions.ExtensionLoader(self.temp, context)

        first = loader.reconcile()
        self.assertEqual([{"id": "demo.one", "value": "first"}], first["contributions"]["demo_items"])
        self.assertEqual("applied", first["reconciliation"]["status"])
        self.assertEqual(["extensions/demo/extension.json"], first["reconciliation"]["added"])

        manifest["contributes"]["demo_items"] = [{"id": "demo.two", "value": "second"}]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        second = loader.reconcile()

        self.assertEqual("pass", second["summary"]["status"])
        self.assertEqual(2, second["summary"]["registered"])
        self.assertEqual([{"id": "demo.two", "value": "second"}], second["contributions"]["demo_items"])
        self.assertEqual(["extensions/demo/extension.json"], second["reconciliation"]["changed"])
        self.assertEqual(2, second["reconciliation"]["revision"])
        self.assertEqual(1, loader.close())
        self.assertEqual(0, loader.close())
        self.assertEqual(["demo.caller"], context.resolve()["load_order"])

    def test_loader_reconcile_retains_identity_and_isolates_manifest_failure(self):
        provider_reference = "provider/extension.json"
        consumer_reference = "consumer/extension.json"
        self._write_index([provider_reference, consumer_reference])
        self._write_manifest(
            provider_reference,
            self._manifest("demo.provider", ("demo.provider",), ("vemo.platform",)),
        )
        consumer = self._manifest(
            "demo.consumer", ("demo.consumer",), ("demo.provider",)
        )
        consumer_path = self._write_manifest(consumer_reference, consumer)
        context = extensions.CompositionContext(("vemo.platform",))
        loader = extensions.ExtensionLoader(self.temp, context)

        with mock.patch.object(context, "register", wraps=context.register) as register:
            first = loader.reconcile()
            unchanged = loader.reconcile()

            self.assertEqual(2, register.call_count)
            self.assertEqual("noop", unchanged["reconciliation"]["status"])
            self.assertEqual(1, unchanged["reconciliation"]["revision"])
            self.assertEqual(
                ["extensions/provider/extension.json", "extensions/consumer/extension.json"],
                unchanged["reconciliation"]["retained"],
            )
            self.assertEqual(first["load_order"], unchanged["load_order"])

            self._write_index([consumer_reference, provider_reference])
            reordered = loader.reconcile()
            self.assertEqual(2, register.call_count)
            self.assertEqual("noop", reordered["reconciliation"]["status"])
            self.assertEqual(1, reordered["reconciliation"]["revision"])
            self.assertEqual(
                ["extensions/provider/extension.json", "extensions/consumer/extension.json"],
                loader._order,
            )

            consumer["version"] = "1.1.0"
            consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
            changed = loader.reconcile()

            self.assertEqual(3, register.call_count)
            self.assertEqual(
                ["extensions/provider/extension.json"], changed["reconciliation"]["retained"]
            )
            self.assertEqual(
                ["extensions/consumer/extension.json"], changed["reconciliation"]["changed"]
            )

            consumer_path.write_text("{not-json", encoding="utf-8")
            isolated = loader.reconcile()

        self.assertEqual("fail", isolated["summary"]["status"])
        self.assertEqual(
            ["extensions/provider/extension.json"], isolated["reconciliation"]["retained"]
        )
        self.assertEqual(
            ["extensions/consumer/extension.json"], isolated["reconciliation"]["removed"]
        )
        self.assertEqual(["demo.provider"], context.resolve()["load_order"])
        self.assertIn(
            "extension_manifest_json_invalid", {row["code"] for row in isolated["issues"]}
        )
        self.assertEqual(1, loader.close())

    def test_loader_defers_invalid_index_and_retains_last_valid_revision(self):
        reference = "demo/extension.json"
        index_path = self._write_index([reference])
        self._write_manifest(
            reference,
            self._manifest("demo.stable", ("demo.stable",), ("vemo.platform",)),
        )
        context = extensions.CompositionContext(("vemo.platform",))
        loader = extensions.ExtensionLoader(self.temp, context)
        first = loader.reconcile()

        index_path.write_text("{not-json", encoding="utf-8")
        deferred = loader.reconcile()

        self.assertEqual("pass", first["summary"]["status"])
        self.assertEqual("fail", deferred["summary"]["status"])
        self.assertFalse(deferred["reconciliation"]["applied"])
        self.assertEqual("deferred", deferred["reconciliation"]["status"])
        self.assertEqual(2, deferred["reconciliation"]["attempt"])
        self.assertEqual(1, deferred["reconciliation"]["revision"])
        self.assertEqual(
            ["extensions/demo/extension.json"], deferred["reconciliation"]["retained"]
        )
        self.assertEqual(["demo.stable"], context.resolve()["load_order"])
        codes = {row["code"] for row in deferred["issues"]}
        self.assertIn("extension_index_json_invalid", codes)
        self.assertIn("reconciliation_deferred", codes)

        index_path.write_text(
            json.dumps({"schema_version": 2, "extensions": []}), encoding="utf-8"
        )
        unsupported = loader.reconcile()
        self.assertEqual("deferred", unsupported["reconciliation"]["status"])
        self.assertEqual(3, unsupported["reconciliation"]["attempt"])
        self.assertEqual(1, unsupported["reconciliation"]["revision"])
        self.assertEqual(["demo.stable"], context.resolve()["load_order"])
        self.assertIn(
            "extension_index_schema_version", {row["code"] for row in unsupported["issues"]}
        )
        self.assertEqual(1, loader.close())

    def test_missing_duplicate_and_cyclic_dependencies_fail_with_stable_codes(self):
        missing = extensions.ExtensionRegistry(("vemo.platform",))
        missing.register(
            self._manifest("demo.missing-consumer", ("demo.consumer",), ("demo.absent",)),
            "memory/missing.json",
        )
        self.assertIn("missing_required_capability", {row["code"] for row in missing.resolve()["issues"]})

        duplicate = extensions.ExtensionRegistry(("vemo.platform",))
        duplicate.register(
            self._manifest("demo.provider-a", ("demo.shared",), ("vemo.platform",)),
            "memory/provider-a.json",
        )
        duplicate.register(
            self._manifest("demo.provider-b", ("demo.shared",), ("vemo.platform",)),
            "memory/provider-b.json",
        )
        duplicate.register(
            self._manifest("demo.same", ("demo.same-a",), ("vemo.platform",)),
            "memory/same-a.json",
        )
        duplicate.register(
            self._manifest("demo.same", ("demo.same-b",), ("vemo.platform",)),
            "memory/same-b.json",
        )
        duplicate_codes = {row["code"] for row in duplicate.resolve()["issues"]}
        self.assertIn("duplicate_capability_provider", duplicate_codes)
        self.assertIn("duplicate_extension_id", duplicate_codes)
        self.assertEqual(4, duplicate.resolve()["summary"]["conflicts"])

        cyclic = extensions.ExtensionRegistry(("vemo.platform",))
        cyclic.register(
            self._manifest("demo.cycle-a", ("demo.a",), ("demo.b",)),
            "memory/cycle-a.json",
        )
        cyclic.register(
            self._manifest("demo.cycle-b", ("demo.b",), ("demo.a",)),
            "memory/cycle-b.json",
        )
        cycle_report = cyclic.resolve()
        cycle_issue = next(row for row in cycle_report["issues"] if row["code"] == "dependency_cycle")
        self.assertEqual(["demo.cycle-a", "demo.cycle-b"], cycle_issue["extensions"])
        self.assertEqual({"cycle"}, {row["state"] for row in cycle_report["extensions"]})
        self.assertEqual(2, cycle_report["summary"]["cycles"])

    def test_manifest_schema_rejects_unsafe_contribution_paths(self):
        seam = {
            "id": "demo_seam",
            "name": "Demo seam",
            "owner": "control",
            "roles": [
                {"id": "definition", "required": True, "minimum": 1, "paths": ["../secret"]},
                {"id": "provider", "required": True, "minimum": 1, "paths": ["bin/provider.py"]},
                {"id": "consumer", "required": True, "minimum": 1, "paths": ["bin/consumer.py"]},
            ],
        }
        registry = extensions.ExtensionRegistry(("vemo.platform",))

        with self.assertRaises(extensions.ExtensionManifestError) as captured:
            registry.register(
                self._manifest("demo.unsafe", ("demo.unsafe",), ("vemo.platform",), (seam,)),
                "memory/unsafe.json",
            )

        self.assertIn("platform_role_path_unsafe", {row["code"] for row in captured.exception.issues})
        self.assertEqual([], registry.resolve()["extensions"])

    def test_manifest_rejects_boolean_schema_and_unencodable_display_name(self):
        manifest = self._manifest("demo.invalid-metadata", ("demo.invalid-metadata",))
        manifest["schema_version"] = True
        manifest["name"] = "\ud800"
        registry = extensions.ExtensionRegistry(("vemo.platform",))

        with self.assertRaises(extensions.ExtensionManifestError) as captured:
            registry.register(manifest, "memory/invalid-metadata.json")

        codes = {row["code"] for row in captured.exception.issues}
        self.assertIn("manifest_schema_version", codes)
        self.assertIn("manifest_name", codes)

    def test_discovery_rejects_bad_json_traversal_and_external_symlink_without_reading_target(self):
        references = [
            "bad/extension.json",
            "../outside/extension.json",
            "linked/extension.json",
        ]
        self._write_index(references)
        bad = self.temp / "extensions" / "bad" / "extension.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{not-json", encoding="utf-8")
        linked = self.temp / "extensions" / "linked" / "extension.json"
        linked.parent.mkdir(parents=True)
        with tempfile.TemporaryDirectory(prefix="vemo_extensions_external_") as external:
            target = Path(external) / "extension.json"
            sentinel = "external-extension-secret-must-not-appear"
            target.write_text(json.dumps(self._manifest(
                "demo.external", ("demo.external", sentinel), ("vemo.platform",)
            )), encoding="utf-8")
            try:
                linked.symlink_to(target)
            except (NotImplementedError, OSError) as error:
                self.skipTest("symlinks unavailable: %s" % error)
            report = extensions.build_extension_report(self.temp)

        encoded = json.dumps(report)
        codes = {row["code"] for row in report["issues"]}
        self.assertEqual("fail", report["summary"]["status"])
        self.assertIn("extension_manifest_json_invalid", codes)
        self.assertIn("manifest_reference_unsafe", codes)
        self.assertIn("extension_manifest_unsafe", codes)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn(str(target), encoded)
        with mock.patch.object(extensions, "ROOT", self.temp), mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(2, extensions.main(["--check", "--json"]))

    def test_cli_is_read_only_and_documented(self):
        command = [sys.executable, str(ROOT / "bin" / "vemo"), "extensions", "--check", "--json"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)

        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(1, report["schema_version"])
        self.assertEqual("declarative_manifests_only", report["execution_model"])
        self.assertEqual("pass", report["summary"]["status"])
        self.assertEqual(2, report["summary"]["active"])
        self.assertEqual(
            ["vemo.ring1-guard", "vemo.verification-evidence"], report["load_order"]
        )
        self.assertNotIn(str(ROOT), completed.stdout)
        self.assertLessEqual(
            len((ROOT / "bin" / "vemo_extensions.py").read_text(encoding="utf-8").splitlines()), 120
        )
        extension_doc = (ROOT / "docs" / "EXTENSIONS.md").read_text(encoding="utf-8")
        for phrase in (
            "Stable capabilities", "Reversible registration", "Activation index", "No code loading",
            "CompositionContext", "EffectScope", "ExtensionLoader", "ContributionSpec",
        ):
            self.assertIn(phrase, extension_doc)


if __name__ == "__main__":
    unittest.main()
