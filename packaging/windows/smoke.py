"""Exercise the packaged runtime and real Git gates in an isolated Windows project."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="windows-中文 项目-", dir=args.evidence.parent))
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VEMO_", "PYTHON"))}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PATH=str(package / "runtime") + os.pathsep + os.environ["PATH"])
    python = str(package / "runtime/python.exe")
    entry = str(package / "framework/bin/vemo")
    checks = []

    def run(argv, cwd=target, expected=0):
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=120)
        if result.returncode != expected:
            raise AssertionError(f"{argv}: exit={result.returncode}\n{result.stdout}\n{result.stderr}")
        return result

    def setup(action, *extra):
        result = run([python, entry, "setup", action, str(target), "--json", *extra])
        return json.loads(result.stdout)

    run(["git", "init", "-q"])
    (target / "README.md").write_text("Project-owned document\n", encoding="utf-8")
    before = (target / "README.md").read_bytes()
    preview = setup("install", "--preset", "docs")
    assert preview["ready"] and not (target / "bin/vemo").exists()
    checks.append("preview is read-only")
    installed = setup("install", "--preset", "docs", "--apply", "--plan-id", preview["plan_id"])
    assert installed["verification"]["ready"]
    checks.append("Unicode-path install and all setup probes")
    repeated = setup("install", "--preset", "docs")
    assert all(row["status"] == "unchanged" for row in repeated["actions"])
    assert setup("check")["ready"]
    checks.append("idempotency and installed integrity")
    (target / "unplanned.py").write_text("print('unplanned')\n", encoding="utf-8")
    run(["git", "add", "unplanned.py"])
    blocked = subprocess.run(["git", "-c", "user.name=VEMO probe", "-c", "user.email=probe@example.invalid",
                              "commit", "-m", "This unplanned commit must be rejected"], cwd=target,
                             env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert blocked.returncode != 0 and "plan-before-commit" in blocked.stdout + blocked.stderr, blocked
    assert subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=target, capture_output=True).returncode != 0
    checks.append("real Git commit blocked without task plan; no commit created")
    removal = setup("uninstall")
    assert removal["ready"]
    setup("uninstall", "--apply", "--plan-id", removal["plan_id"])
    assert not (target / "bin/vemo").exists() and not (target / ".git/hooks/pre-commit").exists()
    assert (target / "README.md").read_bytes() == before and (target / "unplanned.py").exists()
    checks.append("uninstall preserves project-owned files")
    result = {"status": "pass", "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "package": str(package), "build_id": json.loads((package / "package.json").read_text())["build_id"],
              "project": str(target), "checks": checks, "blocked_commit_exit": blocked.returncode,
              "blocked_commit_output": (blocked.stdout + blocked.stderr)[-8000:]}
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
