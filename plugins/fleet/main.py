#!/usr/bin/env python3
"""Optional local control plane for multiple VEMO-governed Git projects.

The control plane never executes code from a registered project. It reads contract files,
uses this trusted checkout's evaluator, and invokes Git with fixed argv for observation only.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlparse
import webbrowser


ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = Path(__file__).resolve().parent / "ui"
sys.path.insert(0, str(ROOT / "enforcement"))
import core

SCHEMA_VERSION = 1
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist",
             "build", "target", "__pycache__", ".cache", "AppData", "$Recycle.Bin"}
APPROVAL_ENV = ("VEMO_APPROVED_TASK", "VEMO_APPROVED_TASK_DIGEST", "VEMO_APPROVED_BY",
                "VEMO_APPROVED_ACTIONS")


class FleetError(Exception):
    """A bounded, user-actionable control-plane error."""


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_path(value):
    return str(Path(value).expanduser().resolve())


def project_id(path):
    return hashlib.sha256(os.path.normcase(canonical_path(path)).encode()).hexdigest()[:16]


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class FleetStore:
    """Private user-local registry. Project repositories remain the source of governance truth."""

    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("VEMO_HOME") or Path.home() / ".vemo").expanduser().resolve()
        self.registry = self.home / "projects.json"
        self.audit = self.home / "control-audit.jsonl"

    def load(self):
        try:
            value = json.loads(self.registry.read_text(encoding="utf-8"))
        except FileNotFoundError:
            value = {"schema_version": SCHEMA_VERSION, "projects": []}
        except (OSError, ValueError) as exc:
            raise FleetError(f"cannot read registry {self.registry}: {exc}") from exc
        if (not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION
                or not isinstance(value.get("projects"), list)):
            raise FleetError(f"invalid registry: {self.registry}")
        return value

    def save(self, value):
        value = {"schema_version": SCHEMA_VERSION,
                 "projects": sorted(value["projects"], key=lambda row: os.path.normcase(row["path"]))}
        atomic_json(self.registry, value)

    @contextmanager
    def lock(self, timeout=5.0, stale_after=300.0):
        self.home.mkdir(parents=True, exist_ok=True)
        path = self.home / "control.lock"
        deadline = time.monotonic() + timeout
        descriptor = None
        while descriptor is None:
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(descriptor, f"pid={os.getpid()} ts={utc_now()}\n".encode())
            except FileExistsError:
                try:
                    if time.time() - path.stat().st_mtime > stale_after:
                        path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise FleetError(f"timed out waiting for registry lock: {path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(descriptor)
            path.unlink(missing_ok=True)

    def find(self, value, registry=None):
        if not value:
            return None
        registry = registry or self.load()
        candidate = canonical_path(value)
        for row in registry["projects"]:
            if row.get("id") == value or os.path.normcase(row.get("path", "")) == os.path.normcase(candidate):
                return row
        return None

    def record(self, event, project=None):
        self.home.mkdir(parents=True, exist_ok=True)
        previous = "0" * 64
        try:
            with self.audit.open("rb") as stream:
                lines = [line for line in stream if line.strip()]
            if lines:
                previous = json.loads(lines[-1]).get("hash", previous)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            previous = "invalid"
        row = {"schema_version": 1, "ts": utc_now(), "event": event,
               "project": project, "previous": previous}
        row["hash"] = hashlib.sha256(json.dumps(
            row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        with self.audit.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def register(self, path, label=None):
        root = Path(canonical_path(path))
        if not (root / ".git").exists():
            raise FleetError(f"not a Git repository: {root}")
        with self.lock():
            registry = self.load()
            existing = self.find(str(root), registry)
            now = utc_now()
            if existing:
                existing["label"] = label or existing.get("label") or root.name
                existing["updated_at"] = now
                row, event = existing, "project.updated"
            else:
                row = {"id": project_id(root), "path": str(root), "label": label or root.name,
                       "registered_at": now, "updated_at": now}
                registry["projects"].append(row)
                event = "project.registered"
            self.save(registry)
            self.record(event, row["id"])
        return row

    def unregister(self, value):
        with self.lock():
            registry = self.load()
            row = self.find(value, registry)
            if not row:
                raise FleetError(f"project is not registered: {value}")
            registry["projects"] = [item for item in registry["projects"] if item["id"] != row["id"]]
            self.save(registry)
            self.record("project.unregistered", row["id"])
        return row

    def audit_status(self):
        previous, count = "0" * 64, 0
        try:
            lines = self.audit.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return {"valid": True, "events": 0}
        except OSError:
            return {"valid": False, "events": 0}
        for line in lines:
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
                actual = row.pop("hash")
                expected = hashlib.sha256(json.dumps(
                    row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                if row.get("previous") != previous or actual != expected:
                    return {"valid": False, "events": count}
                previous = actual
            except (ValueError, TypeError, KeyError):
                return {"valid": False, "events": count}
        return {"valid": True, "events": count}


def git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FleetError(f"git observation failed for {root}: {exc}") from exc


def discover_projects(roots, max_depth=5):
    found = set()
    for value in roots:
        root = Path(value).expanduser().resolve()
        if not root.is_dir():
            continue
        base_depth = len(root.parts)
        for directory, names, _files in os.walk(root, followlinks=False):
            path = Path(directory)
            depth = len(path.parts) - base_depth
            names[:] = [name for name in names if name not in SKIP_DIRS and not (path / name).is_symlink()]
            if (path / ".git").exists():
                found.add(str(path))
                if depth:
                    names[:] = []
            elif depth >= max_depth:
                names[:] = []
    return sorted(found, key=os.path.normcase)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def git_state(root):
    result = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames")
    if result.returncode:
        return {"available": False, "staged": 0, "unstaged": 0, "untracked": 0}
    staged = unstaged = untracked = 0
    for item in result.stdout.split("\0"):
        if not item:
            continue
        state = item[:2]
        if state == "??":
            untracked += 1
        else:
            staged += state[0] not in {" ", "?"}
            unstaged += state[1] not in {" ", "?"}
    return {"available": True, "staged": staged, "unstaged": unstaged,
            "untracked": untracked, "clean": not (staged or unstaged or untracked)}


def evidence_rows(root, limit=20):
    directory = Path(root) / core.EVIDENCE_DIR
    paths = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit] \
        if directory.is_dir() else []
    rows = []
    for path in paths:
        value = read_json(path)
        if isinstance(value, dict):
            rows.append({"file": path.name, "task": value.get("task"), "passed": value.get("passed"),
                         "critical": value.get("critical"), "ts": value.get("ts"),
                         "commands": len(value.get("commands", []))})
    return rows


@contextmanager
def without_approval():
    """A monitor reports fail-closed state and never inherits one project's approval."""
    saved = {key: os.environ.pop(key) for key in APPROVAL_ENV if key in os.environ}
    try:
        yield
    finally:
        os.environ.update(saved)


