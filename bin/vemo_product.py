#!/usr/bin/env python3
"""User-facing product workflows for VEMO.

This layer is intentionally read-mostly. It makes onboarding and recurring value visible without
moving enforcement out of the existing hooks, Git gates, and CI backstop.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[1]).resolve()
SCHEMA_VERSION = 1
PLATFORM_SCHEMA_VERSION = 2
PROFILES = {
    "solo": {
        "name": "Solo Core",
        "summary": "Low-friction local protection for one developer or an experiment.",
    },
    "team": {
        "name": "Team Control",
        "summary": "Shared policy, CI authority, ownership, and review evidence.",
    },
    "regulated": {
        "name": "Regulated Evidence",
        "summary": "Evidence-oriented controls for higher-assurance delivery; not certification.",
    },
}

# Responsibility planes, not directory layers.  The same repository can be deployed under different
# harnesses, but these contracts and their ownership stay stable.  Keep paths relative: `vemo platform`
# is safe to feed to dashboards without disclosing the checkout location.
PLATFORM_PLANES = (
    {
        "id": "ingress",
        "name": "Ingress",
        "responsibility": "Normalize a human or harness request into VEMO's portable entry and adapter contract.",
        "components": (
            {"id": "agent_entry", "path": "AGENTS.md", "kind": "contract", "required": True},
            {"id": "adapter_contract", "path": "docs/ADAPTERS.md", "kind": "contract", "required": False},
        ),
    },
    {
        "id": "control",
        "name": "Control",
        "responsibility": "Orient sessions, classify risk and capability, and drive the task lifecycle.",
        "components": (
            {"id": "cli", "path": "bin/vemo", "kind": "runtime", "required": True},
            {"id": "project_control", "path": "bin/vemo_product.py", "kind": "runtime", "required": True},
            {"id": "fleet_control", "path": "bin/vemo_fleet.py", "kind": "runtime", "required": True},
            {"id": "task_state", "path": "enforcement/validators/task_state.py", "kind": "runtime", "required": True},
        ),
    },
    {
        "id": "policy",
        "name": "Policy",
        "responsibility": "Hold the single source for configuration, safety, and just-in-time lifecycle rules.",
        "components": (
            {"id": "configuration", "path": "vemo.config.yaml", "kind": "policy", "required": True},
            {"id": "spec_manifest", "path": "specs/_manifest.yaml", "kind": "policy", "required": True},
            {"id": "safety_spec", "path": "specs/safety.spec.md", "kind": "policy", "required": True},
        ),
    },
    {
        "id": "execution",
        "name": "Execution",
        "responsibility": "Supply bounded agents, reusable skills, and executable conformance scenarios.",
        "components": (
            {"id": "judge_agent", "path": "agents/governance-judge.md", "kind": "agent", "required": True},
            {"id": "skill_catalog", "path": "skill/_catalog.md", "kind": "skill", "required": False},
            {"id": "conformance_eval", "path": "eval/run.py", "kind": "verification", "required": False},
        ),
    },
    {
        "id": "enforcement",
        "name": "Enforcement",
        "responsibility": "Apply pre-action, Git, and CI gates independently of the worker's claims.",
        "components": (
            {"id": "hook_dispatcher", "path": "enforcement/hooks/run.py", "kind": "guard", "required": True},
            {"id": "pre_commit_source", "path": "enforcement/ci/pre-commit", "kind": "guard", "required": True},
            {"id": "pre_push_source", "path": "enforcement/ci/pre-push", "kind": "guard", "required": True},
            {"id": "ci_source", "path": "enforcement/ci/vemo-ci.yml", "kind": "guard", "required": True},
        ),
    },
    {
        "id": "evidence",
        "name": "Evidence",
        "responsibility": "Persist task memory, receipts, judge provenance, and privacy-minimized telemetry.",
        "components": (
            {
                "id": "task_memory", "path": "tasks", "kind": "evidence", "required": True,
                "materialization": "durable_record",
            },
            {
                "id": "judge_ledger", "path": ".vemo/judge.jsonl", "kind": "evidence", "required": False,
                "materialization": "durable_record",
            },
            {
                "id": "verification_receipt", "path": ".vemo/run/receipt.json",
                "kind": "runtime_evidence", "required": False, "materialization": "runtime_artifact",
            },
            {
                "id": "telemetry", "path": ".vemo/telemetry.jsonl", "kind": "runtime_evidence",
                "required": False, "materialization": "runtime_artifact",
            },
        ),
    },
)

PLATFORM_LIFECYCLE = (
    {"step": 1, "id": "ingest", "plane": "ingress", "outcome": "portable request envelope"},
    {"step": 2, "id": "orient", "plane": "control", "outcome": "session brief and continuity state"},
    {"step": 3, "id": "classify", "plane": "control", "outcome": "task type, risk tier, and capability posture"},
    {"step": 4, "id": "resolve_policy", "plane": "policy", "outcome": "just-in-time rules and allowed scope"},
    {"step": 5, "id": "authorize", "plane": "enforcement", "outcome": "allow or fail-closed block"},
    {"step": 6, "id": "execute", "plane": "execution", "outcome": "bounded work product"},
    {"step": 7, "id": "prove", "plane": "evidence", "outcome": "task state, receipt, telemetry, and judge provenance"},
    {"step": 8, "id": "deliver", "plane": "enforcement", "outcome": "Git and CI delivery decision"},
)


# A seam is useful only when its contract owner, provider, and consumer are visible.  Provider roles may be
# optional when the capability is installable (ring 1); required definition/consumer roles still fail closed.
# These are composition facts, not claims that a hook or verification command executed.
PLATFORM_CAPABILITY_SEAMS = (
    {
        "id": "ring1_guard",
        "name": "Ring-1 guard adapter",
        "owner": "ingress",
        "roles": (
            {
                "id": "definition", "required": True, "minimum": 1,
                "paths": ("enforcement/hooks/hooks.json",),
            },
            {
                "id": "provider", "required": False, "minimum": 1,
                "paths": (".claude/settings.json", ".codex/hooks.json"),
            },
            {
                "id": "consumer", "required": True, "minimum": 1,
                "paths": ("enforcement/hooks/run.py",),
            },
        ),
    },
    {
        "id": "verification_evidence",
        "name": "Executed verification evidence",
        "owner": "evidence",
        "roles": (
            {
                "id": "definition", "required": True, "minimum": 1,
                "paths": ("specs/verify.spec.md",),
            },
            {
                "id": "provider", "required": True, "minimum": 1,
                "paths": ("enforcement/validators/task_state.py",),
            },
            {
                "id": "consumer", "required": True, "minimum": 1,
                "paths": ("enforcement/ci/pre-push", ".github/workflows/vemo-ci.yml"),
            },
        ),
    },
)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _stamp(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp
    except ValueError:
        return None


def _read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _config_value(root, section, key, default=None):
    state, path = _resolve_local_file(root, "vemo.config.yaml")
    if state != "valid":
        return default
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return default
    in_section = False
    section_indent = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_section = line.strip().rstrip(":") == section
            section_indent = indent if in_section else None
            continue
        if not in_section or section_indent is None or indent <= section_indent:
            continue
        match = re.match(r"^\s*" + re.escape(key) + r"\s*:\s*(.*?)\s*(?:#.*)?$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    return default


def _platform_version(root):
    configured = _config_value(root, "vemo", "version")
    if configured:
        return configured
    state, path = _resolve_local_file(root, "VERSION")
    if state != "valid":
        return "unknown"
    try:
        return path.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def _platform_planes(root):
    root = Path(root)
    planes = []
    for plane in PLATFORM_PLANES:
        components = []
        for component in plane["components"]:
            row = dict(component)
            row.setdefault("materialization", "source")
            row["present"] = _local_path_present(root, component["path"])
            components.append(row)
        required = [row for row in components if row["required"]]
        planes.append({
            "id": plane["id"],
            "name": plane["name"],
            "responsibility": plane["responsibility"],
            "status": "ready" if all(row["present"] for row in required) else "incomplete",
            "required_present": sum(1 for row in required if row["present"]),
            "required_total": len(required),
            "components": components,
        })
    return planes


def _platform_seams(root):
    root = Path(root)
    seams = []
    for seam in PLATFORM_CAPABILITY_SEAMS:
        roles = []
        for role in seam["roles"]:
            components = [
                {"path": path, "present": _local_path_present(root, path)}
                for path in role["paths"]
            ]
            present = sum(1 for component in components if component["present"])
            satisfied = present >= role["minimum"]
            roles.append({
                "id": role["id"],
                "required": role["required"],
                "minimum": role["minimum"],
                "present": present,
                "status": "ready" if satisfied else ("missing" if role["required"] else "not_bound"),
                "components": components,
            })
        required_missing = [role["id"] for role in roles if role["required"] and role["status"] != "ready"]
        optional_missing = [role["id"] for role in roles if not role["required"] and role["status"] != "ready"]
        seams.append({
            "id": seam["id"],
            "name": seam["name"],
            "owner": seam["owner"],
            "status": "incomplete" if required_missing else ("available" if optional_missing else "complete"),
            "missing_required_roles": required_missing,
            "roles": roles,
        })
    return seams


def _resolve_local_path(root, relative):
    """Resolve an allowlisted relative path without accepting a link outside the checkout."""
    try:
        root = Path(root).resolve()
        source = root / relative
        if not source.exists() and not source.is_symlink():
            return "missing", None
        resolved = source.resolve()
        resolved.relative_to(root)
    except (OSError, TypeError, ValueError):
        return "unsafe", None
    return ("valid", resolved) if resolved.exists() else ("invalid", None)


def _resolve_local_file(root, relative):
    state, path = _resolve_local_path(root, relative)
    if state != "valid":
        return state, None
    return ("valid", path) if path.is_file() else ("invalid", None)


def _local_path_present(root, relative):
    return _resolve_local_path(root, relative)[0] == "valid"


def _load_local_json(root, relative):
    state, path = _resolve_local_file(root, relative)
    if state != "valid":
        return state, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "invalid", None
    return ("valid", value) if isinstance(value, dict) else ("invalid", None)


def _command_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "command" and isinstance(item, str):
                yield item
            yield from _command_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _command_values(item)


def _hook_bindings(document):
    hooks = document.get("hooks") if isinstance(document, dict) else None
    if not isinstance(hooks, dict):
        return set()
    bindings = set()
    action_pattern = re.compile(
        r"(?:^|[/\\\"'\s])enforcement[/\\]+hooks[/\\]+run\.py[\"']?\s+([a-z][a-z0-9-]*)\b"
    )
    for event, entries in hooks.items():
        for command in _command_values(entries):
            for match in action_pattern.finditer(command):
                bindings.add((str(event), match.group(1)))
    return bindings


def _adapter_binding_invariant(root):
    definition_state, definition = _load_local_json(root, "enforcement/hooks/hooks.json")
    expected = _hook_bindings(definition)
    definition_valid = definition_state == "valid" and bool(expected)
    consumer_present = _resolve_local_file(root, "enforcement/hooks/run.py")[0] == "valid"
    providers = []
    failures = []
    if not definition_valid:
        failures.append("invalid_definition")
    if not consumer_present:
        failures.append("missing_consumer")
    for relative in (".claude/settings.json", ".codex/hooks.json"):
        state, document = _load_local_json(root, relative)
        if state == "missing":
            continue
        bindings = _hook_bindings(document)
        bound = state == "valid" and bool(expected) and expected.issubset(bindings)
        providers.append({
            "path": relative,
            "status": "bound" if bound else "invalid",
            "binding_count": len(bindings),
            "expected_binding_count": len(expected),
        })
        if state in ("unsafe", "invalid"):
            failures.append("invalid_provider")
        elif not bound:
            failures.append("incomplete_provider_binding")
    status = "fail" if failures else ("pass" if providers else "not_observed")
    return {
        "id": "ring1_adapter_binding",
        "owner": "ingress",
        "kind": "configuration_relationship",
        "capability_seam": "ring1_guard",
        "status": status,
        "observed": bool(providers),
        "checks": {
            "definition_valid": definition_valid,
            "consumer_present": consumer_present,
            "providers_observed": len(providers),
            "providers_bound": sum(1 for provider in providers if provider["status"] == "bound"),
        },
        "providers": providers,
        "failure_codes": sorted(set(failures)),
    }


def _safe_runtime_log_reference(value):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        return None
    parts = PurePosixPath(normalized).parts
    if len(parts) < 3 or parts[:2] != (".vemo", "run") or ".." in parts:
        return None
    return "/".join(parts)


def _receipt_chain_invariant(root):
    state, receipt = _load_local_json(root, ".vemo/run/receipt.json")
    if state == "missing":
        return {
            "id": "verification_receipt_chain",
            "owner": "evidence",
            "kind": "durable_relationship",
            "capability_seam": "verification_evidence",
            "status": "not_observed",
            "observed": False,
            "checks": {},
            "failure_codes": [],
        }
    receipt_valid = state == "valid"
    task_id = receipt.get("task") if receipt_valid else None
    task_reference_valid = isinstance(task_id, str) and bool(re.fullmatch(r"T-[A-Za-z0-9][A-Za-z0-9._-]*", task_id))
    task_record_present = False
    if task_reference_valid:
        task_record_present = any(
            _resolve_local_file(root, relative)[0] == "valid"
            for relative in ("tasks/%s.md" % task_id, "tasks/Archive/%s.md" % task_id)
        )
    log_reference = _safe_runtime_log_reference(receipt.get("log") if receipt_valid else None)
    log_reference_safe = log_reference is not None
    log_present = False
    if log_reference_safe:
        log_state, log_path = _resolve_local_file(root, log_reference)
        if log_state == "valid":
            try:
                log_present = log_path.stat().st_size > 0
            except OSError:
                log_present = False
    checks = {
        "receipt_valid": receipt_valid,
        "task_reference_valid": task_reference_valid,
        "task_record_present": task_record_present,
        "log_reference_safe": log_reference_safe,
        "evidence_log_present": log_present,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "id": "verification_receipt_chain",
        "owner": "evidence",
        "kind": "durable_relationship",
        "capability_seam": "verification_evidence",
        "status": "pass" if not failures else "fail",
        "observed": True,
        "checks": checks,
        "failure_codes": failures,
    }


def _platform_invariants(root):
    return [_adapter_binding_invariant(root), _receipt_chain_invariant(root)]


def _delivery_authority(root):
    root = Path(root)
    adapter_paths = (".claude/settings.json", ".codex/hooks.json")
    configured_adapters = [path for path in adapter_paths if _resolve_local_file(root, path)[0] == "valid"]
    git_paths = (".git/hooks/pre-commit", ".git/hooks/pre-push")
    git_gates = all(_resolve_local_file(root, path)[0] == "valid" for path in git_paths)
    ci_path = ".github/workflows/vemo-ci.yml"
    ci_backstop = _resolve_local_file(root, ci_path)[0] == "valid"
    if ci_backstop:
        posture = "ci_backstop_present"
    elif git_gates:
        posture = "local_gates"
    else:
        posture = "advisory"
    return {
        "posture": posture,
        "remote_branch_protection": "not_locally_verified",
        "rings": [
            {
                "id": "agent_loop",
                "role": "fast_feedback",
                "status": "adapter_config_present" if configured_adapters else "not_present",
                "candidate_adapter_files": configured_adapters,
            },
            {
                "id": "git",
                "role": "local_delivery_gate",
                "status": "gate_files_present" if git_gates else "not_present",
                "paths": list(git_paths),
            },
            {
                "id": "ci",
                "role": "server_backstop",
                "status": "workflow_present" if ci_backstop else "not_present",
                "path": ci_path,
            },
        ],
    }


def build_platform(root=None):
    """Return VEMO's responsibility topology plus locally observable deployment facts.

    The probe is deliberately content-minimizing: relationship checks read only allowlisted hook structure
    and receipt references, then emit booleans/counts rather than command or evidence content.  It never
    creates runtime directories, follows paths outside the checkout, reads telemetry payloads, or infers
    remote branch-protection state.
    """
    root = Path(root or ROOT).resolve()
    planes = _platform_planes(root)
    seams = _platform_seams(root)
    invariants = _platform_invariants(root)
    authority = _delivery_authority(root)
    missing = [
        component["path"]
        for plane in planes
        for component in plane["components"]
        if component["required"] and not component["present"]
    ]
    failed_seams = [seam["id"] for seam in seams if seam["status"] == "incomplete"]
    failed_invariants = [invariant["id"] for invariant in invariants if invariant["status"] == "fail"]
    check_status = "pass" if not (missing or failed_seams or failed_invariants) else "fail"
    return {
        "schema_version": PLATFORM_SCHEMA_VERSION,
        "command": "vemo platform",
        "platform": "VEMO AI governance platform",
        "version": _platform_version(root),
        "read_only": True,
        "data_local_only": True,
        "runtime": {
            "capability_tier": _config_value(root, "capability", "tier", "unknown"),
            "enforcement_mode": _config_value(root, "enforcement", "mode", "unknown"),
        },
        "summary": {
            "core_status": "ready" if not missing else "incomplete",
            "missing_required_components": missing,
            "capability_seam_status": "ready" if not failed_seams else "incomplete",
            "failed_capability_seams": failed_seams,
            "invariant_status": "pass" if not failed_invariants else "fail",
            "failed_invariants": failed_invariants,
            "observed_invariants": sum(1 for invariant in invariants if invariant["observed"]),
            "check_status": check_status,
            "delivery_posture": authority["posture"],
        },
        "planes": planes,
        "materializations": [
            {"id": "source", "meaning": "versioned definition or implementation"},
            {"id": "durable_record", "meaning": "reviewable task or provenance record"},
            {"id": "runtime_artifact", "meaning": "generated local observation, never source authority"},
        ],
        "capability_seams": seams,
        "lifecycle": [dict(stage) for stage in PLATFORM_LIFECYCLE],
        "invariants": invariants,
        "authority": authority,
        "boundaries": [
            "Topology and seam presence do not prove that a hook or verification command executed.",
            "Relationship invariants validate local bindings and referential integrity, not behavioral success.",
            "No source code, prompt, telemetry payload, credential, or absolute repository path is emitted.",
            "VEMO is a cooperative-host control surface, not an OS or container sandbox.",
        ],
    }


def print_platform(platform):
    summary = platform["summary"]
    runtime = platform["runtime"]
    authority = platform["authority"]
    print("VEMO platform | core=%s | delivery=%s" % (
        summary["core_status"], summary["delivery_posture"]))
    print("  runtime          : version=%s capability=%s mode=%s" % (
        platform["version"], runtime["capability_tier"], runtime["enforcement_mode"]))
    print("  responsibility planes:")
    for plane in platform["planes"]:
        print("    %-11s %-10s %d/%d required components" % (
            plane["id"], plane["status"], plane["required_present"], plane["required_total"]))
    seam_status = " ".join("%s=%s" % (seam["id"], seam["status"])
                           for seam in platform["capability_seams"])
    print("  capability seams : %s" % seam_status)
    invariant_status = " ".join("%s=%s" % (invariant["id"], invariant["status"])
                                for invariant in platform["invariants"])
    print("  invariants       : %s" % invariant_status)
    ring_status = " ".join("%s=%s" % (ring["id"], ring["status"]) for ring in authority["rings"])
    print("  delivery rings   : %s" % ring_status)
    print("  remote authority : branch protection %s" % authority["remote_branch_protection"])
    print("  lifecycle        : %s" % " -> ".join(stage["id"] for stage in platform["lifecycle"]))
    if summary["missing_required_components"]:
        print("  missing required : %s" % ", ".join(summary["missing_required_components"]))
    if summary["failed_capability_seams"]:
        print("  incomplete seams : %s" % ", ".join(summary["failed_capability_seams"]))
    if summary["failed_invariants"]:
        print("  failed invariants: %s" % ", ".join(summary["failed_invariants"]))


def detect_stack(root=None):
    root = Path(root or ROOT)
    if any((root / name).is_file() for name in ("pyproject.toml", "setup.py", "requirements.txt", "Pipfile")):
        return "python"
    if (root / "package.json").is_file():
        return "node"
    if any((root / name).is_file() for name in ("CMakeLists.txt", "Makefile")):
        return "cpp"
    if (root / "README.md").is_file():
        return "docs"
    return "unknown"


def _preset_path(root, preset):
    return Path(root) / "presets" / (preset + ".yaml")


def start_plan(root=None, preset=None, profile="solo"):
    root = Path(root or ROOT).resolve()
    detected = detect_stack(root)
    chosen = preset or (detected if detected in {"python", "node", "cpp", "docs"} else "python")
    actions = []
    conflicts = []
    source = _preset_path(root, chosen)
    overlay = root / "vemo.config.preset.yaml"
    if not source.is_file():
        conflicts.append("missing preset: %s" % chosen)
    elif overlay.is_file() and overlay.read_bytes() != source.read_bytes():
        conflicts.append("existing vemo.config.preset.yaml differs from preset '%s'" % chosen)
    else:
        actions.append({
            "action": "apply_preset",
            "path": "vemo.config.preset.yaml",
            "description": "Apply the stack defaults for %s." % chosen,
        })
    actions.extend([
        {
            "action": "install_local_guards",
            "path": ".claude/settings.json and .git/hooks",
            "description": "Install fast local hooks and Git gates; existing project files are preserved by the installer.",
        },
        {
            "action": "ensure_task_storage",
            "path": "tasks/ and tasks/Archive/",
            "description": "Create durable task storage for scope and acceptance state.",
        },
        {
            "action": "next_step",
            "path": ".github/workflows/vemo-ci.yml",
            "description": "Copy the CI backstop and require the vemo check on protected branches.",
        },
    ])
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "vemo start",
        "mode": "preview",
        "root": str(root),
        "detected_stack": detected,
        "preset": chosen,
        "profile": profile,
        "profile_name": PROFILES.get(profile, {}).get("name", profile),
        "read_only_preview": True,
        "conflicts": conflicts,
        "actions": actions,
        "next": [
            "Review this plan, then run `vemo start --preset %s --apply`." % chosen,
            "After the first agent session, run `vemo report` to see observed value.",
        ],
    }


def _write_profile(root, profile):
    path = Path(root) / ".vemo" / "product-profile.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "set_at": utc_now().isoformat().replace("+00:00", "Z"),
        "data_local_only": True,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def apply_start(root=None, preset=None, profile="solo"):
    root = Path(root or ROOT).resolve()
    plan = start_plan(root, preset, profile)
    if plan["conflicts"]:
        return {**plan, "mode": "blocked", "exit_code": 2}
    command = [sys.executable, str(root / "bin" / "vemo"), "init", "--preset", plan["preset"]]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode == 0:
        _write_profile(root, profile)
    return {
        **plan,
        "mode": "apply",
        "exit_code": result.returncode,
        "init_output": (result.stdout + result.stderr).strip(),
    }


def _task_counts(root):
    counts = {"total": 0, "active": 0, "accepted": 0}
    tasks = Path(root) / "tasks"
    if not tasks.is_dir():
        return counts
    for path in tasks.glob("*.md"):
        if path.name.startswith("_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"(?ms)^---\s*\n(.*?)\n---", text)
        if not match:
            continue
        state = re.search(r"(?m)^state:\s*(\S+)", match.group(1))
        counts["total"] += 1
        value = state.group(1) if state else "PlanCreated"
        if value not in {"Archived", "AcceptancePassed", "ProcedureCompleted"}:
            counts["active"] += 1
        if value in {"AcceptancePassed", "ProcedureCompleted", "Archived"}:
            counts["accepted"] += 1
    return counts


def _telemetry(root, days):
    path = Path(root) / ".vemo" / "telemetry.jsonl"
    cutoff = utc_now() - timedelta(days=days)
    counts = {
        "events": 0,
        "sessions": 0,
        "blocked_actions": 0,
        "degraded_guards": 0,
        "approved_exceptions": 0,
        "malformed_events": 0,
    }
    if not path.is_file():
        return counts
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        row = _read_json_line(line)
        if not row:
            counts["malformed_events"] += 1
            continue
        stamp = _stamp(row.get("ts"))
        if stamp and stamp < cutoff:
            continue
        counts["events"] += 1
        event = str(row.get("event") or "")
        if event == "session_start":
            counts["sessions"] += 1
        if "block" in event or event in {"scope_violation", "destructive_command", "secret_in_diff"}:
            counts["blocked_actions"] += 1
        if event == "guard_degraded":
            counts["degraded_guards"] += 1
        if event == "command_approved":
            counts["approved_exceptions"] += 1
    return counts


def _read_json_line(line):
    try:
        value = json.loads(line)
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


def _verification(root, days):
    run_dir = Path(root) / ".vemo" / "run"
    cutoff = utc_now() - timedelta(days=days)
    runs = 0
    if run_dir.is_dir():
        for path in run_dir.glob("*.log"):
            try:
                if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) >= cutoff:
                    runs += 1
            except OSError:
                pass
    receipt = _read_json(Path(root) / ".vemo" / "run" / "receipt.json")
    if not isinstance(receipt, dict):
        return {"runs": runs, "latest": None, "status": "not_run"}
    exits = receipt.get("exit_codes") or {}
    status = "passed" if exits and all(value == 0 for value in exits.values()) else "failed"
    return {
        "runs": runs,
        "latest": {
            "timestamp": receipt.get("ts"),
            "profile": receipt.get("profile"),
            "cached": bool(receipt.get("cached")),
            "status": status,
        },
        "status": status,
    }


def _recommendations(root, report):
    setup = report["setup"]
    recommendations = []
    if not setup["config"]:
        recommendations.append("Run `vemo start --apply` to initialize the project.")
    elif not setup["hooks"]:
        recommendations.append("Run `vemo start --apply` to install local guards.")
    if not setup["ci"]:
        recommendations.append("Add the VEMO CI backstop and require it on protected branches.")
    if report["verification"]["status"] == "not_run":
        recommendations.append("Create a scoped task, then run `vemo verify` for executed evidence.")
    if report["profile"] == "solo":
        recommendations.append("Move to the team profile when more than one person or Agent edits the repo.")
    if report["telemetry"]["malformed_events"]:
        recommendations.append("Review malformed telemetry lines before using this report for audit evidence.")
    return recommendations or ["Keep the current policy and review this report after each delivery cycle."]


def build_report(root=None, days=30):
    root = Path(root or ROOT).resolve()
    profile_payload = _read_json(root / ".vemo" / "product-profile.json", {}) or {}
    profile = profile_payload.get("profile") if profile_payload.get("profile") in PROFILES else "solo"
    setup = {
        "config": (root / "vemo.config.yaml").is_file(),
        "hooks": (root / ".claude" / "settings.json").is_file(),
        "git_gates": (root / ".git" / "hooks" / "pre-commit").is_file()
                     and (root / ".git" / "hooks" / "pre-push").is_file(),
        "ci": (root / ".github" / "workflows" / "vemo-ci.yml").is_file(),
        "mode": _config_value(root, "enforcement", "mode", "unknown"),
        "capability_tier": _config_value(root, "capability", "tier", "unknown"),
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now().isoformat().replace("+00:00", "Z"),
        "window_days": days,
        "profile": profile,
        "profile_name": PROFILES[profile]["name"],
        "setup": setup,
        "telemetry": _telemetry(root, days),
        "verification": _verification(root, days),
        "tasks": _task_counts(root),
        "data_local_only": True,
        "source_upload": False,
        "measurement_note": "Observed local events and receipts only; no incident prevention, legal compliance, or monetary savings are inferred.",
    }
    report["recommendations"] = _recommendations(root, report)
    report["readiness"] = "ready" if all((setup["config"], setup["hooks"], setup["git_gates"], setup["ci"])) else "partial"
    return report


def print_report(report):
    observed = report["telemetry"]
    verification = report["verification"]
    setup = report["setup"]
    print("VEMO value report | last %d days | profile=%s" % (report["window_days"], report["profile_name"]))
    print("  readiness        : %s" % report["readiness"])
    print("  local data only  : yes (no source upload)")
    print("  observed events  : %d" % observed["events"])
    print("  blocked actions  : %d" % observed["blocked_actions"])
    print("  sessions         : %d" % observed["sessions"])
    print("  verification     : %s (%d run log(s))" % (verification["status"], verification["runs"]))
    print("  tasks            : %d total / %d active / %d accepted" % (
        report["tasks"]["total"], report["tasks"]["active"], report["tasks"]["accepted"]))
    print("  setup            : config=%s hooks=%s git_gates=%s ci=%s mode=%s" % (
        "on" if setup["config"] else "off", "on" if setup["hooks"] else "off",
        "on" if setup["git_gates"] else "off", "on" if setup["ci"] else "off", setup["mode"]))
    print("  next best actions:")
    for item in report["recommendations"]:
        print("    - %s" % item)


def build_parser():
    parser = argparse.ArgumentParser(description="VEMO product onboarding, platform topology, and local value reporting")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="Preview or apply first-project onboarding")
    start.add_argument("--preset", choices=("python", "node", "cpp", "docs"))
    start.add_argument("--profile", choices=tuple(PROFILES), default="solo")
    start.add_argument("--apply", action="store_true")
    start.add_argument("--json", action="store_true")
    report = sub.add_parser("report", help="Show observed local governance value")
    report.add_argument("--days", type=int, default=30)
    report.add_argument("--json", action="store_true")
    platform = sub.add_parser("platform", help="Show the read-only AI platform topology and delivery posture")
    platform.add_argument("--json", action="store_true")
    platform.add_argument("--check", action="store_true", help="Exit non-zero on incomplete core/seams or failed invariants")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "start":
        if args.apply:
            payload = apply_start(ROOT, args.preset, args.profile)
        else:
            payload = start_plan(ROOT, args.preset, args.profile)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("VEMO start %s | stack=%s preset=%s profile=%s" % (
                payload["mode"], payload["detected_stack"], payload["preset"], payload["profile_name"]))
            for item in payload["actions"]:
                print("  %-20s %s" % (item["action"], item["path"]))
            if payload["conflicts"]:
                print("blocked by conflicts:")
                for item in payload["conflicts"]:
                    print("  - %s" % item)
            for item in payload.get("next", []):
                print("next: %s" % item)
            if args.apply and payload.get("init_output"):
                print(payload["init_output"])
        return int(payload.get("exit_code", 1 if payload.get("conflicts") else 0))
    if args.command == "platform":
        payload = build_platform(ROOT)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_platform(payload)
        return 0 if not args.check or payload["summary"]["check_status"] == "pass" else 2
    days = max(1, min(args.days, 3650))
    payload = build_report(ROOT, days)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
