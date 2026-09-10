"""Windows runtime portability and native junction regressions."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "bin"))
from vemo_setup import service, windows


class WindowsTests(unittest.TestCase):
    def test_scope_uses_portable_git_paths(self):
        spec = importlib.util.spec_from_file_location("task_state_windows_test", ROOT / "enforcement/validators/task_state.py")
        ts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ts)
        with mock.patch.object(ts.os.path, "relpath", return_value="src\\nested\\app.py"):
            self.assertEqual("src/nested/app.py", ts._rel("app.py"))
            self.assertTrue(ts._match(ts._rel("app.py"), "src/**"))

    @unittest.skipUnless(os.name == "nt", "native Windows junction test")
    def test_directory_junction_is_refused_without_admin_or_pathlib_support(self):
        with tempfile.TemporaryDirectory(prefix="vemo-junction-") as temp:
            root = Path(temp) / "project"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            junction = root / "bin"
            env = dict(os.environ, VEMO_TEST_JUNCTION=str(junction), VEMO_TEST_TARGET=str(outside))
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "New-Item -ItemType Junction -Path $env:VEMO_TEST_JUNCTION -Target $env:VEMO_TEST_TARGET | Out-Null"],
                           check=True, capture_output=True, env=env)
            try:
                self.assertTrue(windows.linked_path(junction))
                with self.assertRaises(service.SetupError):
                    service.safe_path(root, "bin/app.py")
                self.assertEqual([], list(outside.iterdir()))
            finally:
                # Remove only the junction, never recurse through its target.
                os.rmdir(junction)

    @unittest.skipUnless(os.name == "nt", "native Git for Windows")
    def test_git_shell_is_not_the_wsl_system_launcher(self):
        bash = windows.git_bash()
        self.assertNotEqual(Path(os.environ["SystemRoot"]) / "System32/bash.exe", Path(bash))
        result = subprocess.run([bash, "-c", 'test "${BASH_VERSINFO[0]}" -ge 4'], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
