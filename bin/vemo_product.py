#!/usr/bin/env python3
"""User-facing product workflows for VEMO.

This layer is intentionally read-mostly. It makes onboarding and recurring value visible without
moving enforcement out of the existing hooks, Git gates, and CI backstop.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[1]).resolve()
SCHEMA_VERSION = 1
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


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _stamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _config_value(root, section, key, default=None):
    path = Path(root) / "vemo.config.yaml"
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
    parser = argparse.ArgumentParser(description="VEMO product onboarding and local value reporting")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="Preview or apply first-project onboarding")
    start.add_argument("--preset", choices=("python", "node", "cpp", "docs"))
    start.add_argument("--profile", choices=tuple(PROFILES), default="solo")
    start.add_argument("--apply", action="store_true")
    start.add_argument("--json", action="store_true")
    report = sub.add_parser("report", help="Show observed local governance value")
    report.add_argument("--days", type=int, default=30)
    report.add_argument("--json", action="store_true")
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
    days = max(1, min(args.days, 3650))
    payload = build_report(ROOT, days)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
