import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enforcement"))
import core


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.root, check=True)
        (self.root / ".vemo/evidence").mkdir(parents=True); (self.root / "src").mkdir()
        self.write_policy(); self.write_task(); (self.root / "src/app.py").write_text("x=1\n")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.root, check=True)

    def tearDown(self): self.tmp.cleanup()

    def write_policy(self, **updates):
        value = {"version": 2, "critical_paths": ["critical/**"],
                 "deny_actions": ["destructive_fs", "git_history_rewrite", "credential_write", "out_of_repo_write"],
                 "verification": {"normal": [["python3", "-c", "print('ok')"]],
                                  "critical": [["python3", "-c", "print('critical')"]]},
                 "plugins": []}; value.update(updates)
        (self.root / "vemo.json").write_text(json.dumps(value))

    def write_task(self, **updates):
        value = {"version": 1, "id": "T-test", "scope": ["src/**"], "risk": "normal"}; value.update(updates)
        (self.root / "vemo.task.json").write_text(json.dumps(value))

    def stage_change(self, text="x=2\n"):
        (self.root / "src/app.py").write_text(text); subprocess.run(["git", "add", "src/app.py"], cwd=self.root, check=True)

    def approval(self):
        return {"VEMO_APPROVED_TASK": "T-test", "VEMO_APPROVED_BY": "human",
                "VEMO_APPROVED_TASK_DIGEST": core.task_digest(core.load_task(self.root))}

    def test_action_scope_secret_and_destructive_decisions(self):
        self.assertEqual("allow", core.check_action("write", "src/app.py", root=self.root)["decision"])
        self.assertEqual("scope_violation", core.check_action("write", "other.py", root=self.root)["reason"])
        secret_fixture = "api_key='" + "a" * 16 + "'"
        self.assertEqual("credential_write", core.check_action("write", "src/app.py", content=secret_fixture, root=self.root)["reason"])
        aws_fixture = "AWS_SECRET_ACCESS_KEY=" + "a" * 40
        self.assertEqual("credential_write", core.check_action("write", "src/app.py", content=aws_fixture, root=self.root)["reason"])
        audit_fixture = "AWS_SECRET_ACCESS_KEY=deny/credential_write"
        self.assertEqual("allow", core.check_action("write", "src/app.py", content=audit_fixture, root=self.root)["decision"])
        for prefix in ("allow_", "redacted-", "approval_required_", "blocked/"):
            bypass_fixture = "AWS_SECRET_ACCESS_KEY=" + prefix + "a" * 32
            self.assertEqual("credential_write", core.check_action(
                "write", "src/app.py", content=bypass_fixture, root=self.root)["reason"])
        self.assertEqual("approval_required", core.check_action("command", command="rm -rf build", root=self.root)["decision"])
        self.assertEqual("out_of_repo_write", core.check_action("command", command="echo x > ../outside", root=self.root)["reason"])
        python_delete = "python3 -c \"import shutil; shutil.rmtree('../outside')\""
        self.assertEqual("destructive_fs", core.check_action("command", command=python_delete, root=self.root)["reason"])
        old = dict(__import__('os').environ)
        try:
            __import__('os').environ.update(self.approval())
            self.assertEqual("approval_required", core.check_action("command", command="rm -rf build", root=self.root)["decision"])
            __import__('os').environ["VEMO_APPROVED_ACTIONS"] = "destructive_fs"
            self.assertEqual("allow", core.check_action("command", command="rm -rf build", root=self.root)["decision"])
            self.assertEqual("approval_required", core.check_action("write", "/outside/file", root=self.root)["decision"])
            __import__('os').environ["VEMO_APPROVED_ACTIONS"] = "out_of_repo_write"
            self.assertEqual("allow", core.check_action("write", "/outside/file", root=self.root)["decision"])
        finally:
            __import__('os').environ.clear(); __import__('os').environ.update(old)

    def test_evidence_is_bound_to_snapshot_and_commands(self):
        self.stage_change(); self.assertEqual("verification_missing", core.check_merge(self.root)["reason"])
        self.assertTrue(core.verify(self.root)["passed"]); self.assertEqual("allow", core.check_merge(self.root)["decision"])
        self.stage_change("x=3\n"); self.assertEqual("verification_stale", core.check_merge(self.root)["reason"])
        self.write_task(scope=["src/**", "vemo.json"])
        self.write_policy(verification={"normal": [["python3", "-c", "print('different')"]],
                                        "critical": [["python3", "-c", "print('critical')"]]})
        subprocess.run(["git", "add", "vemo.json", "vemo.task.json"], cwd=self.root, check=True)
        with mock.patch.dict(os.environ, self.approval()):
            self.assertEqual("verification_stale", core.check_merge(self.root)["reason"])

    def test_verification_is_argv_only_and_does_not_invoke_shell(self):
        self.write_policy(verification={"normal": ["echo unsafe > outside"],
                                        "critical": [["python3", "-c", "print('ok')"]]})
        with self.assertRaises(core.VemoError):
            core.load_policy(self.root)

    def test_unstaged_task_cannot_expand_scope_for_staged_diff(self):
        (self.root / "outside.py").write_text("x=1\n")
        subprocess.run(["git", "add", "outside.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "outside change"], cwd=self.root, check=True)
        self.write_task(scope=["src/**", "outside.py"])
        self.assertEqual("contract_unstaged", core.check_merge(self.root, require_evidence=False)["reason"])
        self.assertEqual("contract_unstaged", core.check_merge(self.root, "HEAD~1..HEAD", False)["reason"])

    def test_generated_audit_evidence_does_not_trigger_source_secret_scan(self):
        (self.root / ".vemo/judge.jsonl").write_text(
            '{"evidence":"token=' + 'allow_' + 'abcdefghijklmnop"}\n')
        subprocess.run(["git", "add", ".vemo/judge.jsonl"], cwd=self.root, check=True)
        self.assertEqual("allow", core.check_merge(self.root, require_evidence=False)["decision"])

    def test_scope_authorization_is_part_of_snapshot(self):
        self.stage_change(); self.assertTrue(core.verify(self.root)["passed"])
        self.write_task(scope=["src/**", "other/**"])
        subprocess.run(["git", "add", "vemo.task.json"], cwd=self.root, check=True)
        with mock.patch.dict(os.environ, self.approval()):
            self.assertEqual("verification_stale", core.check_merge(self.root)["reason"])

    def test_critical_change_requires_approval(self):
        (self.root / "critical").mkdir(); (self.root / "critical/policy.py").write_text("x=1\n")
        self.write_task(scope=["src/**", "critical/**"]); subprocess.run(["git", "add", "vemo.task.json", "critical/policy.py"], cwd=self.root, check=True)
        self.assertEqual("approval_required", core.check_merge(self.root, require_evidence=False)["decision"])
        old = dict(os.environ)
        try:
            os.environ.update(self.approval())
            self.assertEqual("allow", core.check_merge(self.root, require_evidence=False)["decision"])
            self.write_task(scope=["src/**", "critical/**", "outside/**"])
            subprocess.run(["git", "add", "vemo.task.json"], cwd=self.root, check=True)
            self.assertEqual("approval_required", core.check_merge(self.root, require_evidence=False)["decision"])
        finally:
            os.environ.clear(); os.environ.update(old)

    def test_unknown_policy_fields_fail_closed(self):
        self.write_policy(surprise=True)
        with self.assertRaises(core.VemoError): core.load_policy(self.root)

    def test_task_cannot_self_grant_approval(self):
        self.write_task(approval={"granted": True})
        with self.assertRaises(core.VemoError): core.load_task(self.root)

    def test_task_create_replaces_only_the_distribution_placeholder(self):
        with self.assertRaises(core.VemoError):
            core.write_task("T-new", ["src/**"], root=self.root)
        example = {"version": 1, "id": "T-example", "scope": ["src/**"], "risk": "normal"}
        (self.root / "vemo.task.example.json").write_text(json.dumps(example))
        (self.root / "vemo.task.json").write_text(json.dumps(example))
        created = core.write_task("T-new", ["src/**"], root=self.root)
        self.assertEqual("T-new", created["id"])

    def test_legacy_migration_preserves_scope_and_raises_r2(self):
        (self.root / "vemo.task.json").unlink(); (self.root / "tasks").mkdir()
        (self.root / "tasks/T-legacy.md").write_text(
            '---\nid: T-legacy\nrisk: R2\nstate: AcceptancePassed\n'
            'scope_in: ["src/**", "tests/**"]\nheartbeat: 2026-09-11T00:00:00Z\n---\n')
        result = core.migrate(self.root); task = json.loads((self.root / "vemo.task.json").read_text())
        self.assertTrue(result["changed"]); self.assertEqual("critical", task["risk"])
        self.assertEqual(["src/**", "tests/**"], task["scope"]); self.assertNotIn("approval", task)

    def test_legacy_config_migration_fails_closed_instead_of_weakening_policy(self):
        (self.root / "vemo.task.json").unlink(); (self.root / "vemo.config.yaml").write_text(
            'risk_tiers:\n  R2_critical:\n    match_paths:\n      - "payments/**"\n'
            'paths:\n  build: "make test"\n  smoke: "make smoke"\n')
        with self.assertRaisesRegex(core.VemoError, "explicit mapping"):
            core.migrate(self.root)

    def test_plugin_enablement_and_collision(self):
        (self.root / "plugins/a").mkdir(parents=True); (self.root / "tool.py").write_text("print('a')\n")
        (self.root / "plugins/a/plugin.json").write_text(json.dumps({"version": 1, "name": "a", "commands": {"extra": ["tool.py"]}}))
        self.assertEqual({}, core.enabled_plugin_commands(self.root))
        core.set_plugin("a", True, self.root); self.assertIn("extra", core.enabled_plugin_commands(self.root))
        (self.root / "plugins/b").mkdir(); (self.root / "plugins/b/plugin.json").write_text(json.dumps({"version": 1, "name": "b", "commands": {"extra": ["tool.py"]}}))
        policy = core.load_policy(self.root); policy["plugins"].append("b"); (self.root / "vemo.json").write_text(json.dumps(policy))
        with self.assertRaises(core.VemoError): core.enabled_plugin_commands(self.root)

    def test_disabled_invalid_plugin_cannot_break_core(self):
        (self.root / "plugins/broken").mkdir(parents=True)
        (self.root / "plugins/broken/plugin.json").write_text("not json")
        self.assertEqual({}, core.enabled_plugin_commands(self.root))
        self.assertEqual("allow", core.check_action("write", "src/app.py", root=self.root)["decision"])


class RepositoryContractTests(unittest.TestCase):
    def test_default_help_has_six_core_concepts(self):
        completed = subprocess.run([sys.executable, str(ROOT / "bin/vemo"), "--help"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stderr)
        commands = [line.split()[0] for line in completed.stdout.splitlines() if line.startswith("  ")]
        self.assertEqual(["task", "check", "verify", "status", "init", "plugin"], commands)

    def test_default_payload_excludes_plugins(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        self.assertFalse(any(path.startswith(payload.FORBIDDEN_CORE_PREFIXES) for path in payload.CORE_FILES))
        self.assertLessEqual(len(payload.CORE_FILES), 14)

    def test_packaged_core_runs_without_plugins(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            shutil.copy2(target / "vemo.task.example.json", target / "vemo.task.json")
            completed = subprocess.run([sys.executable, "bin/vemo", "check", "--self"], cwd=target,
                                       capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertFalse((target / "plugins").exists())

    def test_lightweight_installer_refuses_conflicting_hook(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            hook = target / ".git/hooks/pre-commit"; hook.write_text("#!/bin/sh\necho custom\n")
            before = hook.read_bytes()
            completed = subprocess.run(["bash", "enforcement/install.sh"], cwd=target,
                                       capture_output=True, text=True)
            self.assertEqual(2, completed.returncode)
            self.assertEqual(before, hook.read_bytes())
            self.assertIn("refuses to overwrite", completed.stderr)

    def test_repository_guides_reference_current_cli(self):
        guides = [ROOT / "README.md", ROOT / "docs/USAGE.md", ROOT / "docs/INSTALL.md"]
        if not all(path.is_file() for path in guides):
            self.skipTest("repository documentation is not part of the core payload")
        retired = re.compile(r"bin/vemo (?:context|tier|report|platform|extensions|doctor|eval|explain|start)")
        for path in guides:
            self.assertIsNone(retired.search(path.read_text(encoding="utf-8")), str(path))
        self.assertIn("plugins/setup/entry.py setup install", guides[2].read_text(encoding="utf-8"))

    def test_plugin_manifest_cannot_replace_core_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "plugins/bad").mkdir(parents=True); (root / "tool.py").write_text("pass\n")
            (root / "vemo.json").write_text(json.dumps({"version": 2, "critical_paths": [],
                "deny_actions": [], "verification": {"normal": [["true"]], "critical": [["true"]]},
                "plugins": ["bad"]}))
            (root / "plugins/bad/plugin.json").write_text(json.dumps({"version": 1, "name": "bad",
                "commands": {"verify": ["tool.py"]}}))
            with self.assertRaises(core.VemoError): core.enabled_plugin_commands(root)

    def test_bundled_plugin_entrypoints_are_runnable(self):
        if not (ROOT / "plugins").is_dir(): self.skipTest("bundled plugins are not part of the core payload")
        manifests = core.plugin_manifests(ROOT)
        self.assertEqual({"automation", "fleet", "product", "review", "setup", "skills"}, set(manifests))
        for name, manifest in manifests.items():
            entry = next(iter(manifest["commands"].values()))
            completed = subprocess.run([sys.executable, str(ROOT / entry[0]), *entry[1:], "--help"],
                                       cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, name + ": " + completed.stdout + completed.stderr)


if __name__ == "__main__": unittest.main()
