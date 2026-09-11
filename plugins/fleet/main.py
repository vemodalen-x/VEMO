#!/usr/bin/env python3
"""Local VEMO control plane for governing a fleet of Git projects."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from uuid import uuid4

BIN_DIR = str(Path(__file__).resolve().parent)
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)
SETUP_DIR = str(Path(__file__).resolve().parents[1] / "setup")
if SETUP_DIR not in sys.path:
    sys.path.insert(0, SETUP_DIR)
from vemo_setup.payload import managed_sources


SCHEMA_VERSION = 1
DEFAULT_PROFILE = "solo"
ZERO_HASH = "0" * 64
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".venv", "venv", "node_modules",
    "dist", "build", "target", "__pycache__", "AppData", "$Recycle.Bin",
}


class FleetError(Exception):
    """A user-actionable fleet operation failure."""


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_path(value):
    return str(Path(value).expanduser().resolve())


def stable_project_id(path):
    normalized = os.path.normcase(canonical_path(path)).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:16]


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise FleetError(f"cannot read {path}: {exc}") from exc


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class FleetStore:
    """Persist a private local registry and a hash-chained mutation log."""

    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("VEMO_HOME") or Path.home() / ".vemo").expanduser().resolve()
        self.registry_path = self.home / "fleet.json"
        self.audit_path = self.home / "fleet-audit.jsonl"

    def load(self):
        data = _read_json(self.registry_path, {"schema_version": SCHEMA_VERSION, "projects": []})
        if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("projects"), list):
            raise FleetError(f"unsupported or invalid fleet registry: {self.registry_path}")
        return data

    @contextmanager
    def lock(self, name, timeout=10.0, stale_after=300.0):
        """Serialize cross-process mutations with a crash-recoverable local lock file."""
        self.home.mkdir(parents=True, exist_ok=True)
        lock_path = self.home / (name + ".lock")
        deadline = time.monotonic() + timeout
        descriptor = None
        while descriptor is None:
            try:
                descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(descriptor, f"pid={os.getpid()} created={utc_now()}\n".encode("utf-8"))
            except FileExistsError:
                try:
                    if time.time() - lock_path.stat().st_mtime > stale_after:
                        lock_path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise FleetError(f"timed out waiting for local fleet lock: {lock_path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def save(self, data):
        data["schema_version"] = SCHEMA_VERSION
        data["projects"] = sorted(data["projects"], key=lambda item: os.path.normcase(item["path"]))
        _atomic_json(self.registry_path, data)

    def find(self, value, data=None):
        data = data or self.load()
        candidate = canonical_path(value)
        for item in data["projects"]:
            if item["id"] == value or os.path.normcase(item["path"]) == os.path.normcase(candidate):
                return item
        return None

    def register(self, path, profile, source="manual", managed_files=None):
        root = canonical_path(path)
        if not os.path.exists(os.path.join(root, ".git")):
            raise FleetError(f"not a Git project: {root}")
        with self.lock("fleet-registry"):
            data = self.load()
            project = self.find(root, data)
            now = utc_now()
            created = project is None
            if created:
                project = {
                    "id": stable_project_id(root),
                    "name": os.path.basename(root) or root,
                    "path": root,
                    "registered_at": now,
                    "framework": {"managed_files": {}, "managed_version": None},
                }
                data["projects"].append(project)
            project["profile"] = profile
            project["source"] = source
            project["updated_at"] = now
            if managed_files is not None:
                project["framework"] = {
                    "managed_files": dict(sorted(managed_files.items())),
                    "managed_version": _framework_version(root),
                }
            self.save(data)
        self.audit("fleet.project.registered" if created else "fleet.project.updated", project["id"], profile)
        return project, created

    def unregister(self, value):
        with self.lock("fleet-registry"):
            data = self.load()
            project = self.find(value, data)
            if not project:
                raise FleetError(f"project is not registered: {value}")
            data["projects"] = [item for item in data["projects"] if item["id"] != project["id"]]
            self.save(data)
        self.audit("fleet.project.unregistered", project["id"], project.get("profile"))
        return project

    def audit(self, event_name, project_id=None, profile=None, outcome="success", details=None):
        with self.lock("fleet-audit"):
            previous = ZERO_HASH
            if self.audit_path.exists():
                try:
                    last = self.audit_path.read_text(encoding="utf-8").splitlines()[-1]
                    previous = json.loads(last).get("event_hash", ZERO_HASH)
                except (IndexError, OSError, ValueError):
                    previous = ZERO_HASH
            event = {
                "schema_version": SCHEMA_VERSION,
                "event_id": str(uuid4()),
                "timestamp": utc_now(),
                "event_name": event_name,
                "event_domain": "vemo.fleet",
                "outcome": outcome,
                "actor_type": "local_user",
                "project_id": project_id,
                "profile": profile,
                "previous_hash": previous,
            }
            if details:
                event["details"] = details
            canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            event["event_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            if os.name != "nt":
                os.chmod(self.audit_path, 0o600)
        return event

    def audit_repair_plan(self):
        valid, failed_line = self.verify_audit()
        content = self.audit_path.read_bytes() if self.audit_path.exists() else b""
        return {
            "valid": valid,
            "failed_line": None if valid else failed_line,
            "current_sha256": hashlib.sha256(content).hexdigest(),
            "action": "none" if valid else "archive-and-restart",
        }

    def repair_audit(self):
        plan = self.audit_repair_plan()
        if plan["valid"]:
            return {**plan, "archive": None}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = self.home / f"fleet-audit.invalid-{stamp}.jsonl"
        with self.lock("fleet-audit"):
            if not self.audit_path.exists():
                raise FleetError("audit log disappeared before recovery")
            os.replace(self.audit_path, archive)
        self.audit(
            "fleet.audit.recovered",
            details={
                "archived_file": archive.name,
                "archived_sha256": plan["current_sha256"],
                "failed_line": plan["failed_line"],
            },
        )
        return {**plan, "archive": str(archive)}

    def audit_events(self, limit=None):
        if not self.audit_path.exists():
            return []
        events = []
        for line_number, line in enumerate(self.audit_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                events.append(json.loads(line))
            except ValueError as exc:
                raise FleetError(f"invalid audit JSON at line {line_number}: {exc}") from exc
        return events[-limit:] if limit else events

    def verify_audit(self):
        previous = ZERO_HASH
        events = self.audit_events()
        for index, event in enumerate(events, 1):
            recorded = event.get("event_hash")
            body = dict(event)
            body.pop("event_hash", None)
            actual = hashlib.sha256(json.dumps(
                body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")).hexdigest()
            if event.get("previous_hash") != previous or recorded != actual:
                return False, index
            previous = recorded
        return True, len(events)


def load_profiles(source_root):
    profiles = {}
    directory = Path(source_root) / "plugins" / "setup" / "profiles"
    for path in sorted(directory.glob("*.json")):
        profile = _read_json(path, {})
        required = {"schema_version", "id", "display_name", "maturity", "description",
                    "required_checks", "recommended_checks", "manual_controls", "standards"}
        if profile.get("schema_version") != SCHEMA_VERSION or not required.issubset(profile):
            raise FleetError(f"invalid governance profile: {path}")
        if profile["id"] != path.stem or profile["id"] in profiles:
            raise FleetError(f"profile id/path mismatch: {path}")
        profiles[profile["id"]] = profile
    if DEFAULT_PROFILE not in profiles:
        raise FleetError(f"missing default profile '{DEFAULT_PROFILE}' in {directory}")
    return profiles


def discover_projects(roots, max_depth=5):
    """Return canonical Git roots without mutating targets or the fleet registry."""
    found = set()
    for supplied in roots:
        start = Path(supplied).expanduser().resolve()
        if not start.is_dir():
            continue
        start_depth = len(start.parts)
        for current, dirs, _files in os.walk(start):
            here = Path(current)
            depth = len(here.parts) - start_depth
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith(".")]
            if (here / ".git").exists():
                found.add(str(here.resolve()))
            elif depth >= max_depth:
                dirs[:] = []
    return sorted(found, key=os.path.normcase)


def _exists_any(root, paths):
    return any((Path(root) / item).exists() for item in paths)


def _contains(root, relative, needle):
    try:
        return needle.lower() in (Path(root) / relative).read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def _tracked(root, relative):
    process = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return process.returncode == 0


def _framework_version(root):
    path = Path(root) / "vemo.config.yaml"
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "version:" in line:
                value = line.split("version:", 1)[1].split("#", 1)[0].strip()
                return value.strip("'\"")
    except OSError:
        pass
    return None


def _release_provenance(root):
    workflows = Path(root) / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    for path in list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")):
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "attest-build-provenance" in text or "artifact attestation" in text:
            return True
    return False


CHECKS = {
    "git_repository": ("Git repository", lambda root: (Path(root) / ".git").exists(), "Initialize Git first."),
    "vemo_config": ("VEMO configuration", lambda root: (Path(root) / "vemo.config.yaml").is_file(), "Run `vemo fleet onboard <path>` and review the plan."),
    "agents_router": ("Agent entry router", lambda root: (Path(root) / "AGENTS.md").is_file(), "Add the thin AGENTS.md router."),
    "task_template": ("Machine-readable task template", lambda root: (Path(root) / "tasks" / "_TASK_TEMPLATE.md").is_file(), "Install the VEMO task template."),
    "scope_guard": ("Scope guard", lambda root: (Path(root) / "enforcement" / "hooks" / "run.py").is_file() and (Path(root) / "enforcement" / "validators" / "task_state.py").is_file(), "Install VEMO enforcement files."),
    "secret_scan": ("Secret scanning gate", lambda root: _contains(root, "enforcement/validators/task_state.py", "secret"), "Install a VEMO release with the secret diff gate."),
    "local_hooks": ("Local Git gates", lambda root: (Path(root) / ".git" / "hooks" / "pre-commit").is_file() and (Path(root) / ".git" / "hooks" / "pre-push").is_file(), "Run the project's `vemo init --preset <stack>`."),
    "ci_workflow": ("Authoritative CI gate", lambda root: (Path(root) / ".github" / "workflows" / "vemo-ci.yml").is_file(), "Install the VEMO workflow and require its check on the protected branch."),
    "security_policy": ("Security policy", lambda root: _exists_any(root, ("SECURITY.md", ".github/SECURITY.md")), "Add a vulnerability reporting policy appropriate to the product."),
    "contributing_policy": ("Contribution policy", lambda root: (Path(root) / "CONTRIBUTING.md").is_file(), "Document review, test, and release expectations."),
    "codeowners": ("Critical-path ownership", lambda root: _exists_any(root, ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")), "Assign owners for governance and release paths."),
    "dependency_updates": ("Dependency update automation", lambda root: _exists_any(root, (".github/dependabot.yml", ".github/dependabot.yaml")), "Configure dependency update automation or document an equivalent control."),
    "judge_provenance": ("Judge provenance", lambda root: (Path(root) / ".vemo" / "judge.jsonl").is_file() and _tracked(root, ".vemo/judge.jsonl"), "Track the append-only judge provenance log."),
    "evidence_receipt": ("Executed verification receipt", lambda root: (Path(root) / ".vemo" / "run" / "receipt.json").is_file(), "Run `vemo verify` for the active task."),
    "audit_telemetry": ("Local governance telemetry", lambda root: (Path(root) / ".vemo" / "telemetry.jsonl").is_file(), "Run `vemo init` and confirm telemetry is created."),
    "release_provenance": ("Release artifact provenance", _release_provenance, "Generate and verify artifact attestations in the release workflow."),
}


def assess_project(path, profile):
    root = canonical_path(path)
    results = []
    required = set(profile["required_checks"])
    recommended = set(profile["recommended_checks"])
    unknown = (required | recommended) - set(CHECKS)
    if unknown:
        raise FleetError(f"profile {profile['id']} uses unknown checks: {', '.join(sorted(unknown))}")
    for check_id in profile["required_checks"] + profile["recommended_checks"]:
        title, detector, remediation = CHECKS[check_id]
        try:
            passed = bool(detector(root))
        except (OSError, subprocess.SubprocessError):
            passed = False
        results.append({
            "id": check_id,
            "title": title,
            "level": "required" if check_id in required else "recommended",
            "status": "pass" if passed else "fail",
            "remediation": None if passed else remediation,
        })
    required_rows = [row for row in results if row["level"] == "required"]
    passed_required = sum(row["status"] == "pass" for row in required_rows)
    score = round(100 * passed_required / len(required_rows)) if required_rows else 100
    return {
        "id": stable_project_id(root),
        "name": os.path.basename(root) or root,
        "path": root,
        "profile": profile["id"],
        "maturity": profile["maturity"],
        "framework_version": _framework_version(root),
        "ready": passed_required == len(required_rows),
        "score": score,
        "checks": results,
        "manual_controls": profile["manual_controls"],
    }


def _managed_sources(source_root, skills_root=None):
    """Share the portable payload catalog with setup; add explicitly selected skills. @codex-comment"""
    root = Path(source_root).resolve()
    files = managed_sources(root)
    if skills_root:
        skills_home = Path(skills_root).expanduser().resolve()
        skills_dir = skills_home / "skills"
        if not skills_dir.is_dir():
            raise FleetError(f"not a VEMO_SKILLS home: {skills_home}")
        names = set()
        for skill_dir in sorted(skills_dir.glob("*/*")):
            if not (skill_dir / "SKILL.md").is_file():
                continue
            name = skill_dir.name
            if name in names:
                raise FleetError(f"duplicate skill name across categories: {name}")
            names.add(name)
            for path in sorted(skill_dir.rglob("*")):
                if (not path.is_file() or "__pycache__" in path.parts
                        or path.suffix in {".pyc", ".pyo"} or path.name == ".skill-validated.json"):
                    continue
                suffix = path.relative_to(skill_dir)
                relative = str(Path(".claude") / "skills" / name / suffix).replace("\\", "/")
                files[relative] = path
    return files


def onboard_plan(source_root, target, registered=None, skills_root=None):
    target = Path(target).expanduser().resolve()
    if not (target / ".git").exists():
        raise FleetError(f"not a Git project: {target}")
    baseline = ((registered or {}).get("framework") or {}).get("managed_files") or {}
    actions = []
    for relative, source in _managed_sources(source_root, skills_root).items():
        destination = target / Path(relative)
        source_digest = file_hash(source)
        if not destination.exists():
            status = "create"
        elif not destination.is_file():
            status = "conflict"
        else:
            current = file_hash(destination)
            if current == source_digest:
                status = "unchanged"
            elif baseline.get(relative) == current:
                status = "update"
            else:
                status = "conflict"
        actions.append({
            "path": relative,
            "status": status,
            "source_hash": source_digest,
            "source": str(source),
            "destination": str(destination),
        })
    return actions


def _git_dirty(path):
    process = subprocess.run(
        ["git", "status", "--porcelain"], cwd=path, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if process.returncode != 0:
        raise FleetError(f"cannot inspect Git status: {path}")
    return bool(process.stdout.strip())


def apply_onboard(source_root, target, profile, store, skills_root=None):
    root = canonical_path(target)
    with store.lock("project-" + stable_project_id(root)):
        return _apply_onboard_locked(source_root, root, profile, store, skills_root)


def _apply_onboard_locked(source_root, root, profile, store, skills_root=None):
    registered = store.find(root)
    plan = onboard_plan(source_root, root, registered, skills_root)
    conflicts = [row["path"] for row in plan if row["status"] == "conflict"]
    if conflicts:
        raise FleetError("onboarding blocked by project-owned files: " + ", ".join(conflicts[:8]))
    if _git_dirty(root):
        raise FleetError("onboarding blocked: target worktree is dirty; commit or stash its changes first")
    for row in plan:
        if row["status"] not in {"create", "update"}:
            continue
        destination = Path(row["destination"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row["source"], destination)
    managed = {
        row["path"]: file_hash(row["destination"])
        for row in plan if Path(row["destination"]).is_file()
    }
    project, _created = store.register(root, profile, source="onboard", managed_files=managed)
    store.audit("fleet.project.onboarded", project["id"], profile)
    return plan, project


def launcher_plan(source_root, home=None):
    store = FleetStore(home)
    bin_dir = store.home / "bin"
    python = canonical_path(sys.executable or "python")
    script = canonical_path(Path(source_root) / "bin" / "vemo")
    cmd = f'@echo off\r\n"{python}" "{script}" %*\r\n'
    shell = "#!/usr/bin/env sh\nexec " + shlex.quote(python) + " " + shlex.quote(script) + ' "$@"\n'
    config = {
        "schema_version": SCHEMA_VERSION,
        "source_root": canonical_path(source_root),
        "python": python,
        "installed_at": utc_now(),
    }
    return {
        "bin_dir": str(bin_dir),
        "files": {
            str(bin_dir / "vemo.cmd"): cmd,
            str(bin_dir / "vemo"): shell,
            str(store.home / "config.json"): json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        },
    }


def apply_launcher(source_root, store):
    plan = launcher_plan(source_root, store.home)
    for path, content in plan["files"].items():
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="")
        if destination.name == "vemo" and os.name != "nt":
            os.chmod(destination, 0o700)
    store.audit("fleet.control-plane.installed")
    return plan


def report_payload(assessments):
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "summary": {
            "projects": len(assessments),
            "ready": sum(item["ready"] for item in assessments),
            "not_ready": sum(not item["ready"] for item in assessments),
        },
        "projects": assessments,
    }


def _print_assessment(item):
    marker = "PASS" if item["ready"] else "GAP"
    version = item["framework_version"] or "not-installed"
    print(f"[{marker}] {item['name']}  profile={item['profile']} score={item['score']}% vemo={version}")
    print(f"       {item['path']}")
    for row in item["checks"]:
        if row["status"] == "fail":
            print(f"       - {row['level']}: {row['title']} -> {row['remediation']}")


def build_parser():
    parser = argparse.ArgumentParser(prog="vemo fleet", description="Govern all local Git projects from one PC.")
    parser.add_argument("--source-root", default=str(Path(__file__).resolve().parent.parent), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("register", help="Register one Git project in the private local fleet registry.")
    register.add_argument("path", nargs="?", default=".")
    register.add_argument("--profile", default=DEFAULT_PROFILE)

    unregister = sub.add_parser("unregister", help="Remove a project from the registry; never changes the project.")
    unregister.add_argument("project")

    discover = sub.add_parser("discover", help="Find Git projects without registering or modifying them.")
    discover.add_argument("roots", nargs="*", default=["."])
    discover.add_argument("--max-depth", type=int, default=5)
    discover.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Assess all registered projects against their policy profiles.")
    status.add_argument("--json", action="store_true")
    status.add_argument("--strict", action="store_true", help="Exit 1 when a required control is missing.")

    onboard = sub.add_parser("onboard", help="Preview or apply VEMO-managed files to one clean Git project.")
    onboard.add_argument("path")
    onboard.add_argument("--profile", default=DEFAULT_PROFILE)
    onboard.add_argument("--skills-root", help="Explicit VEMO_SKILLS home to bind byte-identically.")
    onboard.add_argument("--apply", action="store_true", help="Apply the displayed plan; default is read-only.")
    onboard.add_argument("--json", action="store_true")

    install = sub.add_parser("install", help="Preview or install a user-local vemo launcher.")
    install.add_argument("--apply", action="store_true", help="Write launchers under VEMO_HOME; default is preview.")
    install.add_argument("--json", action="store_true")

    profiles = sub.add_parser("profiles", help="List progressive governance profiles and their intent.")
    profiles.add_argument("--json", action="store_true")

    audit = sub.add_parser("audit", help="Read or verify the private hash-chained fleet mutation log.")
    audit.add_argument("--verify", action="store_true")
    audit.add_argument("--repair", action="store_true", help="Preview preservation and restart of an invalid chain.")
    audit.add_argument("--apply", action="store_true", help="Apply audit repair; never deletes the invalid log.")
    audit.add_argument("--limit", type=int, default=20)
    audit.add_argument("--json", action="store_true")
    return parser


def main(argv=None, home=None):
    args = build_parser().parse_args(argv)
    store = FleetStore(home)
    profiles = load_profiles(args.source_root)

    if args.command == "register":
        if args.profile not in profiles:
            raise FleetError(f"unknown profile: {args.profile}")
        project, created = store.register(args.path, args.profile)
        print(f"{'registered' if created else 'updated'} {project['id']} {project['path']} profile={project['profile']}")
        return 0
    if args.command == "unregister":
        project = store.unregister(args.project)
        print(f"unregistered {project['id']} {project['path']} (project files unchanged)")
        return 0
    if args.command == "discover":
        projects = discover_projects(args.roots, args.max_depth)
        payload = {"schema_version": SCHEMA_VERSION, "projects": projects, "mutated": False}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"discovered {len(projects)} Git project(s); no changes made")
            for path in projects:
                marker = "registered" if store.find(path) else "unregistered"
                print(f"  [{marker}] {path}")
        return 0
    if args.command == "status":
        registry = store.load()
        assessments = []
        for project in registry["projects"]:
            profile = profiles.get(project.get("profile"))
            if not profile:
                raise FleetError(f"project {project['id']} uses missing profile {project.get('profile')}")
            assessments.append(assess_project(project["path"], profile))
        payload = report_payload(assessments)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"VEMO Fleet: {payload['summary']['ready']}/{payload['summary']['projects']} project(s) ready")
            for item in assessments:
                _print_assessment(item)
        return 1 if args.strict and payload["summary"]["not_ready"] else 0
    if args.command == "onboard":
        if args.profile not in profiles:
            raise FleetError(f"unknown profile: {args.profile}")
        registered = store.find(args.path)
        plan = onboard_plan(args.source_root, args.path, registered, args.skills_root)
        if args.apply:
            plan, _project = apply_onboard(
                args.source_root, args.path, args.profile, store, args.skills_root
            )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "mode": "apply" if args.apply else "dry-run",
            "target": canonical_path(args.path),
            "profile": args.profile,
            "skills_root": canonical_path(args.skills_root) if args.skills_root else None,
            "summary": {status: sum(row["status"] == status for row in plan)
                        for status in ("create", "update", "unchanged", "conflict")},
            "actions": [{key: row[key] for key in ("path", "status", "source_hash")} for row in plan],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"VEMO onboard {payload['mode']}: {payload['target']} profile={args.profile}")
            for row in plan:
                if row["status"] != "unchanged":
                    print(f"  {row['status']:9} {row['path']}")
            print("summary:", " ".join(f"{key}={value}" for key, value in payload["summary"].items()))
            if not args.apply:
                print("no changes made; re-run with --apply after reviewing conflicts and committing the target")
            else:
                print("managed files applied; run the target project's `vemo init --preset <stack>` to install local hooks")
        return 1 if payload["summary"]["conflict"] else 0
    if args.command == "install":
        plan = apply_launcher(args.source_root, store) if args.apply else launcher_plan(args.source_root, store.home)
        payload = {"schema_version": SCHEMA_VERSION, "mode": "apply" if args.apply else "dry-run", **plan}
        if args.json:
            serializable = dict(payload)
            serializable["files"] = sorted(plan["files"])
            print(json.dumps(serializable, ensure_ascii=False, indent=2))
        else:
            print(f"VEMO fleet install {payload['mode']}")
            for path in sorted(plan["files"]):
                print("  write", path)
            print("launcher directory:", plan["bin_dir"])
            if not args.apply:
                print("no changes made; re-run with --apply")
            else:
                print("add this directory to PATH once, or invoke vemo.cmd directly on Windows")
        return 0
    if args.command == "profiles":
        values = [profiles[key] for key in sorted(profiles, key=lambda key: profiles[key]["maturity"])]
        if args.json:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "profiles": values}, ensure_ascii=False, indent=2))
        else:
            for profile in values:
                print(f"{profile['id']:10} level={profile['maturity']} {profile['display_name']}: {profile['description']}")
        return 0
    if args.command == "audit":
        if args.repair:
            payload = store.repair_audit() if args.apply else store.audit_repair_plan()
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            elif payload["valid"]:
                print("audit chain is already valid; no repair needed")
            elif args.apply:
                print(f"invalid audit preserved at {payload['archive']}; recovery chain started")
            else:
                print(f"audit repair preview: failed_line={payload['failed_line']} sha256={payload['current_sha256']}")
                print("no changes made; re-run with --repair --apply to preserve and restart the chain")
            return 0 if payload["valid"] or args.apply else 1
        if args.verify:
            valid, count = store.verify_audit()
            payload = {"valid": valid, "events_checked": count}
            print(json.dumps(payload, indent=2) if args.json else f"audit chain: {'valid' if valid else 'INVALID'} ({count} event(s))")
            return 0 if valid else 1
        events = store.audit_events(args.limit)
        if args.json:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "events": events}, ensure_ascii=False, indent=2))
        else:
            for event in events:
                print(event["timestamp"], event["event_name"], event.get("project_id") or "-")
        return 0
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FleetError as exc:
        print(f"[vemo fleet] {exc}", file=sys.stderr)
        sys.exit(2)
