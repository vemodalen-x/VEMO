import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from urllib.request import urlopen

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

    def test_only_current_task_evidence_is_implicitly_authorized(self):
        foreign = self.root / ".vemo/evidence/T-other.json"
        foreign.write_text('{"passed":true}\n')
        subprocess.run(["git", "add", str(foreign)], cwd=self.root, check=True)
        result = core.check_merge(self.root, require_evidence=False)
        self.assertEqual("scope_violation", result["reason"])
        self.assertEqual(".vemo/evidence/T-other.json", result["evidence"]["path"])

    def test_authorized_foreign_evidence_is_bound_into_snapshot(self):
        self.write_task(scope=["src/**", ".vemo/evidence/T-other.json"])
        foreign = self.root / ".vemo/evidence/T-other.json"
        foreign.write_text('{"passed":true}\n')
        subprocess.run(["git", "add", "vemo.task.json", str(foreign)], cwd=self.root, check=True)
        first = core.snapshot(self.root)
        foreign.write_text('{"passed":false}\n')
        subprocess.run(["git", "add", str(foreign)], cwd=self.root, check=True)
        self.assertNotEqual(first, core.snapshot(self.root))

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

    def test_lightweight_installer_preflights_all_managed_files(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            hook = target / ".git/hooks/pre-commit"; hook.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target / "enforcement/ci/pre-commit", hook)
            push = target / ".git/hooks/pre-push"; push.write_text("#!/bin/sh\necho custom\n")
            before = hook.read_bytes()
            completed = subprocess.run(["bash", "enforcement/install.sh"], cwd=target,
                                       capture_output=True, text=True)
            self.assertEqual(2, completed.returncode)
            self.assertEqual(before, hook.read_bytes())
            self.assertEqual("#!/bin/sh\necho custom\n", push.read_text())
            self.assertFalse((target / ".github/workflows/vemo-ci.yml").exists())

    @unittest.skipIf(os.name == "nt", "symbolic-link behavior is platform specific")
    def test_lightweight_installer_rejects_linked_parent_before_any_write(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target, outside = Path(td) / "target", Path(td) / "outside"
            target.mkdir(); outside.mkdir(); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            (target / ".claude").symlink_to(outside, target_is_directory=True)
            completed = subprocess.run(["bash", "enforcement/install.sh"], cwd=target,
                                       capture_output=True, text=True)
            self.assertEqual(2, completed.returncode)
            self.assertIn("symlinked managed path", completed.stderr)
            self.assertEqual([], list(outside.iterdir()))
            self.assertFalse((target / ".git/hooks/pre-commit").exists())
            self.assertFalse((target / ".github/workflows/vemo-ci.yml").exists())

    def test_lightweight_installer_rejects_invalid_claude_settings_before_any_write(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            settings = target / ".claude/settings.json"
            settings.parent.mkdir(); settings.write_text("not json\n")
            completed = subprocess.run(["bash", "enforcement/install.sh"], cwd=target,
                                       capture_output=True, text=True)
            self.assertNotEqual(0, completed.returncode)
            self.assertEqual("not json\n", settings.read_text())
            self.assertFalse((target / ".git/hooks/pre-commit").exists())
            self.assertFalse((target / ".github/workflows/vemo-ci.yml").exists())

    @unittest.skipIf(os.name == "nt", "symbolic-link behavior is platform specific")
    def test_lightweight_installer_rejects_linked_framework_source(self):
        spec = importlib.util.spec_from_file_location("payload", ROOT / "enforcement/payload.py")
        payload = importlib.util.module_from_spec(spec); spec.loader.exec_module(payload)
        with tempfile.TemporaryDirectory() as td:
            target, outside = Path(td) / "target", Path(td) / "outside-vemo"
            target.mkdir(); outside.mkdir(); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for relative in payload.CORE_FILES:
                source, destination = ROOT / relative, target / relative
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
            (target / "bin/vemo").unlink()
            (target / "bin/vemo").symlink_to(outside / "vemo")
            (outside / "vemo").write_text("unchanged\n")
            completed = subprocess.run(["bash", "enforcement/install.sh"], cwd=target,
                                       capture_output=True, text=True)
            self.assertEqual(2, completed.returncode)
            self.assertIn("symlinked managed path", completed.stderr)
            self.assertEqual("unchanged\n", (outside / "vemo").read_text())
            self.assertFalse((target / ".git/hooks/pre-commit").exists())

    def test_repository_guides_reference_current_cli(self):
        guides = [ROOT / "README.md", ROOT / "docs/USAGE.md", ROOT / "docs/INSTALL.md",
                  ROOT / "docs/PLATFORMS.md", ROOT / "docs/AI-INSTALL.md", ROOT / "docs/EXAMPLES.md"]
        if not all(path.is_file() for path in guides):
            self.skipTest("repository documentation is not part of the core payload")
        retired = re.compile(r"bin/vemo (?:context|tier|report|platform|extensions|doctor|eval|explain|start)")
        for path in guides:
            self.assertIsNone(retired.search(path.read_text(encoding="utf-8")), str(path))
        self.assertIn("plugins/setup/entry.py setup install", guides[2].read_text(encoding="utf-8"))

    def test_delivery_documentation_has_platform_ai_and_examples_navigation(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = (ROOT / "docs/INSTALL.md").read_text(encoding="utf-8")
        platforms = (ROOT / "docs/PLATFORMS.md").read_text(encoding="utf-8")
        ai_install = (ROOT / "docs/AI-INSTALL.md").read_text(encoding="utf-8")
        examples = (ROOT / "docs/EXAMPLES.md").read_text(encoding="utf-8")
        for name in ("PLATFORMS.md", "AI-INSTALL.md", "EXAMPLES.md"):
            self.assertIn(name, readme)
        self.assertIn("PLATFORMS.md", install)
        for platform in ("Linux", "macOS", "Windows", "GitHub Actions", "Claude Code"):
            self.assertIn(platform, platforms)
        self.assertIn("--plan-id", ai_install)
        self.assertIn("VEMO_APPROVED_*", ai_install)
        self.assertIn("Out-of-scope change", examples)
        self.assertTrue((ROOT / "plugins/setup/ui/start.command").is_file())
        self.assertTrue((ROOT / "plugins/setup/ui/start.cmd").is_file())

    def test_control_plane_documentation_matches_current_fleet_contract(self):
        paths = [ROOT / "README.md", ROOT / "docs/USAGE.md", ROOT / "docs/INSTALL.md",
                 ROOT / "docs/PLUGINS.md", ROOT / "docs/PLATFORMS.md"]
        for path in paths:
            self.assertIn("CONTROL-PLANE.md", path.read_text(encoding="utf-8"), str(path))
        active = paths + [ROOT / "SECURITY.md", ROOT / "CONTRIBUTING.md", ROOT / "ROADMAP.md",
                          ROOT / "docs/AI-INSTALL.md", ROOT / "docs/EXAMPLES.md",
                          ROOT / "docs/MIGRATION.md", ROOT / "docs/CONTROL-PLANE.md",
                          ROOT / "plugins/setup/ui/help/install.html",
                          ROOT / "plugins/setup/ui/help/usage.html",
                          ROOT / "plugins/setup/ui/help/design.html"]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in active)
        for stale in ("plugin enable product", "plugin disable product", "plugins/product",
                      "fleet onboard", "fleet profiles", "fleet install"):
            self.assertNotIn(stale, combined)
        self.assertIn("plugins/fleet/main.py register", combined)
        self.assertIn("plugins/fleet/main.py serve", combined)
        self.assertNotIn("不安装 Fleet、UI、product", combined)
        self.assertNotIn("/home/aimer", combined)
        self.assertNotIn("14-file core payload", combined)
        self.assertNotIn("14 个文件", combined)

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
        self.assertEqual({"automation", "fleet", "review", "setup", "skills"}, set(manifests))
        for name, manifest in manifests.items():
            for command, entry in manifest["commands"].items():
                completed = subprocess.run([sys.executable, str(ROOT / entry[0]), *entry[1:], "--help"],
                                           cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(0, completed.returncode,
                                 name + ":" + command + ": " + completed.stdout + completed.stderr)

    def test_call_graph_tool_uses_argv_without_shell_execution(self):
        script = (ROOT / "plugins/skills/skill/call-graph/scripts/cg.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", script)
        self.assertNotIn("os.popen", script)

    def test_setup_apply_requires_a_content_bound_preview(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            for action in ("install", "uninstall"):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "plugins/setup/entry.py"), "setup", action,
                     str(target), "--apply", "--json"],
                    cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(2, completed.returncode)
                self.assertIn("plan_id", completed.stderr)

    def test_setup_preview_id_drives_install_check_and_uninstall(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            entry = str(ROOT / "plugins/setup/entry.py")

            def setup(*args):
                return subprocess.run([sys.executable, entry, "setup", *args, "--json"],
                                      cwd=ROOT, capture_output=True, text=True)

            preview = setup("install", str(target))
            self.assertEqual(0, preview.returncode, preview.stderr)
            plan_id = json.loads(preview.stdout)["plan_id"]
            stale = setup("install", str(target), "--apply", "--plan-id", "0" * 64)
            self.assertEqual(2, stale.returncode)
            self.assertIn("重新预览", stale.stderr)
            applied = setup("install", str(target), "--apply", "--plan-id", plan_id)
            self.assertEqual(0, applied.returncode, applied.stderr)
            checked = setup("check", str(target))
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["ready"])
            removal = setup("uninstall", str(target))
            remove_id = json.loads(removal.stdout)["plan_id"]
            removed = setup("uninstall", str(target), "--apply", "--plan-id", remove_id)
            self.assertEqual(0, removed.returncode, removed.stderr)

    def test_fleet_registry_probe_and_audit_are_user_local(self):
        spec = importlib.util.spec_from_file_location("vemo_fleet", ROOT / "plugins/fleet/main.py")
        fleet = importlib.util.module_from_spec(spec); spec.loader.exec_module(fleet)
        with tempfile.TemporaryDirectory() as td:
            home, target = Path(td) / "home", Path(td) / "project"
            target.mkdir(); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            store = fleet.FleetStore(home)
            registered = store.register(target, "Fixture")
            self.assertEqual("Fixture", registered["label"])
            self.assertFalse((target / "vemo.json").exists())
            unmanaged = fleet.probe_project(registered, detail=True)
            self.assertEqual("unmanaged", unmanaged["status"])
            self.assertTrue(store.audit_status()["valid"])
            if os.name != "nt":
                self.assertEqual(0o700, home.stat().st_mode & 0o777)
                self.assertEqual(0o600, store.registry.stat().st_mode & 0o777)
                self.assertEqual(0o600, store.audit.stat().st_mode & 0o777)
            removed = store.unregister(registered["id"])
            self.assertEqual(registered["id"], removed["id"])
            self.assertEqual([], store.load()["projects"])

    def test_fleet_discovery_finds_nested_projects_below_a_git_root(self):
        spec = importlib.util.spec_from_file_location("vemo_fleet_discover", ROOT / "plugins/fleet/main.py")
        fleet = importlib.util.module_from_spec(spec); spec.loader.exec_module(fleet)
        with tempfile.TemporaryDirectory() as td:
            outer, nested = Path(td), Path(td) / "group" / "nested"
            nested.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=outer, check=True)
            subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
            self.assertEqual({str(outer), str(nested)}, set(fleet.discover_projects([outer], 3)))

    @unittest.skipIf(os.name == "nt", "symbolic-link behavior is platform specific")
    def test_fleet_refuses_linked_state_files_before_registry_mutation(self):
        spec = importlib.util.spec_from_file_location("vemo_fleet_links", ROOT / "plugins/fleet/main.py")
        fleet = importlib.util.module_from_spec(spec); spec.loader.exec_module(fleet)
        with tempfile.TemporaryDirectory() as td:
            home, target = Path(td) / "home", Path(td) / "project"
            home.mkdir(); target.mkdir(); subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            destination = Path(td) / "outside-audit"
            destination.write_text("unchanged\n")
            (home / "control-audit.jsonl").symlink_to(destination)
            store = fleet.FleetStore(home)
            with self.assertRaises(fleet.FleetError):
                store.audit_status()
            with self.assertRaises(fleet.FleetError):
                store.register(target)
            self.assertFalse(store.registry.exists())
            self.assertEqual("unchanged\n", destination.read_text())

    def test_fleet_dashboard_serves_overview_and_project_detail(self):
        spec = importlib.util.spec_from_file_location("vemo_fleet_http", ROOT / "plugins/fleet/main.py")
        fleet = importlib.util.module_from_spec(spec); spec.loader.exec_module(fleet)
        with tempfile.TemporaryDirectory() as td:
            store = fleet.FleetStore(Path(td) / "home")
            store.register(ROOT, "VEMO")
            server = fleet.HTTPServer(("127.0.0.1", 0), fleet.DashboardHandler)
            server.store = store
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                page = urlopen(base + "/", timeout=5)
                html = page.read().decode()
                overview = json.loads(urlopen(base + "/api/overview", timeout=5).read())
                identifier = overview["projects"][0]["id"]
                detail = json.loads(urlopen(base + "/api/project?id=" + identifier, timeout=5).read())
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=5)
            self.assertIn("VEMO Control Plane", html)
            self.assertIn("default-src 'self'", page.headers["Content-Security-Policy"])
            self.assertEqual(1, overview["summary"]["projects"])
            self.assertEqual("VEMO", detail["label"])
            self.assertIn(detail["gate"]["decision"], {"allow", "deny", "approval_required"})
            self.assertTrue(any(row["id"] == "policy" for row in detail["controls"]))


if __name__ == "__main__": unittest.main()
