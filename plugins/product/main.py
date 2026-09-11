#!/usr/bin/env python3
"""Optional read-only product summary for the minimal VEMO kernel."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[2]).resolve()
sys.path.insert(0, str(ROOT / "enforcement"))
import core


def platform():
    policy = core.load_policy(ROOT); task = core.load_task(ROOT)
    return {"version": 1, "core": ["policy", "task", "gate", "verify", "evidence"],
            "policy": core.POLICY_FILE, "task": task["id"], "risk": task["risk"],
            "plugins": {"enabled": policy["plugins"], "installed": sorted(core.plugin_manifests(ROOT))},
            "decision": core.check_merge(ROOT, os.environ.get("VEMO_DIFF_RANGE"))}


def report(days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days); decisions = Counter(); evidence = []
    directory = ROOT / core.EVIDENCE_DIR
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try: row = json.loads(path.read_text(encoding="utf-8")); stamp = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
        except (OSError, ValueError, KeyError, TypeError): continue
        if stamp >= cutoff:
            decisions["passed" if row.get("passed") else "failed"] += 1
            evidence.append({"task": row.get("task"), "passed": row.get("passed"), "ts": row.get("ts")})
    return {"version": 1, "days": days, "verification": dict(decisions), "evidence": evidence,
            "current": platform()["decision"]}


def main(argv=None):
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("platform"); report_parser = sub.add_parser("report"); report_parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args(argv); value = platform() if args.command == "platform" else report(args.days)
    print(json.dumps(value, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
