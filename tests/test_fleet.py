import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout


ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":
    ROOT = ROOT.parent
SPEC = importlib.util.spec_from_file_location("vemo_fleet", ROOT / "bin" / "vemo_fleet.py")
fleet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fleet)


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vemo_fleet_test_"))
        self.home = self.temp / "home"

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def git_project(self, name, commit=False):
        project = self.temp / name
        project.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.name", "VEMO Test"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.email", "vemo@example.invalid"], cwd=project, check=True)
        if commit:
            (project / "README.md").write_bytes((ROOT / "README.md").read_bytes())
            subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=project, check=True)
        return project

    def snapshot(self, root):
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }

    def test_profiles_are_ordered_and_reference_known_checks(self):
        profiles = fleet.load_profiles(ROOT)
        self.assertEqual([1, 2, 3], sorted(item["maturity"] for item in profiles.values()))
        for profile in profiles.values():
            configured = set(profile["required_checks"] + profile["recommended_checks"])
            self.assertFalse(configured - set(fleet.CHECKS))

    def test_registry_deduplicates_canonical_project_paths(self):
        project = self.git_project("registered")
        store = fleet.FleetStore(self.home)
        first, created = store.register(project, "solo")
        second, created_again = store.register(project / ".", "team")
        data = store.load()
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual("team", data["projects"][0]["profile"])
        self.assertEqual(1, len(data["projects"]))

    def test_parallel_registrations_do_not_lose_projects(self):
        projects = [self.git_project(f"parallel-{index}") for index in range(8)]
        store = fleet.FleetStore(self.home)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda path: store.register(path, "solo"), projects))
        data = store.load()
        self.assertEqual(8, len(data["projects"]))
        valid, count = store.verify_audit()
        self.assertTrue(valid)
        self.assertEqual(8, count)

    def test_discovery_is_read_only_and_finds_nested_repositories(self):
        parent = self.git_project("parent")
        nested = parent / "components" / "nested"
        nested.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
        before = self.snapshot(parent)
        found = fleet.discover_projects([parent], max_depth=5)
        after = self.snapshot(parent)
        self.assertEqual(before, after)
        self.assertEqual({str(parent.resolve()), str(nested.resolve())}, set(found))
        self.assertFalse((self.home / "fleet.json").exists())

    def test_git_file_is_accepted_for_worktree_style_project(self):
        project = self.temp / "worktree"
        project.mkdir()
        (project / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        found = fleet.discover_projects([project], max_depth=1)
        self.assertEqual([str(project.resolve())], found)

    def test_assessment_returns_deterministic_required_gaps(self):
        project = self.git_project("assessment")
        profile = fleet.load_profiles(ROOT)["solo"]
        result = fleet.assess_project(project, profile)
        failed = {row["id"] for row in result["checks"] if row["status"] == "fail"}
        self.assertFalse(result["ready"])
        self.assertEqual(17, result["score"])
        self.assertIn("vemo_config", failed)
        self.assertIn("secret_scan", failed)

    def test_framework_version_ignores_yaml_line_comment(self):
        project = self.git_project("version-comment")
        (project / "vemo.config.yaml").write_text(
            'vemo:\n  version: "2.4.0"  # product note\n', encoding="utf-8"
        )
        self.assertEqual("2.4.0", fleet._framework_version(project))

    def test_onboard_dry_run_never_changes_target(self):
        project = self.git_project("dry-run")
        before = self.snapshot(project)
        plan = fleet.onboard_plan(ROOT, project)
        self.assertTrue(any(row["status"] == "create" for row in plan))
        self.assertEqual(before, self.snapshot(project))
        self.assertFalse((self.home / "fleet.json").exists())

    def test_onboard_apply_refuses_dirty_target(self):
        project = self.git_project("dirty", commit=True)
        (project / "working.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(fleet.FleetError, "worktree is dirty"):
            fleet.apply_onboard(ROOT, project, "solo", fleet.FleetStore(self.home))
        self.assertFalse((project / "AGENTS.md").exists())

    def test_onboard_apply_refuses_project_owned_conflict(self):
        project = self.git_project("conflict")
        (project / "AGENTS.md").write_text("project policy\n", encoding="utf-8")
        subprocess.run(["git", "add", "AGENTS.md"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "policy"], cwd=project, check=True)
        with self.assertRaisesRegex(fleet.FleetError, "project-owned files"):
            fleet.apply_onboard(ROOT, project, "solo", fleet.FleetStore(self.home))
        self.assertEqual("project policy\n", (project / "AGENTS.md").read_text(encoding="utf-8"))

    def test_onboard_apply_records_managed_hashes(self):
        project = self.git_project("adopt")
        plan, registered = fleet.apply_onboard(ROOT, project, "solo", fleet.FleetStore(self.home))
        self.assertTrue((project / "AGENTS.md").is_file())
        self.assertTrue((project / "bin" / "vemo_fleet.py").is_file())
        self.assertTrue(any(row["status"] == "create" for row in plan))
        self.assertIn("AGENTS.md", registered["framework"]["managed_files"])

    def test_onboard_can_bind_an_explicit_skill_home_byte_identically(self):
        project = self.git_project("skills-adopt")
        skills_home = self.temp / "skills-home"
        source = skills_home / "skills" / "governance" / "governing-example"
        (source / "references").mkdir(parents=True)
        (source / "SKILL.md").write_text("---\nname: governing-example\n---\nbody\n", encoding="utf-8")
        (source / "references" / "policy.md").write_text("policy\n", encoding="utf-8")
        (source / ".skill-validated.json").write_text("{}\n", encoding="utf-8")
        plan, registered = fleet.apply_onboard(
            ROOT, project, "solo", fleet.FleetStore(self.home), skills_home
        )
        destination = project / ".claude" / "skills" / "governing-example"
        self.assertEqual((source / "SKILL.md").read_bytes(), (destination / "SKILL.md").read_bytes())
        self.assertEqual(
            (source / "references" / "policy.md").read_bytes(),
            (destination / "references" / "policy.md").read_bytes(),
        )
        self.assertFalse((destination / ".skill-validated.json").exists())
        self.assertIn(".claude/skills/governing-example/SKILL.md", registered["framework"]["managed_files"])
        self.assertTrue(any(row["path"].startswith(".claude/skills/") for row in plan))

    def test_launcher_is_preview_first_then_installs_under_home(self):
        preview = fleet.launcher_plan(ROOT, self.home)
        self.assertFalse((self.home / "bin" / "vemo.cmd").exists())
        applied = fleet.apply_launcher(ROOT, fleet.FleetStore(self.home))
        self.assertEqual(preview["bin_dir"], applied["bin_dir"])
        self.assertTrue((self.home / "bin" / "vemo.cmd").is_file())
        self.assertTrue((self.home / "config.json").is_file())

    def test_audit_chain_detects_tampering(self):
        project = self.git_project("audited")
        store = fleet.FleetStore(self.home)
        store.register(project, "solo")
        valid, count = store.verify_audit()
        self.assertTrue(valid)
        self.assertEqual(1, count)
        event = json.loads(store.audit_path.read_text(encoding="utf-8"))
        event["profile"] = "regulated"
        store.audit_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        valid, failed_line = store.verify_audit()
        self.assertFalse(valid)
        self.assertEqual(1, failed_line)
        recovered = store.repair_audit()
        self.assertTrue(Path(recovered["archive"]).is_file())
        self.assertEqual(fleet.file_hash(recovered["archive"]), recovered["current_sha256"])
        valid, count = store.verify_audit()
        self.assertTrue(valid)
        self.assertEqual(1, count)
        self.assertEqual("fleet.audit.recovered", store.audit_events()[0]["event_name"])

    def test_cli_status_has_machine_readable_contract(self):
        project = self.git_project("cli")
        store = fleet.FleetStore(self.home)
        store.register(project, "solo")
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = fleet.main(["--source-root", str(ROOT), "status", "--json"], home=self.home)
        payload = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual(1, payload["summary"]["projects"])


if __name__ == "__main__":
    unittest.main()
