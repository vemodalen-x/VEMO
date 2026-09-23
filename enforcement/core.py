#!/usr/bin/env python3
"""VEMO minimal governance kernel: Policy -> Task -> Gate -> Verify -> Evidence.

This module owns every policy decision. CLI, harness hooks, Git hooks, and CI are adapters only.
It deliberately uses JSON and the Python standard library so the governed repository has one
machine contract and no parser/runtime dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[1]).resolve()
POLICY_FILE = "vemo.json"
TASK_FILE = "vemo.task.json"
EVIDENCE_DIR = ".vemo/evidence"
DECISIONS = {"allow", "deny", "approval_required"}
RESERVED_COMMANDS = {"task", "check", "verify", "status", "init", "plugin"}
CONTROL_PATHS = ("vemo.json", "vemo.task.json", "enforcement/**", ".github/**")

SECRET_RE = re.compile(
    r'(?<![A-Za-z0-9_-])(?:[A-Z][A-Z0-9_-]*(?:API[_-]?KEY|ACCESS[_-]?KEY|PRIVATE[_-]?KEY|SECRET|PASSWORD|TOKEN)'
    r'|api[_-]?key|access[_-]?key|private[_-]?key|secret|password|token)(?![A-Za-z0-9_-])'
    r'["\' ]*[:=]["\' ]*(?!deny/credential_write(?=["\'\s,}\]]|$))'
    r'[A-Za-z0-9/_+\-]{16,}'
    r'|BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY', re.I
)
DESTRUCTIVE = (
    (re.compile(r'(^|[^a-zA-Z])rm\b(?=[^|;&\n]*(?:-[a-zA-Z]*[rR]|--recursive))'
                r'(?=[^|;&\n]*(?:-[a-zA-Z]*f|--force))'), "destructive_fs"),
    (re.compile(r'git\s+reset\s+--hard'), "git_history_rewrite"),
    (re.compile(r'git\s+checkout\s+--\s'), "destructive_fs"),
    (re.compile(r'git\s+clean\s+(?:-[a-zA-Z]*f|[^|;&]*--force)'), "destructive_fs"),
    (re.compile(r'git\s+push\b[^|;&\n]*(?:--force\b|(?<![\w-])-[a-zA-Z]*f)'),
     "git_history_rewrite"),
    (re.compile(r'(^|\s)(sudo|doas)\s'), "destructive_fs"),
    (re.compile(r'curl[^|]*\|\s*(sh|bash)'), "destructive_fs"),
    (re.compile(r'\b(?:shutil\.rmtree|os\.(?:remove|unlink|rmdir|removedirs)|Path\([^)]*\)\.(?:unlink|rmdir))\s*\('),
     "destructive_fs"),
)


class VemoError(Exception):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(path: Path):
    if path.is_symlink():
        raise VemoError(f"linked contract file is not allowed: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise VemoError(f"invalid JSON: {path.name}: {exc}") from exc


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise VemoError("path must be a non-empty repository-relative string")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or ":" in value:
        raise VemoError(f"unsafe relative path: {value}")
    return path.as_posix()


def _normalize_patterns(values, field):
    if not isinstance(values, list) or not all(isinstance(x, str) and x for x in values):
        raise VemoError(f"{field} must be a list of non-empty strings")
    return list(dict.fromkeys(x.replace("\\", "/") for x in values))


def load_policy(root=ROOT):
    value = _json(Path(root) / POLICY_FILE)
    if not isinstance(value, dict) or value.get("version") != 2:
        raise VemoError("vemo.json must be a version-2 object")
    allowed = {"version", "critical_paths", "deny_actions", "verification", "plugins"}
    if set(value) - allowed:
        raise VemoError("unknown vemo.json fields: " + ", ".join(sorted(set(value) - allowed)))
    critical = _normalize_patterns(value.get("critical_paths", []), "critical_paths")
    deny = value.get("deny_actions", [])
    known_actions = {name for _, name in DESTRUCTIVE} | {"credential_write", "out_of_repo_write"}
    if not isinstance(deny, list) or not all(x in known_actions for x in deny):
        raise VemoError("deny_actions contains an unknown action")
    verification = value.get("verification")
    if not isinstance(verification, dict) or set(verification) != {"normal", "critical"}:
        raise VemoError("verification must define exactly normal and critical command lists")
    for name, commands in verification.items():
        if (not isinstance(commands, list) or not commands
                or not all(isinstance(command, list) and command
                           and all(isinstance(arg, str) and arg for arg in command)
                           for command in commands)):
            raise VemoError(f"verification.{name} must be a non-empty list of argv arrays")
    plugins = value.get("plugins", [])
    if not isinstance(plugins, list) or not all(isinstance(x, str) and x for x in plugins):
        raise VemoError("plugins must be a list of names")
    return {**value, "critical_paths": critical, "deny_actions": list(dict.fromkeys(deny)),
            "plugins": list(dict.fromkeys(plugins))}


def _legacy_list(text, key):
    match = re.search(rf"(?m)^{re.escape(key)}:\s*\[(.*)\]\s*$", text)
    if not match:
        return []
    try:
        return json.loads("[" + match.group(1) + "]")
    except ValueError:
        return []


def _legacy_task(root):
    tasks = []
    for path in (Path(root) / "tasks").glob("T-*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        identifier = re.search(r"(?m)^id:\s*(\S+)\s*$", text)
        state = re.search(r"(?m)^state:\s*(\S+)\s*$", text)
        heartbeat = re.search(r"(?m)^heartbeat:\s*(\S+)\s*$", text)
        scope = _legacy_list(text, "scope_in")
        if identifier and scope and state and state.group(1) not in {"Archived", "ProcedureCompleted"}:
            tasks.append((heartbeat.group(1) if heartbeat else "", {
                "version": 1, "id": identifier.group(1), "scope": scope,
                "risk": "critical" if re.search(r"(?m)^risk:\s*R2", text) else "normal",
                "legacy_path": path.relative_to(root).as_posix(),
            }))
    return max(tasks, default=("", None), key=lambda row: row[0])[1]


def load_task(root=ROOT):
    value = _json(Path(root) / TASK_FILE)
    if value is None:
        value = _legacy_task(root)
        if value is None:
            raise VemoError(f"no {TASK_FILE}; run `vemo task create`")
        return value
    if not isinstance(value, dict) or value.get("version") != 1:
        raise VemoError(f"{TASK_FILE} must be a version-1 object")
    allowed = {"version", "id", "scope", "risk"}
    if set(value) - allowed:
        raise VemoError("unknown task fields: " + ", ".join(sorted(set(value) - allowed)))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,80}", str(value.get("id") or "")):
        raise VemoError("task id is invalid")
    scope = _normalize_patterns(value.get("scope", []), "scope")
    risk = value.get("risk", "normal")
    if risk not in {"normal", "critical"}:
        raise VemoError("task risk must be normal or critical")
    return {**value, "scope": scope, "risk": risk}


def _match(path, pattern):
    path = path.replace("\\", "/").lstrip("./")
    pattern = pattern.replace("\\", "/").lstrip("./")
    return fnmatch.fnmatchcase(path, pattern) or (pattern.endswith("/**") and path == pattern[:-3])


def in_scope(path, task):
    return any(_match(path, pattern) for pattern in task["scope"])


def is_critical(paths, task, policy):
    return task.get("risk") == "critical" or any(
        _match(path, pattern) for path in paths for pattern in (*CONTROL_PATHS, *policy["critical_paths"])
    )


def task_digest(task):
    contract = {key: task[key] for key in ("version", "id", "scope", "risk")}
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def approved(task, action=None):
    if (os.environ.get("VEMO_APPROVED_TASK") != task["id"]
            or os.environ.get("VEMO_APPROVED_TASK_DIGEST") != task_digest(task)
            or not os.environ.get("VEMO_APPROVED_BY")):
        return False
    if action is None: return True
    actions = {item.strip() for item in os.environ.get("VEMO_APPROVED_ACTIONS", "").split(",") if item.strip()}
    return action in actions


def decision(effect, reason, **evidence):
    if effect not in DECISIONS:
        raise VemoError(f"invalid decision: {effect}")
    safe = {key: value for key, value in evidence.items()
            if key in {"path", "action", "task", "snapshot", "critical"}}
    return {"version": 1, "decision": effect, "reason": reason, "evidence": safe}


def classify_command(command, root=ROOT):
    for pattern, action in DESTRUCTIVE:
        if pattern.search(command):
            return action
    # A redirect or tee can bypass file-level scope checks, including after `cd`.
    if re.search(r'(?:^|[^<])>>?\s*[^&]|\btee\s+(?:-a\s+)?\S+', command):
        return "out_of_repo_write"
    return None


def check_action(action, path=None, command=None, content=None, root=ROOT):
    try:
        policy, task = load_policy(root), load_task(root)
    except VemoError as exc:
        return decision("deny", "configuration_invalid", action=action, task=str(exc))
    if action == "command":
        classified = classify_command(command or "", root)
        if classified and classified in policy["deny_actions"]:
            if approved(task, classified):
                return decision("allow", "approved_critical_action", action=action,
                                task=task["id"], critical=True)
            return decision("approval_required", classified, action=action, task=task["id"], critical=True)
        return decision("allow", "action_allowed", action=action, task=task["id"])
    if action == "write":
        target = str(path or "")
        try:
            absolute = Path(target).expanduser().resolve() if Path(target).is_absolute() else (Path(root) / target).resolve()
            relative = absolute.relative_to(Path(root).resolve()).as_posix()
        except (OSError, ValueError):
            if "out_of_repo_write" in policy["deny_actions"] and approved(task, "out_of_repo_write"):
                return decision("allow", "approved_critical_action", action=action, path=target,
                                task=task["id"], critical=True)
            return decision("approval_required", "out_of_repo_write", action=action, path=target,
                            task=task["id"], critical=True)
        if not in_scope(relative, task):
            return decision("deny", "scope_violation", action=action, path=relative, task=task["id"])
        if content and SECRET_RE.search(content):
            return decision("deny", "credential_write", action=action, path=relative, task=task["id"])
        critical = is_critical([relative], task, policy)
        if critical and not approved(task):
            return decision("approval_required", "critical_approval_missing", action=action, path=relative,
                            task=task["id"], critical=True)
        return decision("allow", "action_allowed", action=action, path=relative, task=task["id"], critical=critical)
    return decision("deny", "unknown_action", action=action, task=task["id"])


def changed_paths(root=ROOT, diff_range=None):
    args = ["git", "-C", str(root), "diff", "--no-renames", "--name-only", "-z"]
    args.append(diff_range) if diff_range else args.append("--cached")
    result = subprocess.run(args + ["--"], capture_output=True, timeout=30)
    if result.returncode:
        raise VemoError("git diff failed")
    return sorted(raw.decode("utf-8", "surrogateescape").replace("\\", "/")
                  for raw in result.stdout.split(b"\0") if raw)


def unstaged_contract_paths(root=ROOT):
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "--", POLICY_FILE, TASK_FILE],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if result.returncode:
        raise VemoError("git diff failed")
    return sorted(path for path in result.stdout.splitlines() if path)


def snapshot(root=ROOT, diff_range=None, task=None, paths=None):
    task = task or load_task(root)
    paths = paths if paths is not None else changed_paths(root, diff_range)
    current_evidence = evidence_relative(task)
    relevant = [path for path in paths if in_scope(path, task)
                and path not in {TASK_FILE, current_evidence}
                and path != ".vemo/judge.jsonl" and not path.startswith("tasks/")]
    if not relevant:
        return "empty-diff"
    args = ["git", "-C", str(root), "diff", "--no-renames", "--binary"]
    args.append(diff_range) if diff_range else args.append("--cached")
    digest = hashlib.sha256()
    for path in relevant:
        result = subprocess.run(args + ["--", path], capture_output=True, timeout=30)
        if result.returncode:
            raise VemoError("git diff failed")
        digest.update(path.encode("utf-8", "surrogateescape") + b"\0" + result.stdout + b"\0")
    policy = load_policy(root)
    critical = is_critical(paths, task, policy)
    contract = {
        "task": {key: task[key] for key in ("version", "id", "scope", "risk")},
        "policy": {key: policy[key] for key in ("version", "critical_paths", "deny_actions", "verification")},
        "commands": verification_commands(policy, critical),
    }
    digest.update(json.dumps(contract, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8"))
    return digest.hexdigest()


def evidence_path(task, root=ROOT):
    return Path(root) / EVIDENCE_DIR / (task["id"] + ".json")


def evidence_relative(task):
    return f"{EVIDENCE_DIR}/{task['id']}.json"


def verification_commands(policy, critical):
    commands = policy["verification"]["critical" if critical else "normal"]
    return [list(command) for command in dict.fromkeys(tuple(command) for command in commands)]


def verify(root=ROOT, diff_range=None):
    policy, task = load_policy(root), load_task(root)
    paths = changed_paths(root, diff_range)
    critical = is_critical(paths, task, policy)
    preflight = check_merge(root, diff_range, require_evidence=False)
    if preflight["decision"] != "allow":
        raise VemoError("preflight %s: %s" % (preflight["decision"], preflight["reason"]))
    current = snapshot(root, diff_range, task, paths)
    if current == "empty-diff":
        raise VemoError("verification requires a non-empty in-scope diff")
    results = []
    for command in verification_commands(policy, critical):
        completed = subprocess.run(command, cwd=root, shell=False, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
        if completed.stdout: print(completed.stdout, end="")
        results.append({"command": command, "exit": completed.returncode})
        if completed.returncode:
            break
    row = {"version": 1, "task": task["id"], "snapshot": current, "critical": critical,
           "commands": results, "passed": bool(results) and all(x["exit"] == 0 for x in results), "ts": _utc()}
    path = evidence_path(task, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return row


def _diff_text(root=ROOT, diff_range=None, paths=None):
    args = ["git", "-C", str(root), "diff", "--no-renames", "-U0"]
    args.append(diff_range) if diff_range else args.append("--cached")
    result = subprocess.run(args + ["--", *(paths or [])], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=30)
    if result.returncode:
        raise VemoError("git diff failed")
    return result.stdout


def check_merge(root=ROOT, diff_range=None, require_evidence=True):
    try:
        policy, task = load_policy(root), load_task(root)
        paths = changed_paths(root, diff_range)
        drift = unstaged_contract_paths(root)
        if drift:
            return decision("deny", "contract_unstaged", path=drift[0], task=task["id"])
    except VemoError as exc:
        return decision("deny", "configuration_invalid", task=str(exc))
    if not paths:
        return decision("allow", "no_changes", task=task["id"])
    current_evidence = evidence_relative(task)
    outside = next((path for path in paths if path not in {TASK_FILE, ".vemo/judge.jsonl", current_evidence}
                    and not in_scope(path, task)), None)
    if outside:
        return decision("deny", "scope_violation", path=outside, task=task["id"])
    try:
        scanned = [path for path in paths if path not in {".vemo/judge.jsonl", current_evidence}]
        diff = _diff_text(root, diff_range, scanned) if scanned else ""
    except VemoError as exc:
        return decision("deny", "diff_unavailable", task=str(exc))
    if SECRET_RE.search(diff):
        return decision("deny", "credential_write", task=task["id"])
    critical = is_critical(paths, task, policy)
    if critical and not approved(task):
        return decision("approval_required", "critical_approval_missing", task=task["id"], critical=True)
    try:
        current = snapshot(root, diff_range, task, paths)
    except VemoError as exc:
        return decision("deny", "snapshot_unavailable", task=str(exc))
    if require_evidence:
        try:
            evidence = _json(evidence_path(task, root))
        except VemoError:
            evidence = None
        if not isinstance(evidence, dict) or not evidence.get("passed"):
            return decision("deny", "verification_missing", task=task["id"], snapshot=current,
                            critical=critical)
        if evidence.get("task") != task["id"] or evidence.get("snapshot") != current:
            return decision("deny", "verification_stale", task=task["id"], snapshot=current,
                            critical=critical)
        expected = verification_commands(policy, critical)
        observed = [row.get("command") for row in evidence.get("commands", [])]
        if observed != expected or any(row.get("exit") != 0 for row in evidence.get("commands", [])):
            return decision("deny", "verification_incomplete", task=task["id"], snapshot=current,
                            critical=critical)
    return decision("allow", "merge_allowed", task=task["id"], snapshot=current, critical=critical)


def write_task(identifier, scope, risk="normal", root=ROOT):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,80}", str(identifier or "")):
        raise VemoError("task id is invalid")
    if risk not in {"normal", "critical"}:
        raise VemoError("task risk must be normal or critical")
    task = {"version": 1, "id": identifier, "scope": _normalize_patterns(scope, "scope"), "risk": risk}
    path = Path(root) / TASK_FILE
    if path.exists():
        current = _json(path)
        example = _json(Path(root) / "vemo.task.example.json")
        if example is None or current != example:
            raise VemoError(f"{TASK_FILE} already exists; edit its explicit authorization instead of overwriting it")
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return task


def migrate(root=ROOT):
    destination = Path(root) / TASK_FILE
    if (Path(root) / "vemo.config.yaml").exists():
        raise VemoError(
            "legacy vemo.config.yaml requires explicit mapping of critical paths and verification commands "
            "into vemo.json before migration; move the reviewed legacy file to plugins/legacy/ afterward"
        )
    if destination.exists():
        return {"changed": False, "path": TASK_FILE}
    legacy = _legacy_task(root)
    if legacy is None:
        return {"changed": False, "path": None}
    legacy.pop("legacy_path", None)
    destination.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"changed": True, "path": TASK_FILE, "task": legacy["id"]}


def installed_plugins(root=ROOT):
    base = Path(root) / "plugins"
    if not base.is_dir():
        return []
    return sorted(path.parent.name for path in base.glob("*/plugin.json")
                  if re.fullmatch(r"[a-z][a-z0-9-]*", path.parent.name))


def load_plugin(name, root=ROOT):
    if not re.fullmatch(r"[a-z][a-z0-9-]*", str(name or "")):
        raise VemoError(f"invalid plugin name: {name}")
    path = Path(root) / "plugins" / name / "plugin.json"
    value = _json(path)
    if value is None:
        raise VemoError(f"plugin is not installed: {name}")
    if not isinstance(value, dict) or set(value) != {"version", "name", "commands"} or value.get("version") != 1:
        raise VemoError(f"invalid plugin manifest: {path.relative_to(root)}")
    if value.get("name") != name:
        raise VemoError(f"invalid plugin name: {path.relative_to(root)}")
    commands = value.get("commands")
    if not isinstance(commands, dict) or not commands:
        raise VemoError(f"plugin commands must be a non-empty object: {name}")
    normalized = {}
    for command, spec in commands.items():
        if (not re.fullmatch(r"[a-z][a-z0-9-]*", command) or not isinstance(spec, list) or not spec
                or not all(isinstance(item, str) for item in spec)):
            raise VemoError(f"invalid plugin command: {name}:{command}")
        entry = _safe_relative(spec[0])
        target = (Path(root) / entry).resolve()
        try:
            target.relative_to(Path(root).resolve())
        except ValueError as exc:
            raise VemoError(f"plugin entry escapes repository: {name}:{command}") from exc
        if not target.is_file():
            raise VemoError(f"plugin entry missing: {name}:{command}")
        normalized[command] = [entry, *spec[1:]]
    return {"name": name, "commands": normalized, "manifest": path}


def plugin_manifests(root=ROOT):
    manifests = {}
    for name in installed_plugins(root):
        manifests[name] = load_plugin(name, root)
    return manifests


def enabled_plugin_commands(root=ROOT):
    policy = load_policy(root)
    commands = {}
    for name in policy["plugins"]:
        manifest = load_plugin(name, root)
        for command, spec in manifest["commands"].items():
            if command in RESERVED_COMMANDS or command in commands:
                raise VemoError(f"plugin command collision: {command}")
            commands[command] = {"plugin": name, "argv": spec}
    return commands


def set_plugin(name, enabled, root=ROOT):
    policy = load_policy(root)
    load_plugin(name, root)
    plugins = [item for item in policy["plugins"] if item != name]
    if enabled:
        plugins.append(name)
    for plugin_name in plugins:
        load_plugin(plugin_name, root)
    seen = set(RESERVED_COMMANDS)
    for plugin_name in plugins:
        for command in load_plugin(plugin_name, root)["commands"]:
            if command in seen: raise VemoError(f"plugin command collision: {command}")
            seen.add(command)
    policy["plugins"] = plugins
    (Path(root) / POLICY_FILE).write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plugins


def selfcheck(root=ROOT):
    policy = load_policy(root)
    task = load_task(root)
    enabled_plugin_commands(root)
    required = ["AGENTS.md", "VERSION", "vemo.json", "vemo.task.example.json", "bin/vemo",
                "enforcement/core.py", "enforcement/install.sh", "enforcement/hooks/run.py",
                "enforcement/hooks/hooks.json", "enforcement/ci/pre-commit",
                "enforcement/ci/pre-push", "enforcement/ci/vemo-ci.yml", "tests/test_core.py", "eval/run.py"]
    missing = [path for path in required if not (Path(root) / path).is_file()]
    if missing:
        raise VemoError("missing core files: " + ", ".join(missing))
    source, installed = Path(root) / "enforcement/ci/vemo-ci.yml", Path(root) / ".github/workflows/vemo-ci.yml"
    if installed.is_file() and installed.read_bytes() != source.read_bytes():
        raise VemoError("installed CI workflow differs from the canonical adapter")
    hooks = _json(Path(root) / "enforcement/hooks/hooks.json")
    if not isinstance(hooks, dict) or set((hooks.get("hooks") or {})) != {"PreToolUse"}:
        raise VemoError("hook contract must contain only the PreToolUse adapters")
    return {"policy": POLICY_FILE, "task": task["id"], "plugins_installed": installed_plugins(root),
            "plugins_enabled": policy["plugins"], "core_files": required}