def probe_project(registration, detail=False):
    root = Path(registration["path"])
    result = {"id": registration["id"], "label": registration.get("label") or root.name,
              "path": str(root), "registered_at": registration.get("registered_at"),
              "updated_at": registration.get("updated_at"), "observed_at": utc_now()}
    if not root.is_dir():
        return {**result, "status": "unavailable", "score": 0,
                "gate": {"decision": "deny", "reason": "project_unavailable"},
                "controls": [{"id": "path", "status": "fail", "label": "Project path", "detail": "Directory is missing"}]}
    if not (root / core.POLICY_FILE).is_file():
        return {**result, "status": "unmanaged", "score": 0, "git": git_state(root),
                "gate": {"decision": "deny", "reason": "vemo_not_installed"},
                "controls": [{"id": "policy", "status": "fail", "label": "VEMO policy", "detail": "vemo.json is missing"}]}
    controls, policy, task = [], None, None
    try:
        policy = core.load_policy(root)
        controls.append({"id": "policy", "status": "pass", "label": "Policy", "detail": "Version 2 contract is valid"})
    except core.VemoError as exc:
        controls.append({"id": "policy", "status": "fail", "label": "Policy", "detail": str(exc)})
    try:
        task = core.load_task(root)
        controls.append({"id": "task", "status": "pass", "label": "Task", "detail": task["id"]})
    except core.VemoError as exc:
        controls.append({"id": "task", "status": "fail", "label": "Task", "detail": str(exc)})
    for identifier, label, relative in (
        ("core", "Governance evaluator", "enforcement/core.py"),
        ("cli", "VEMO CLI", "bin/vemo"),
        ("ci", "Server-side workflow", ".github/workflows/vemo-ci.yml"),
        ("pre_commit", "Pre-commit adapter", ".git/hooks/pre-commit"),
        ("pre_push", "Pre-push adapter", ".git/hooks/pre-push"),
    ):
        present = (root / relative).is_file()
        controls.append({"id": identifier, "status": "pass" if present else "fail",
                         "label": label, "detail": relative + (" is present" if present else " is missing")})
    with without_approval():
        gate = core.check_merge(root) if policy and task else {"decision": "deny", "reason": "configuration_invalid", "evidence": {}}
    evidence = evidence_rows(root)
    latest = evidence[0] if evidence else None
    evidence_ok = bool(latest and latest.get("passed") and task and latest.get("task") == task["id"])
    controls.append({"id": "evidence", "status": "pass" if evidence_ok else "warn",
                     "label": "Latest verification evidence",
                     "detail": latest.get("ts") if evidence_ok else "No passing evidence for the current task"})
    required = [row for row in controls if row["status"] == "fail"]
    status = "ready" if not required and gate["decision"] == "allow" else "attention"
    score = round(100 * (sum(row["status"] == "pass" for row in controls)
                         + (gate["decision"] == "allow")) / (len(controls) + 1))
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        version = None
    return {**result, "status": status, "score": score, "version": version,
            "gate": gate, "git": git_state(root), "controls": controls,
            "task": task, "policy": ({"critical_paths": policy["critical_paths"],
                                       "deny_actions": policy["deny_actions"],
                                       "plugins": policy["plugins"],
                                       "verification": {key: len(value) for key, value in policy["verification"].items()}}
                                      if policy else None),
            "evidence": evidence if detail else evidence[:1]}


