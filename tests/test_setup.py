"""Real installation lifecycle and browser API boundary checks."""

import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":  # Installed framework tests live under eval/tests, apart from application tests.
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "bin"))
from vemo_setup import service
from vemo_setup.payload import managed_sources
from vemo_setup.server import SetupServer


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The CI template runs this suite in consuming projects as well as the development repo.
        # Use a fresh distribution source; a user's installed project is never a deployment source.
        global ROOT
        cls.original_root = ROOT
        cls.source_fixture = tempfile.TemporaryDirectory(prefix="vemo-test-source-")
        source = Path(cls.source_fixture.name)
        for relative, file in managed_sources(ROOT).items():
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
            if relative == "AGENTS.md":
                text = target.read_text(encoding="utf-8")
                if text.count(service.BEGIN) == text.count(service.END) == 1:
                    target.write_text(text.split(service.BEGIN, 1)[1].split(service.END, 1)[0].strip() + "\n", encoding="utf-8")
        ROOT = source

    @classmethod
    def tearDownClass(cls):
        global ROOT
        ROOT = cls.original_root
        if cls.source_fixture:
            cls.source_fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vemo-setup-")
        self.root = Path(self.temp.name) / "中文 项目"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def install(self):
        return service.apply_install(ROOT, str(self.root), "docs")

    def test_preview_is_read_only_and_payload_is_complete(self):
        before = self.snapshot()
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.assertTrue(plan["ready"])
        self.assertEqual(before, self.snapshot())
        paths = {row["path"] for row in plan["actions"]}
        for required in ("bin/vemo_extensions.py", "bin/vemo_composition/loader.py", "extensions/index.json", "ui/app.js", "skill/_catalog.md", "eval/run.py", "eval/tests/test_setup.py"):
            self.assertIn(required, paths)
        self.assertFalse(any(p.startswith("tasks/T-") or "VEMO_SKILLS" in p for p in paths))
        # Repository documents a consuming project owns itself are not payload.
        self.assertFalse({"README.md", "LICENSE", "SECURITY.md"} & paths)
        self.assertFalse(any(p.startswith(("docs/", "assets/")) for p in paths))

    def test_project_owned_documents_are_neither_conflicts_nor_payload(self):
        owned = {"README.md": "# My application\n", "LICENSE": "Proprietary\n", "SECURITY.md": "Mail us.\n",
                 "docs/INSTALL.md": "# Installing my application\n", "assets/logo.svg": "<svg/>\n"}
        for relative, content in owned.items():
            self.write(relative, content)
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.assertEqual([], plan["conflicts"])
        self.assertFalse(set(owned) & {row["path"] for row in plan["actions"]})
        self.install()
        for relative, content in owned.items():
            self.assertEqual(content, (self.root / relative).read_text(encoding="utf-8"), relative)
        self.assertFalse((self.root / "docs/PLATFORM.md").exists())

    def test_unicode_install_idempotence_and_uninstall_preserve_originals_and_records(self):
        self.write("AGENTS.md", "# 项目规则\n保留它。\n")
        self.write("README.md", "# My application\n")
        self.write(".claude/settings.json", '{"permissions":{"allow":["Read"]},"hooks":{"SessionStart":[]}}')
        self.write(".gitignore", "private/\n")
        original = self.snapshot()
        result = self.install()
        self.assertTrue(result["verification"]["ready"])
        self.assertIn("保留它", (self.root / "AGENTS.md").read_text())
        self.assertEqual("# My application\n", (self.root / "README.md").read_text())
        self.assertEqual(["Read"], json.loads((self.root / ".claude/settings.json").read_text())["permissions"]["allow"])
        again = service.plan_install(ROOT, str(self.root), "docs")
        self.assertTrue(all(row["status"] == "unchanged" for row in again["actions"]))
        self.assertTrue(service.check_install(str(self.root))["ready"])
        # Probe the actual installed edit guard against a bounded task, not just file presence.
        self.write("tasks/T-probe.md", '---\nid: T-probe\nrisk: R1\nstate: PlanCreated\nscope_in: ["allowed/**"]\n---\n## Plan\nProbe\n')
        probe = service.run([sys.executable, "enforcement/hooks/run.py", "edit"], self.root,
                            input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(self.root / "outside.py"), "content": "print(1)"}}))
        self.assertEqual(2, probe.returncode, probe.stdout + probe.stderr)
        push_gate = service.run(["bash", ".git/hooks/pre-push"], self.root, input="")
        self.assertNotEqual(0, push_gate.returncode, "An unaccepted task must remain blocked")
        self.assertNotIn("validator error", push_gate.stderr, "Gate must execute the validator in a path with spaces")
        self.write(".vemo/judge.jsonl", "evidence\n")
        self.write(".vemo/run/task.log", "proof\n")
        service.uninstall(str(self.root))
        for path, contents in original.items():
            self.assertEqual(contents, (self.root / path).read_bytes(), path)
        self.assertTrue((self.root / "tasks/T-probe.md").exists())
        self.assertEqual("proof\n", (self.root / ".vemo/run/task.log").read_text())
        self.assertFalse((self.root / "bin/vemo").exists())

    def test_conflicts_fail_before_writing(self):
        self.write(".git/hooks/pre-commit", "#!/bin/sh\necho custom\n")
        before = self.snapshot()
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.assertIn(".git/hooks/pre-commit", plan["conflicts"])
        with self.assertRaises(service.SetupError):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_stale_preview_refuses_apply(self):
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.write("AGENTS.md", "changed after preview")
        with self.assertRaisesRegex(service.SetupError, "预览后"):
            service.apply_install(ROOT, str(self.root), "docs", plan_id=plan["plan_id"])
        self.assertFalse((self.root / "bin/vemo").exists())

    def test_verification_failure_rolls_back(self):
        self.write("AGENTS.md", "original\n")
        before = self.snapshot()
        with mock.patch.object(service, "check_install", side_effect=service.SetupError("probe failed")):
            with self.assertRaisesRegex(service.SetupError, "probe failed"):
                self.install()
        self.assertEqual(before, self.snapshot())

    def test_diagnostics_do_not_import_unowned_project_modules(self):
        marker = self.root / "unexpected-project-code"
        poison = f"open({str(marker)!r}, 'w').write('executed')\nraise RuntimeError('unowned import')\n"
        paths = ("sitecustomize.py", "bin/subprocess.py", "bin/argparse.py",
                 "enforcement/validators/subprocess.py", "bin/vemo_composition/re.py")
        for relative in paths:
            self.write(relative, poison)
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.assertTrue(plan["ready"])
        self.assertFalse(marker.exists(), "Environment preview must ignore project sitecustomize")
        self.assertTrue(self.install()["verification"]["ready"])
        self.assertTrue(service.check_install(str(self.root))["ready"])
        self.assertFalse(marker.exists(), "Diagnostics must import only verified runtime and stdlib")
        service.uninstall(str(self.root))
        for relative in paths:
            self.assertEqual(poison, (self.root / relative).read_text())

    def test_modified_install_blocks_uninstall_and_execution(self):
        self.install()
        self.write("bin/vemo", "raise RuntimeError('must not execute')")
        plan = service.plan_uninstall(str(self.root))
        self.assertFalse(plan["ready"])
        with self.assertRaises(service.SetupError):
            service.uninstall(str(self.root))
        with self.assertRaisesRegex(service.SetupError, "未执行诊断"):
            service.check_install(str(self.root))
        self.assertTrue((self.root / "enforcement/hooks/run.py").is_file())

    def test_missing_or_bad_manifest_does_not_execute_unknown_project(self):
        self.write("bin/vemo", "raise RuntimeError('unknown')")
        with self.assertRaisesRegex(service.SetupError, "没有 setup 安装记录"):
            service.check_install(str(self.root))
        self.write(service.MANIFEST, "[]")
        with self.assertRaises(service.SetupError):
            service.read_manifest(self.root)

    def test_malformed_settings_are_not_overwritten(self):
        self.write(".claude/settings.json", "{invalid}")
        with self.assertRaisesRegex(service.SetupError, "JSON"):
            self.install()
        self.assertEqual("{invalid}", (self.root / ".claude/settings.json").read_text())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_and_dangling_parent_refused(self):
        for name in ("bin", ".vemo", ".claude"):
            with self.subTest(name=name):
                link = self.root / name
                link.symlink_to(Path(self.temp.name) / "does-not-exist", target_is_directory=True)
                with self.assertRaises(service.SetupError):
                    service.plan_install(ROOT, str(self.root))
                link.unlink()

    def test_recovery_restores_journal_and_preserves_newer_changes(self):
        self.write("AGENTS.md", "new")
        before = {"data": "b2xk", "mode": 0o644}
        journal = {"schema_version": 1, "files": {"AGENTS.md": {"before": before, "after_hash": service.digest(b"new")}}}
        self.write(service.JOURNAL, json.dumps(journal))
        with self.assertRaisesRegex(service.SetupError, "未完成安装"):
            service.plan_install(ROOT, str(self.root))
        service.recover(str(self.root))
        self.assertEqual("old", (self.root / "AGENTS.md").read_text())
        self.write("AGENTS.md", "later")
        self.write(service.JOURNAL, json.dumps(journal))
        with self.assertRaisesRegex(service.SetupError, "后续修改"):
            service.recover(str(self.root))
        self.assertEqual("later", (self.root / "AGENTS.md").read_text())
        self.assertTrue((self.root / service.JOURNAL).exists())

    def test_cli_preview_and_missing_target_exit_codes(self):
        result = service.run([sys.executable, str(ROOT / "bin/vemo"), "setup", "install", str(self.root), "--preset", "docs", "--json"], ROOT)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ready"])
        result = service.run([sys.executable, str(ROOT / "bin/vemo"), "setup", "install", "relative"], ROOT)
        self.assertEqual(2, result.returncode)

    def test_upgrade_updates_pristine_payload_but_keeps_original_backup(self):
        self.write("AGENTS.md", "original policy\n")
        self.install()
        source = Path(self.temp.name) / "new-source"
        source.mkdir()
        for relative, file in managed_sources(ROOT).items():
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        with (source / "bin/vemo_extensions.py").open("a") as stream:
            stream.write("\n# upgrade fixture\n")
        plan = service.plan_install(source, str(self.root), "docs")
        self.assertTrue(plan["ready"])
        self.assertEqual("update", next(row["status"] for row in plan["actions"] if row["path"] == "bin/vemo_extensions.py"))
        service.apply_install(source, str(self.root), "docs", plan_id=plan["plan_id"])
        self.assertIn("upgrade fixture", (self.root / "bin/vemo_extensions.py").read_text())
        service.uninstall(str(self.root))
        self.assertEqual("original policy\n", (self.root / "AGENTS.md").read_text())

    def test_recovery_rejects_non_payload_before_restoring_any_file(self):
        self.write("AGENTS.md", "new")
        row = {"before": None, "after_hash": service.digest(b"new")}
        self.write(service.JOURNAL, json.dumps({"schema_version": 1, "files": {"AGENTS.md": row, ".git/config": row}}))
        with self.assertRaisesRegex(service.SetupError, "非安装路径"):
            service.recover(str(self.root))
        self.assertEqual("new", (self.root / "AGENTS.md").read_text())

    def test_preexisting_matching_hook_gains_executable_permission(self):
        if os.name == "nt":
            self.skipTest("POSIX executable bit")
        self.write(".git/hooks/pre-commit", (ROOT / "enforcement/ci/pre-commit").read_text())
        hook = self.root / ".git/hooks/pre-commit"
        hook.chmod(0o644)
        self.install()
        self.assertTrue(os.access(hook, os.X_OK))
        service.uninstall(str(self.root))
        self.assertEqual(0o644, hook.stat().st_mode & 0o777)

    def test_uninstall_preserves_an_edit_arriving_after_preflight(self):
        self.install()
        original_write = service.write_file

        def write_then_edit(path, data, mode=0o644):
            original_write(path, data, mode)
            if path == self.root / service.JOURNAL:
                self.write("bin/vemo", "new work after preflight\n")

        with mock.patch.object(service, "write_file", side_effect=write_then_edit):
            with self.assertRaises(service.SetupError):
                service.uninstall(str(self.root))
        self.assertEqual("new work after preflight\n", (self.root / "bin/vemo").read_text())
        self.assertTrue((self.root / service.MANIFEST).exists())
        self.assertTrue((self.root / ".git/hooks/pre-commit").exists())

    def test_diagnostics_reject_missing_bindings_and_ci(self):
        self.install()
        for relative in (".claude/settings.json", ".github/workflows/vemo-ci.yml"):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.unlink()
                self.assertFalse(service.check_install(str(self.root))["ready"])
                path.write_bytes(original)
        path = self.root / ".claude/settings.json"
        settings = json.loads(path.read_text())
        del settings["hooks"]["SessionStart"]
        path.write_text(json.dumps(settings))
        self.assertFalse(service.check_install(str(self.root))["ready"])

    def test_diagnostics_reject_incomplete_manifest_before_executing_runtime(self):
        self.install()
        path = self.root / service.MANIFEST
        manifest = json.loads(path.read_text())
        del manifest["files"]["bin/vemo"]
        path.write_text(json.dumps(manifest))
        with mock.patch.object(service, "run", wraps=service.run) as run:
            with self.assertRaisesRegex(service.SetupError, "缺少运行文件记录"):
                service.check_install(str(self.root))
            self.assertFalse(any("bin/vemo" in call.args[0] for call in run.call_args_list))
        # An older manifest is not a damaged one: upgrade and uninstall stay available so the
        # inventory can be completed by a reviewed reinstall from a full checkout.
        self.assertTrue(service.plan_uninstall(str(self.root))["ready"])
        plan = service.plan_install(ROOT, str(self.root), "docs")
        self.assertTrue(plan["ready"])
        service.apply_install(ROOT, str(self.root), "docs", plan_id=plan["plan_id"])
        self.assertTrue(service.check_install(str(self.root))["ready"])

    def test_recovery_validates_all_fields_before_restoring_files(self):
        self.write("AGENTS.md", "new")
        self.write("CLAUDE.md", "new")
        self.write(service.JOURNAL, json.dumps({"schema_version": 1, "files": {
            "AGENTS.md": {"before": None},
            "CLAUDE.md": {"before": None, "after_hash": service.digest(b"new")},
        }}))
        with self.assertRaises(service.SetupError):
            service.recover(str(self.root))
        self.assertEqual("new", (self.root / "CLAUDE.md").read_text())

    def test_environment_requires_the_python_command_used_by_hooks(self):
        original_run = service.run

        def without_hook_python(args, root, **kwargs):
            if args[0] == "bash" and "python3" in args[-1]:
                return subprocess.CompletedProcess(args, 127, stdout="", stderr="python3: not found")
            return original_run(args, root, **kwargs)

        with mock.patch.object(service, "run", side_effect=without_hook_python):
            self.assertTrue(any(not row["ok"] for row in service._environment(self.root)))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = SetupServer(ROOT)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, method="GET", body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def test_local_page_and_asset_allowlist(self):
        code, body, headers = self.request("/")
        self.assertEqual(200, code)
        self.assertIn("项目安装向导".encode(), body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(404, self.request("/../vemo.config.yaml")[0])
        self.assertEqual(404, self.request("/.vemo/install.json")[0])

    def test_api_requires_token_host_and_origin(self):
        self.assertEqual(403, self.request("/api/info")[0])
        headers = {"X-Vemo-Token": self.server.token}
        self.assertEqual(200, self.request("/api/info", headers=headers)[0])
        self.assertEqual(403, self.request("/api/info", headers={**headers, "Host": "evil.test"})[0])
        self.assertEqual(403, self.request("/api/info", headers={**headers, "Origin": "https://evil.test"})[0])

    def test_mutation_requires_preview_and_valid_json(self):
        headers = {"X-Vemo-Token": self.server.token, "Content-Type": "application/json"}
        self.assertEqual(400, self.request("/api/install", "POST", "{}", headers)[0])
        self.assertEqual(400, self.request("/api/preview", "POST", "[]", headers)[0])
        self.assertEqual(400, self.request("/api/preview", "POST", "{" + " " * 16384, headers)[0])


if __name__ == "__main__":
    unittest.main()
