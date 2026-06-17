#!/usr/bin/env python3
"""Portable, Windows-friendly hook dispatcher (R2) — pure Python, no bash required.

The `.sh` guards need bash/git-bash; this is the bash-free path for Windows (and the closing of the
long-standing portability gap). The decision logic lives in the stdlib-only validator, so this just routes.
Register in .claude/settings.json on hosts without bash, e.g.:
  { "type": "command", "command": "python enforcement/hooks/run.py scope" }
  { "type": "command", "command": "python enforcement/hooks/run.py budget" }
Exit 2 = block (stderr fed back to the agent), exit 0 = allow.
"""
import sys, os, json, subprocess
SELF = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SELF))
os.environ.setdefault("VEMO_ROOT", ROOT)
VAL = os.path.join(ROOT, "enforcement", "validators", "task_state.py")


def val(*a):
    return subprocess.run([sys.executable, VAL, *a], capture_output=True, text=True).stdout.strip()


def _payload():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _target(d):
    ti = d.get("tool_input", {})
    return ti.get("file_path") or ti.get("path") or ""


def _monitor():
    return val("config-get", "--field", "enforcement.mode").lower() == "monitor"


def main():
    guard = sys.argv[1] if len(sys.argv) > 1 else ""
    d = _payload()
    if guard == "scope":
        t = _target(d)
        if t:
            v = val("scope-check", "--path", t)
            if v in ("out-of-scope", "no-active-task"):
                msg = f"[VEMO] BLOCKED (safety.spec#1): '{t}' outside the active task scope_in." if v == "out-of-scope" \
                    else "[VEMO] BLOCKED (safety.spec#1): no active task declares scope_in."
                if _monitor():
                    print(msg + "  (monitor mode: logged, not blocking)", file=sys.stderr); return 0
                print(msg, file=sys.stderr); return 2
    elif guard == "budget":
        t = _target(d)
        v = val("budget-tick", *(["--path", t] if t else []))
        if v.startswith("stop:"):
            if val("auto-status").startswith("on") and not _monitor():
                print(f"[VEMO] STOP RULE (unattended): run budget exceeded — {v}.", file=sys.stderr); return 2
            print(f"[VEMO] run budget exceeded — {v} (advisory).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