def overview(store):
    projects = [probe_project(row) for row in store.load()["projects"]]
    counts = {name: sum(row["status"] == name for row in projects)
              for name in ("ready", "attention", "unmanaged", "unavailable")}
    return {"schema_version": SCHEMA_VERSION, "generated_at": utc_now(),
            "summary": {"projects": len(projects), **counts}, "audit": store.audit_status(),
            "projects": projects}


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "VEMOControl/1"

    def log_message(self, _format, *_args):
        return

    def send_content(self, content_type, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        self.send_content("application/json; charset=utf-8", json.dumps(value, ensure_ascii=False).encode(), status)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/overview":
            return self.send_json(overview(self.server.store))
        if parsed.path == "/api/project":
            identifier = parse_qs(parsed.query).get("id", [""])[0]
            row = self.server.store.find(identifier)
            return self.send_json(probe_project(row, detail=True) if row else {"error": "project_not_found"}, 200 if row else 404)
        if parsed.path == "/api/health":
            return self.send_json({"ok": True, "audit": self.server.store.audit_status()})
        relative = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        if relative not in {"index.html", "app.js", "style.css"}:
            return self.send_error(404)
        path = UI_ROOT / relative
        try:
            data = path.read_bytes()
        except OSError:
            return self.send_error(404)
        content_type = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8"}[path.suffix]
        self.send_content(content_type, data)


def serve(store, port=0, open_browser=True):
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    server.store = store
    url = f"http://127.0.0.1:{server.server_port}/"
    print(url, flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def parser():
    value = argparse.ArgumentParser(prog="vemo fleet", description="Local VEMO governance control plane")
    sub = value.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register", help="Register one Git project; project files are unchanged")
    register.add_argument("path")
    register.add_argument("--label")
    unregister = sub.add_parser("unregister", help="Remove only the user-local registry entry")
    unregister.add_argument("project")
    discover = sub.add_parser("discover", help="Find Git repositories below explicit roots without registering")
    discover.add_argument("roots", nargs="+")
    discover.add_argument("--max-depth", type=int, default=5)
    discover.add_argument("--json", action="store_true")
    status = sub.add_parser("status", help="Observe all registered projects without executing project code")
    status.add_argument("--json", action="store_true")
    status.add_argument("--strict", action="store_true")
    inspect = sub.add_parser("inspect", help="Show one registered project's governance state")
    inspect.add_argument("project")
    inspect.add_argument("--json", action="store_true")
    serve_parser = sub.add_parser("serve", help="Start the loopback-only visual monitoring console")
    serve_parser.add_argument("--port", type=int, default=0)
    serve_parser.add_argument("--no-browser", action="store_true")
    sub.add_parser("audit", help="Verify the user-local registry mutation chain")
    return value


def main(argv=None, home=None):
    args = parser().parse_args(argv)
    store = FleetStore(home)
    if args.command == "register":
        print(json.dumps(store.register(args.path, args.label), ensure_ascii=False, indent=2)); return 0
    if args.command == "unregister":
        print(json.dumps(store.unregister(args.project), ensure_ascii=False, indent=2)); return 0
    if args.command == "discover":
        rows = discover_projects(args.roots, args.max_depth)
        payload = {"projects": [{"path": row, "registered": bool(store.find(row))} for row in rows], "mutated": False}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "\n".join(rows)); return 0
    if args.command == "status":
        payload = overview(store)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"VEMO Control Plane: {payload['summary']['ready']}/{payload['summary']['projects']} ready")
            for row in payload["projects"]:
                print(f"{row['status']:11} {row['score']:3}% {row['label']}  {row['gate']['reason']}")
        return 1 if args.strict and payload["summary"]["projects"] != payload["summary"]["ready"] else 0
    if args.command == "inspect":
        row = store.find(args.project)
        if not row:
            raise FleetError(f"project is not registered: {args.project}")
        payload = probe_project(row, detail=True)
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else
              f"{payload['label']}: {payload['status']} {payload['score']}% gate={payload['gate']['reason']}")
        return 0
    if args.command == "serve":
        serve(store, args.port, not args.no_browser); return 0
    if args.command == "audit":
        payload = store.audit_status(); print(json.dumps(payload, indent=2)); return 0 if payload["valid"] else 1
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FleetError as exc:
        print(f"[vemo fleet] {exc}", file=sys.stderr)
        raise SystemExit(2)
