import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vemo_product", ROOT / "bin" / "vemo_product.py")
product = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(product)
TS_SPEC = importlib.util.spec_from_file_location("task_state_product_test", ROOT / "enforcement" / "validators" / "task_state.py")
task_state = importlib.util.module_from_spec(TS_SPEC)
TS_SPEC.loader.exec_module(task_state)


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vemo_product_test_"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

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


if __name__ == "__main__":
    unittest.main()
