import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":
    ROOT = ROOT.parent
SPEC = importlib.util.spec_from_file_location("vemo_package_check", ROOT / "enforcement/validators/package_check.py")
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class PackageCheckTests(unittest.TestCase):
    def test_source_runtime_inventory_compiles(self):
        self.assertEqual("pass", scanner.check_source(ROOT)["status"])

    def test_archive_rejects_traversal_duplicates_and_missing_runtime(self):
        for entries in (("../escape",), ("same", "same"), ("package.json",)):
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as temp:
                archive = Path(temp) / "broken.zip"
                with zipfile.ZipFile(archive, "w") as stream:
                    for name in entries:
                        stream.writestr(name, json.dumps({"schema_version": 1, "files": {}}))
                with self.assertRaises(ValueError):
                    scanner.check_archive(archive)
