#!/usr/bin/env python3
"""Small executable conformance suite for the shipped governance contract."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enforcement"))
import core


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def fixture():
    temp = tempfile.TemporaryDirectory(prefix="vemo-eval-")
    root = Path(temp.name)
    git(root, "init", "-q"); git(root, "config", "user.email", "eval@example.invalid"); git(root, "config", "user.name", "eval")
    (root / "src").mkdir(); (root / "tests").mkdir(); (root / ".vemo/evidence").mkdir(parents=True)
    (root / "vemo.json").write_text(json.dumps({"version": 2, "critical_paths": ["critical/**"],
        "deny_actions": ["destructive_fs", "git_history_rewrite", "credential_write", "out_of_repo_write"],
        "verification": {"normal": [["python3", "-c", "print('ok')"]],
                         "critical": [["python3", "-c", "print('critical')"]]},
        "plugins": []}), encoding="utf-8")
    (root / "vemo.task.json").write_text(json.dumps({"version": 1, "id": "T-eval", "scope": ["src/**", "tests/**"],
        "risk": "normal"}), encoding="utf-8")
    (root / "src/app.py").write_text("before=1\n", encoding="utf-8"); git(root, "add", "src/app.py", "vemo.json", "vemo.task.json")
    git(root, "commit", "-qm", "baseline")
    return temp, root


def main():
    checks = []
    temp, root = fixture()
    try:
        (root / "src/app.py").write_text("after=2\n", encoding="utf-8"); git(root, "add", "src/app.py")
        checks.append(("scope_allow", core.check_action("write", "src/app.py", root=root)["decision"] == "allow"))
        checks.append(("scope_deny", core.check_action("write", "outside.py", root=root)["reason"] == "scope_violation"))
        checks.append(("danger_requires_approval", core.check_action("command", command="rm -rf build", root=root)["decision"] == "approval_required"))
        checks.append(("merge_needs_evidence", core.check_merge(root)["reason"] == "verification_missing"))
        evidence = core.verify(root)
        checks.append(("verify_executes", evidence["passed"] is True))
        checks.append(("merge_allows", core.check_merge(root)["decision"] == "allow"))
        (root / "src/app.py").write_text("changed_again=3\n", encoding="utf-8"); git(root, "add", "src/app.py")
        checks.append(("stale_blocks", core.check_merge(root)["reason"] == "verification_stale"))
    finally:
        temp.cleanup()
    failed = [name for name, ok in checks if not ok]
    print("[eval] conformance %d/%d" % (len(checks) - len(failed), len(checks)))
    if failed: print("failed:", ", ".join(failed)); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())
