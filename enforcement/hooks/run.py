#!/usr/bin/env python3
"""Thin harness adapter. All decisions come from enforcement/core.py."""

import json
import os
from pathlib import Path
import sys

ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[2]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core


WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def payload():
    try: return json.load(sys.stdin)
    except (ValueError, OSError): return {}


def evaluate(mode, data):
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    if mode == "edit" or tool in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path")
        content = tool_input.get("content") or tool_input.get("new_string")
        return core.check_action("write", path=path, content=content, root=ROOT)
    if mode == "command" or tool == "Bash":
        return core.check_action("command", command=tool_input.get("command", ""), root=ROOT)
    return core.decision("allow", "action_allowed", action=mode)


def selftest():
    task = {"version": 1, "id": "T-test", "scope": ["src/**"], "risk": "normal",
            "verify": [], "approval": {"granted": False}}
    assert core.in_scope("src/app.py", task)
    assert not core.in_scope("outside.py", task)
    assert core.classify_command("rm -rf build") == "destructive_fs"
    assert core.decision("allow", "ok")["decision"] == "allow"
    print("VEMO hook adapter selftest: OK")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest": return selftest()
    mode = argv[0] if argv else "action"
    result = evaluate(mode, payload())
    if result["decision"] == "allow": return 0
    print("[VEMO] %s: %s" % (result["decision"].upper(), result["reason"]), file=sys.stderr)
    return 2


if __name__ == "__main__": raise SystemExit(main())
