import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":
    ROOT = ROOT.parent
SPEC = importlib.util.spec_from_file_location("vemo_product", ROOT / "bin" / "vemo_product.py")
product = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(product)
TS_SPEC = importlib.util.spec_from_file_location("task_state_product_test", ROOT / "enforcement" / "validators" / "task_state.py")
task_state = importlib.util.module_from_spec(TS_SPEC)
with mock.patch.dict(os.environ, {"VEMO_ROOT": str(ROOT)}):
    TS_SPEC.loader.exec_module(task_state)


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vemo_product_test_"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def _write_fixture(self, relative, content="fixture\n"):
        path = self.temp / relative
        if relative == "tasks":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return path

    def _install_platform_contract(self):
        for source in sorted((ROOT / "extensions").rglob("*.json")):
            self._write_fixture(source.relative_to(ROOT).as_posix(), source.read_text(encoding="utf-8"))
        required_paths = {
            component["path"]
            for plane in product.PLATFORM_PLANES
            for component in plane["components"]
            if component["required"]
        }
        composition = product.build_extension_report(self.temp)
        self.assertEqual("pass", composition["summary"]["status"])
        for seam in composition["contributions"]["platform_seams"]:
            for role in seam["roles"]:
                if role["required"]:
                    required_paths.update(role["paths"])
        for relative in required_paths:
            if not (self.temp / relative).exists():
                self._write_fixture(relative)

    @staticmethod
    def _hook_document(*bindings):
        hooks = {}
        for event, action in bindings:
            hooks.setdefault(event, []).append({
                "hooks": [{
                    "type": "command",
                    "command": 'python3 "${PROJECT_DIR:-.}/enforcement/hooks/run.py" %s' % action,
                }],
            })
        return {"hooks": hooks}

    def test_detect_stack_and_start_preview_are_read_only(self):
        (self.temp / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        (self.temp / "presets").mkdir()
        (self.temp / "presets" / "python.yaml").write_text("paths:\n  build: python -m pytest\n", encoding="utf-8")
        before = sorted(path.relative_to(self.temp).as_posix() for path in self.temp.rglob("*"))
        plan = product.start_plan(self.temp)
        after = sorted(path.relative_to(self.temp).as_posix() for path in self.temp.rglob("*"))
        self.assertEqual("python", plan["detected_stack"])
        self.assertEqual("python", plan["preset"])
        self.assertEqual(before, after)
        self.assertTrue(plan["read_only_preview"])
        self.assertFalse(plan["conflicts"])

    def test_start_preview_reports_managed_preset_conflict(self):
        (self.temp / "presets").mkdir()
        (self.temp / "presets" / "python.yaml").write_text("paths:\n  build: one\n", encoding="utf-8")
        (self.temp / "vemo.config.preset.yaml").write_text("paths:\n  build: another\n", encoding="utf-8")
        plan = product.start_plan(self.temp, "python")
        self.assertEqual(1, len(plan["conflicts"]))
        self.assertIn("differs", plan["conflicts"][0])

    def test_apply_uses_existing_init_path_and_records_profile(self):
        (self.temp / "presets").mkdir()
        (self.temp / "presets" / "python.yaml").write_text("paths:\n  build: one\n", encoding="utf-8")
        (self.temp / "bin").mkdir()
        (self.temp / "bin" / "vemo").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        completed = subprocess.CompletedProcess([], 0, stdout="ready\n", stderr="")
        with mock.patch.object(product.subprocess, "run", return_value=completed) as run:
            with mock.patch.object(product, "_write_profile") as write_profile:
                result = product.apply_start(self.temp, "python", "team")
        self.assertEqual("apply", result["mode"])
        self.assertEqual(0, result["exit_code"])
        self.assertIn("ready", result["init_output"])
        self.assertEqual("init", run.call_args.args[0][2])
        write_profile.assert_called_once_with(self.temp, "team")

    def test_report_contains_observed_facts_without_event_payloads(self):
        (self.temp / "vemo.config.yaml").write_text(
            "capability:\n  tier: high\nenforcement:\n  mode: enforce\n", encoding="utf-8"
        )
        (self.temp / ".claude").mkdir()
        (self.temp / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
        (self.temp / ".git" / "hooks").mkdir(parents=True)
        (self.temp / ".git" / "hooks" / "pre-commit").write_text("hook\n", encoding="utf-8")
        (self.temp / ".git" / "hooks" / "pre-push").write_text("hook\n", encoding="utf-8")
        (self.temp / ".github" / "workflows").mkdir(parents=True)
        (self.temp / ".github" / "workflows" / "vemo-ci.yml").write_text("name: vemo\n", encoding="utf-8")
        (self.temp / ".vemo" / "run").mkdir(parents=True)
        now = product.utc_now().isoformat().replace("+00:00", "Z")
        (self.temp / ".vemo" / "telemetry.jsonl").write_text(
            json.dumps({"ts": now, "event": "scope_block_out", "content": "must not be echoed"}) + "\n"
            + json.dumps({"ts": now, "event": "session_start"}) + "\n", encoding="utf-8"
        )
        (self.temp / ".vemo" / "run" / "receipt.json").write_text(
            json.dumps({"ts": now, "profile": "full", "exit_codes": {"build": 0, "smoke": 0}}),
            encoding="utf-8",
        )
        (self.temp / ".vemo" / "run" / "run.log").write_text("output\n", encoding="utf-8")
        (self.temp / "tasks").mkdir()
        (self.temp / "tasks" / "T-demo.md").write_text(
            "---\nid: T-demo\nstate: AcceptancePassed\n---\n", encoding="utf-8"
        )

        report = product.build_report(self.temp, days=30)
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertEqual("ready", report["readiness"])
        self.assertEqual(1, report["telemetry"]["blocked_actions"])
        self.assertEqual(1, report["telemetry"]["sessions"])
        self.assertEqual("passed", report["verification"]["status"])
        self.assertEqual(1, report["tasks"]["accepted"])
        self.assertTrue(report["data_local_only"])
        self.assertFalse(report["source_upload"])
        self.assertNotIn("must not be echoed", encoded)

    def test_task_scoped_receipts_do_not_overwrite_each_other(self):
        run_dir = self.temp / ".vemo" / "run"
        receipt = run_dir / "receipt.json"
        task_receipts = run_dir / "receipts"
        original = (task_state.RUN_DIR, task_state.RECEIPT, task_state.TASK_RECEIPTS)
        task_state.RUN_DIR = str(run_dir)
        task_state.RECEIPT = str(receipt)
        task_state.TASK_RECEIPTS = str(task_receipts)
        try:
            task_state._write_receipt({"task": "T-one", "exit_codes": {"build": 0}})
            task_state._write_receipt({"task": "T-two", "exit_codes": {"build": 0}})
            self.assertEqual("T-one", task_state._read_receipt("T-one")["task"])
            self.assertEqual("T-two", task_state._read_receipt("T-two")["task"])
            self.assertEqual("T-two", task_state._read_receipt()["task"])
        finally:
            task_state.RUN_DIR, task_state.RECEIPT, task_state.TASK_RECEIPTS = original

    def test_workflow_report_maps_task_state_to_next_stage(self):
        (self.temp / "tasks").mkdir()
        (self.temp / "tasks" / "T-demo.md").write_text(
            "---\nid: T-demo\nrisk: R1\nstate: ImplementationDone\n"
            "heartbeat: 2026-07-25T00:00:00Z\n---\n", encoding="utf-8"
        )
        report = product.build_workflow_report(self.temp)
        self.assertEqual("review", report["current_stage"])
        self.assertEqual("T-demo", report["task"]["id"])
        self.assertEqual("done", report["stages"][2]["status"])
        self.assertEqual("next", report["stages"][3]["status"])
        self.assertTrue(report["data_local_only"])

    def test_workflow_report_without_task_starts_with_think(self):
        report = product.build_workflow_report(self.temp)
        self.assertIsNone(report["task"])
        self.assertEqual("think", report["current_stage"])
        self.assertEqual("next", report["stages"][0]["status"])

    def test_workflow_uses_bound_session_and_governance_yaml_parser(self):
        (self.temp / "tasks").mkdir()
        (self.temp / ".vemo").mkdir()
        (self.temp / "tasks/T-own.md").write_text(
            '---\nid: T-own\nstate: "ReviewApproved" # approved\nheartbeat: 2026-01-01T00:00:00Z\n---\n', encoding="utf-8")
        (self.temp / "tasks/T-other.md").write_text(
            '---\nid: T-other\nstate: AcceptancePassed\nheartbeat: 2026-08-01T00:00:00Z\n---\n', encoding="utf-8")
        (self.temp / ".vemo/session_task.json").write_text('{"worker":"T-own.md"}', encoding="utf-8")
        with mock.patch.dict(os.environ, {"VEMO_SESSION": "worker"}):
            report = product.build_workflow_report(self.temp)
        self.assertEqual("T-own", report["task"]["id"])
        self.assertEqual("build", report["current_stage"])

    def test_workflow_compares_utc_instants_not_heartbeat_text(self):
        (self.temp / "tasks").mkdir()
        for name, timestamp in (("earlier", "2026-01-01T08:00:00+08:00"), ("later", "2026-01-01T01:00:00Z")):
            (self.temp / f"tasks/T-{name}.md").write_text(
                f'---\nid: T-{name}\nstate: PlanCreated\nheartbeat: {timestamp}\n---\n', encoding="utf-8")
        self.assertEqual("T-later", product.build_workflow_report(self.temp)["task"]["id"])
    def test_platform_topology_is_read_only_content_minimizing_and_stable(self):
        self._install_platform_contract()
        canonical = self._hook_document(("SessionStart", "session-start"), ("Stop", "stop"))
        (self.temp / "enforcement" / "hooks" / "hooks.json").write_text(
            json.dumps(canonical), encoding="utf-8"
        )
        sentinel = "secret-platform-sentinel-must-not-appear"
        (self.temp / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        (self.temp / "vemo.config.yaml").write_text(
            "capability:\n  tier: high\nenforcement:\n  mode: enforce\ncredentials:\n"
            "  app_secret: %s\n" % sentinel,
            encoding="utf-8",
        )
        before = {
            path.relative_to(self.temp).as_posix(): path.read_bytes()
            for path in self.temp.rglob("*") if path.is_file()
        }

        payload = product.build_platform(self.temp)

        after = {
            path.relative_to(self.temp).as_posix(): path.read_bytes()
            for path in self.temp.rglob("*") if path.is_file()
        }
        encoded = json.dumps(payload, ensure_ascii=False)
        plane_ids = [plane["id"] for plane in payload["planes"]]
        self.assertEqual(
            ["ingress", "control", "policy", "execution", "enforcement", "evidence"],
            plane_ids,
        )
        control = next(plane for plane in payload["planes"] if plane["id"] == "control")
        self.assertTrue({
            "extension_registry", "composition_contracts", "composition_context", "composition_loader",
        } <= {component["id"] for component in control["components"]})
        self.assertEqual(list(range(1, 9)), [stage["step"] for stage in payload["lifecycle"]])
        self.assertTrue(all(stage["plane"] in plane_ids for stage in payload["lifecycle"]))
        self.assertEqual("ready", payload["summary"]["core_status"])
        self.assertEqual("pass", payload["summary"]["extension_status"])
        self.assertEqual("ready", payload["summary"]["capability_seam_status"])
        self.assertEqual("pass", payload["summary"]["check_status"])
        self.assertEqual("9.9.9", payload["version"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(
            {"source", "durable_record", "runtime_artifact"},
            {surface["id"] for surface in payload["materializations"]},
        )
        self.assertTrue(all(
            {role["id"] for role in seam["roles"]} == {"definition", "provider", "consumer"}
            for seam in payload["capability_seams"]
        ))
        self.assertEqual(
            ["vemo.ring1-guard", "vemo.verification-evidence"],
            payload["extensions"]["load_order"],
        )
        ring1 = next(seam for seam in payload["capability_seams"] if seam["id"] == "ring1_guard")
        self.assertEqual("available", ring1["status"])
        self.assertFalse((self.temp / "docs" / "ADAPTERS.md").exists())
        self.assertTrue(all(invariant["status"] == "not_observed" for invariant in payload["invariants"]))
        self.assertEqual(before, after)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn(str(self.temp), encoded)

    def test_platform_adapter_invariant_detects_incomplete_observed_binding(self):
        self._install_platform_contract()
        canonical = self._hook_document(("SessionStart", "session-start"), ("Stop", "stop"))
        (self.temp / "enforcement" / "hooks" / "hooks.json").write_text(
            json.dumps(canonical), encoding="utf-8"
        )
        installed = self._hook_document(("SessionStart", "session-start"))
        installed["private_note"] = "adapter-secret-must-not-leak"
        adapter = self.temp / ".claude" / "settings.json"
        adapter.parent.mkdir(parents=True, exist_ok=True)
        adapter.write_text(json.dumps(installed), encoding="utf-8")

        broken = product.build_platform(self.temp)
        invariant = next(item for item in broken["invariants"] if item["id"] == "ring1_adapter_binding")
        self.assertEqual("fail", invariant["status"])
        self.assertIn("incomplete_provider_binding", invariant["failure_codes"])
        self.assertEqual("fail", broken["summary"]["check_status"])
        self.assertNotIn("adapter-secret-must-not-leak", json.dumps(broken))
        self.assertNotIn(str(self.temp), json.dumps(broken))
        with mock.patch.object(product, "ROOT", self.temp), mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(2, product.main(["platform", "--check", "--json"]))

        adapter.write_text(json.dumps(canonical), encoding="utf-8")
        repaired = product.build_platform(self.temp)
        invariant = next(item for item in repaired["invariants"] if item["id"] == "ring1_adapter_binding")
        self.assertEqual("pass", invariant["status"])
        self.assertEqual("pass", repaired["summary"]["check_status"])

    def test_platform_receipt_invariant_validates_references_without_reading_log(self):
        self._install_platform_contract()
        canonical = self._hook_document(("SessionStart", "session-start"))
        (self.temp / "enforcement" / "hooks" / "hooks.json").write_text(
            json.dumps(canonical), encoding="utf-8"
        )
        receipt = self.temp / ".vemo" / "run" / "receipt.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text("{", encoding="utf-8")
        malformed = product.build_platform(self.temp)
        invariant = next(item for item in malformed["invariants"] if item["id"] == "verification_receipt_chain")
        self.assertEqual("fail", invariant["status"])
        self.assertIn("receipt_valid", invariant["failure_codes"])

        receipt.write_text(json.dumps({
            "task": "T-demo",
            "log": ".vemo/run/T-demo.log",
        }), encoding="utf-8")
        stale = product.build_platform(self.temp)
        invariant = next(item for item in stale["invariants"] if item["id"] == "verification_receipt_chain")
        self.assertEqual("fail", invariant["status"])
        self.assertIn("task_record_present", invariant["failure_codes"])
        self.assertIn("evidence_log_present", invariant["failure_codes"])

        (self.temp / "tasks" / "T-demo.md").write_text("task\n", encoding="utf-8")
        (self.temp / ".vemo" / "run" / "T-demo.log").write_text(
            "evidence-secret-must-not-leak\n", encoding="utf-8"
        )
        linked = product.build_platform(self.temp)
        invariant = next(item for item in linked["invariants"] if item["id"] == "verification_receipt_chain")
        self.assertEqual("pass", invariant["status"])
        self.assertTrue(all(invariant["checks"].values()))
        self.assertNotIn("evidence-secret-must-not-leak", json.dumps(linked))

        receipt.write_text(json.dumps({"task": "T-demo", "log": "../outside.log"}), encoding="utf-8")
        unsafe = product.build_platform(self.temp)
        invariant = next(item for item in unsafe["invariants"] if item["id"] == "verification_receipt_chain")
        self.assertEqual("fail", invariant["status"])
        self.assertFalse(invariant["checks"]["log_reference_safe"])

        receipt.write_text(json.dumps({
            "task": "T-demo", "log": ".vemo/run/bad\x00name.log",
        }), encoding="utf-8")
        nul_path = product.build_platform(self.temp)
        invariant = next(item for item in nul_path["invariants"] if item["id"] == "verification_receipt_chain")
        self.assertEqual("fail", invariant["status"])
        self.assertFalse(invariant["checks"]["log_reference_safe"])

    def test_platform_rejects_out_of_checkout_symlink_without_reading_target(self):
        self._install_platform_contract()
        canonical = self._hook_document(("SessionStart", "session-start"))
        (self.temp / "enforcement" / "hooks" / "hooks.json").write_text(
            json.dumps(canonical), encoding="utf-8"
        )
        config = self.temp / "vemo.config.yaml"
        config.unlink()
        with tempfile.TemporaryDirectory(prefix="vemo_product_external_") as external:
            target = Path(external) / "vemo.config.yaml"
            sentinel = "external-symlink-secret-must-not-leak"
            target.write_text(
                "capability:\n  tier: %s\nenforcement:\n  mode: enforce\n" % sentinel,
                encoding="utf-8",
            )
            try:
                config.symlink_to(target)
            except (NotImplementedError, OSError) as error:
                self.skipTest("symlinks unavailable: %s" % error)
            payload = product.build_platform(self.temp)

        policy = next(plane for plane in payload["planes"] if plane["id"] == "policy")
        component = next(item for item in policy["components"] if item["id"] == "configuration")
        self.assertFalse(component["present"])
        self.assertEqual("unknown", payload["runtime"]["capability_tier"])
        self.assertEqual("fail", payload["summary"]["check_status"])
        self.assertNotIn(sentinel, json.dumps(payload))
        self.assertNotIn(str(target), json.dumps(payload))

    def test_platform_delivery_posture_reports_only_locally_observable_facts(self):
        self.assertEqual("advisory", product.build_platform(self.temp)["summary"]["delivery_posture"])
        hooks = self.temp / ".git" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "pre-commit").write_text("gate\n", encoding="utf-8")
        (hooks / "pre-push").write_text("gate\n", encoding="utf-8")
        local = product.build_platform(self.temp)
        self.assertEqual("local_gates", local["summary"]["delivery_posture"])

        workflow = self.temp / ".github" / "workflows" / "vemo-ci.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: vemo\n", encoding="utf-8")
        ci_backed = product.build_platform(self.temp)
        self.assertEqual("ci_backstop_present", ci_backed["summary"]["delivery_posture"])
        self.assertEqual("not_locally_verified", ci_backed["authority"]["remote_branch_protection"])

    def test_platform_check_fails_when_extension_composition_cannot_resolve(self):
        self._install_platform_contract()
        manifest = self.temp / "extensions" / "ring1-guard" / "extension.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["requires"] = ["vemo.missing-service"]
        manifest.write_text(json.dumps(document), encoding="utf-8")

        payload = product.build_platform(self.temp)

        self.assertEqual("fail", payload["summary"]["extension_status"])
        self.assertEqual("fail", payload["summary"]["check_status"])
        self.assertIn("missing_required_capability", payload["summary"]["extension_issue_codes"])
        self.assertNotIn("ring1_guard", {seam["id"] for seam in payload["capability_seams"]})
        with mock.patch.object(product, "ROOT", self.temp), mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(2, product.main(["platform", "--check", "--json"]))

    def test_platform_cli_emits_json_and_docs_link_the_contract(self):
        command = [sys.executable, str(ROOT / "bin" / "vemo"), "platform", "--check", "--json"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(3, payload["schema_version"])
        self.assertTrue(payload["read_only"])
        self.assertEqual("vemo platform", payload["command"])
        self.assertEqual("pass", payload["summary"]["check_status"])

    # Repository documentation is not part of the installed payload; installed copies of this suite
    # under eval/tests verify the runtime only.
    @unittest.skipUnless((ROOT / "docs" / "PLATFORM.md").is_file(), "repository docs are not installed payload")
    def test_repository_docs_link_the_platform_contract(self):
        platform_doc = (ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
        for phrase in (
            "Responsibility planes", "Capability seams", "Relationship invariants",
            "Extension composition", "Authority boundaries", "Request lifecycle", "Wildmeerkat",
            "DeepSeek Harness",
        ):
            self.assertIn(phrase, platform_doc)
        self.assertIn("docs/PLATFORM.md", (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8"))
        for relative in ("README.md", "docs/INDEX.md"):
            self.assertIn("docs/PLATFORM.md", (ROOT / relative).read_text(encoding="utf-8"))
        self.assertIn("docs/EXTENSIONS.md", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("EXTENSIONS.md", (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
