#!/usr/bin/env python3
"""VEMO task-state validator (v1.1) — the deterministic parser hooks/CI rely on.

v1.1 fixes/adds (vs v1.0):
  * Correct NESTED YAML-subset parsing (v1.0 collapsed `acceptance:`/`judge:` maps to []).
  * `tier-required --paths ...`  -> compute required risk tier from vemo.config.yaml globs
                                    (closes the agent self-classification loophole; CI enforces it).
  * `get --field a.b`            -> read a dotted nested field of the active task.
  * `gate-check --gate r2-judge` -> R2 tasks must carry judge.verdict == pass.
  * `doctor`                     -> validate config + active task front-matter.
Stdlib only (no PyYAML) so it runs anywhere VEMO is dropped, incl. Windows/PowerShell wrappers.
"""
import sys, os, glob, fnmatch, argparse, re, json
from datetime import datetime

ROOT = os.environ.get("VEMO_ROOT") or os.popen("git rev-parse --show-toplevel 2>/dev/null").read().strip() or "."
TASKS_DIR = os.path.join(ROOT, "tasks")
CONFIG = os.path.join(ROOT, "vemo.config.yaml")
CONFIG_OVERLAY = os.path.join(ROOT, "vemo.config.preset.yaml")  # v1.4: per-stack preset overlay (vemo init)
AUTO_STATE = os.path.join(ROOT, ".vemo", "auto_mode.json")
RUN_STATE = os.path.join(ROOT, ".vemo", "run.json")
TIER_RANK = {"R0": 1, "R1": 2, "R2": 3}


def _auto_state():
    """Read .vemo/auto_mode.json, honoring TTL expiry. Returns {'enabled': bool, ...}."""
    try:
        st = json.load(open(AUTO_STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"enabled": False}
    exp = st.get("expires_at")
    if st.get("enabled") and exp:
        try:
            if datetime.now() > datetime.fromisoformat(exp):
                return {"enabled": False, "expired": True}
        except ValueError:
            pass
    return st


# ── run budget / stop rules (v1.3, from Fable 5 analysis) ──
def _run_cfg():
    return _load_config().get("run_budget") or {}


def _read_run():
    try:
        return json.load(open(RUN_STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"started": datetime.now().isoformat(timespec="minutes"), "tool_calls": 0, "files": []}


def _save_run(r):
    os.makedirs(os.path.dirname(RUN_STATE), exist_ok=True)
    json.dump(r, open(RUN_STATE, "w", encoding="utf-8"), indent=2)


def budget_reset():
    _save_run({"started": datetime.now().isoformat(timespec="minutes"), "tool_calls": 0, "files": []})
    return "reset"


def budget_tick(path=None):
    cfg, r = _run_cfg(), _read_run()
    r["tool_calls"] = int(r.get("tool_calls", 0)) + 1
    if path:
        files = set(r.get("files", [])); files.add(_rel(path)); r["files"] = sorted(files)
    _save_run(r)
    if not cfg.get("enabled"):
        return "ok"
    if r["tool_calls"] > int(cfg.get("max_tool_calls", 10**9)):
        return "stop:max_tool_calls(%d)" % r["tool_calls"]
    if len(r.get("files", [])) > int(cfg.get("max_files_touched", 10**9)):
        return "stop:max_files_touched(%d)" % len(r["files"])
    try:
        mins = (datetime.now() - datetime.fromisoformat(r.get("started"))).total_seconds() / 60
        if mins > float(cfg.get("max_wall_clock_min", 10**9)):
            return "stop:max_wall_clock_min(%d)" % mins
    except (ValueError, TypeError):
        pass
    return "ok"


def budget_status():
    cfg, r = _run_cfg(), _read_run()
    return "calls=%s/%s files=%s/%s enabled=%s started=%s" % (
        r.get("tool_calls", 0), cfg.get("max_tool_calls", "-"),
        len(r.get("files", [])), cfg.get("max_files_touched", "-"),
        bool(cfg.get("enabled")), r.get("started"))


# ── YAML-subset parser (mappings, nested-by-indent, inline lists, block lists, scalars) ──
def _strip_comment(v):
    s = v.lstrip()
    if s.startswith('"') or s.startswith("'"):          # quoted scalar: keep quoted token, drop trailing comment
        end = s.find(s[0], 1)
        return s[:end + 1] if end != -1 else s
    if s.startswith("["):                               # inline list: keep up to closing ], drop trailing comment
        end = s.find("]")
        return s[:end + 1] if end != -1 else s
    return re.split(r"\s+#", v, 1)[0]


def _scalar(v):
    v = v.strip()
    if v.startswith("["):                       # inline list; tolerate a trailing "# comment" after ]
        end = v.rfind("]")
        inner = (v[1:end] if end != -1 else v[1:]).strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
    if v in ("", "null", "~"):
        return None
    if v in ("true", "false"):
        return v == "true"
    return v.strip("\"'")


def _load_yaml_subset(text):
    root = {}
    stack = [[-1, root, None, None]]   # [indent, container, parent_container, parent_key]
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        top = stack[-1]
        cont = top[1]
        if s.startswith("- "):
            item = _scalar(_strip_comment(s[2:]))
            if isinstance(cont, dict):
                if not cont:                       # empty map created for a key that is actually a list
                    newlist = []
                    if top[2] is not None:
                        top[2][top[3]] = newlist
                    top[1] = cont = newlist
                else:
                    continue                       # malformed; skip safely
            if isinstance(cont, list):
                cont.append(item)
            continue
        key, _, val = s.partition(":")
        key, val = key.strip(), _strip_comment(val).strip()
        if not isinstance(cont, dict):
            continue
        if val == "":
            child = {}
            cont[key] = child
            stack.append([indent, child, cont, key])
        else:
            cont[key] = _scalar(val)
    return root


def _parse_front_matter(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return {}
    if not text.lstrip().startswith("---"):
        return {}
    parts = text.split("---", 2)
    return _load_yaml_subset(parts[1]) if len(parts) >= 3 else {}


def _deep_merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _load_config():
    """Base config + optional per-stack preset overlay (vemo.config.preset.yaml), deep-merged.
    Convention-over-configuration: a preset supplies sane stack defaults; the base stays the template."""
    base = {}
    try:
        base = _load_yaml_subset(open(CONFIG, encoding="utf-8").read())
    except OSError:
        pass
    try:
        base = _deep_merge(base, _load_yaml_subset(open(CONFIG_OVERLAY, encoding="utf-8").read()))
    except OSError:
        pass
    return base


def _rel(target):
    # v1.7: resolve a relative input against ROOT (repo-relative), not the process CWD —
    # makes scope/tier checks CWD-independent (a robustness bug the eval harness caught).
    t = target if os.path.isabs(target) else os.path.join(ROOT, target)
    return os.path.relpath(os.path.abspath(t), ROOT)


def _match(rel, g):
    return fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g.replace("**/", "*").replace("**", "*"))


# ── active task ──
def _active_task():
    best, best_hb = None, ""
    for path in glob.glob(os.path.join(TASKS_DIR, "*.md")):
        if os.path.basename(path).startswith("_"):
            continue
        fm = _parse_front_matter(path)
        if not fm or fm.get("state") == "Archived":
            continue
        hb = fm.get("heartbeat", "") or ""
        if hb >= best_hb:
            best, best_hb = (path, fm), hb
    return best


def _dig(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


# ── commands ──
def scope_check(target):
    act = _active_task()
    if not act:
        return "no-active-task"
    globs = act[1].get("scope_in") or []
    if not globs:
        return "no-active-task"
    rel = _rel(target)
    return "in-scope" if any(_match(rel, g) for g in globs) else "out-of-scope"


def tier_required(paths):
    """Highest risk tier any of the given paths falls into, per vemo.config.yaml risk_tiers."""
    tiers = _load_config().get("risk_tiers", {}) or {}
    # name -> short code, checked high→low
    ordered = sorted(tiers.items(), key=lambda kv: -TIER_RANK.get(kv[0].split("_")[0], 0))
    best = "R0"
    for p in paths:
        rel = _rel(p)
        for name, spec in ordered:
            code = name.split("_")[0]
            for g in (spec or {}).get("match_paths", []) or []:
                if _match(rel, g):
                    if TIER_RANK.get(code, 1) > TIER_RANK.get(best, 1):
                        best = code
                    break
            else:
                continue
            break
    return best


def gate_check(gate):
    act = _active_task()
    if not act:
        return "block:no-active-task"
    fm = act[1]
    if gate == "acceptance-before-push":
        order = ["PlanCreated", "ReviewApproved", "ImplementationDone",
                 "AcceptancePassed", "ProcedureCompleted", "Archived"]
        st = fm.get("state", "PlanCreated")
        if st not in order or order.index(st) < order.index("AcceptancePassed"):
            return f"block:state={st} (need AcceptancePassed before push)"
        cfg = _load_config()                                    # v1.6 executed-ground-truth gate
        if _dig(cfg, "verification.ground_truth_required") and (fm.get("risk") or "R0") != "R0":
            acc = fm.get("acceptance") or {}
            if acc.get("status") == "passed" and (acc.get("build_exit") in (None, "null") or not acc.get("evidence")):
                return "block:executed-evidence-missing ('passed' acceptance lacks a run trace: need exit code + evidence log)"
        return "ok"
    if gate == "r2-judge":
        if (fm.get("risk") or "R0").startswith("R2"):
            v = _dig(fm, "judge.verdict")
            return "ok" if v == "pass" else f"block:judge-verdict={v} (R2 requires governance-judge pass)"
        return "ok"
    if gate == "plan-before-commit":
        return "ok" if fm.get("state") else "block:no-plan"
    return "ok"


def verify_plan(risk):
    """v1.6: derive the required VERIFICATION depth from capability.tier × risk (the inverse coupling).
    Stronger tier => more independent verifiers + ground-truth, less prescription. Mechanizes capability.spec."""
    cfg = _load_config()
    tier = _dig(cfg, "capability.tier") or "high"
    gt = "optional" if risk == "R0" else "required"
    panel = int(_dig(cfg, "verification.independent_verifiers." + tier) or 1)
    verifiers = 0 if risk == "R0" else (1 if risk == "R1" else panel)
    narration = "required" if (_dig(cfg, "verification.require_intent_narration") and tier in ("frontier", "high")) else "advised"
    human = "intent + irreversible only" if tier in ("frontier", "high") else "intent + plan-review + irreversible"
    return f"tier={tier} risk={risk} ground_truth={gt} verifiers={verifiers} narration={narration} human_gate={human}"


def selfcheck():
    """v1.7: framework internal-consistency conformance — catch drift before it ships."""
    issues = []
    cfg = _load_config()
    if _dig(cfg, "capability.tier") not in ("frontier", "high", "medium", "low"):
        issues.append("config: capability.tier invalid")
    for k in ("risk_tiers", "enforcement", "verification", "model_routing", "run_budget"):
        if not cfg.get(k):
            issues.append("config: %s missing" % k)
    if not _dig(cfg, "enforcement.safety_invariant_of_capability"):
        issues.append("config: enforcement.safety_invariant_of_capability not set")
    for s in ("safety.spec.md", "task.spec.md", "verify.spec.md", "capability.spec.md"):
        if not os.path.exists(os.path.join(ROOT, "specs", s)):
            issues.append("specs/%s missing" % s)
    skdir = os.path.join(ROOT, "skill")
    if os.path.isdir(skdir):
        for dd in sorted(os.listdir(skdir)):
            p = os.path.join(skdir, dd)
            if os.path.isdir(p) and not os.path.exists(os.path.join(p, "SKILL.md")):
                issues.append("skill/%s: no SKILL.md" % dd)
    for h in ("guard-scope.sh", "guard-command.sh", "guard-secret.sh", "guard-budget.sh"):
        if not os.path.exists(os.path.join(ROOT, "enforcement", "hooks", h)):
            issues.append("enforcement/hooks/%s missing" % h)
    settings = os.path.join(ROOT, ".claude", "settings.json")          # v1.8 tamper-evidence
    if os.path.exists(settings):
        try:
            txt = open(settings, encoding="utf-8").read()
            if "guard-scope" not in txt and "run.py scope" not in txt:
                issues.append("tamper: .claude/settings.json present but the scope guard is not registered (hooks disabled?)")
        except OSError:
            pass
    print("VEMO selfcheck: OK — framework internally consistent" if not issues
          else "VEMO selfcheck: %d issue(s)\n  - %s" % (len(issues), "\n  - ".join(issues)))
    return 0 if not issues else 1


def doctor():
    issues = []
    cfg = _load_config()
    if not cfg:
        issues.append("config: vemo.config.yaml not found or unparseable")
    else:
        tier = _dig(cfg, "capability.tier")
        if tier not in ("high", "medium", "low"):
            issues.append(f"config: capability.tier='{tier}' invalid (want high|medium|low)")
        if not _dig(cfg, "model_routing"):
            issues.append("config: model_routing missing")
        if not cfg.get("risk_tiers"):
            issues.append("config: risk_tiers missing")
    act = _active_task()
    if act:
        fm = act[1]
        for f in ("id", "risk", "state", "scope_in"):
            if fm.get(f) in (None, "", []):
                issues.append(f"active task {os.path.basename(act[0])}: field '{f}' empty/missing")
    print("VEMO doctor: OK — no issues" if not issues else "VEMO doctor: %d issue(s)\n  - %s" % (len(issues), "\n  - ".join(issues)))
    return 0 if not issues else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope-check"); s.add_argument("--path", required=True)
    g = sub.add_parser("gate-check");  g.add_argument("--gate", required=True)
    t = sub.add_parser("tier-required"); t.add_argument("--paths", nargs="+", required=True)
    ge = sub.add_parser("get"); ge.add_argument("--field", required=True)
    sub.add_parser("active"); sub.add_parser("doctor"); sub.add_parser("auto-status")
    aa = sub.add_parser("auto-allows"); aa.add_argument("--tier", required=True)
    bt = sub.add_parser("budget-tick"); bt.add_argument("--path", default=None)
    sub.add_parser("budget-reset"); sub.add_parser("budget-status")
    cg = sub.add_parser("config-get"); cg.add_argument("--field", required=True)
    vp = sub.add_parser("verify-plan"); vp.add_argument("--risk", required=True)
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "scope-check":
        print(scope_check(a.path))
    elif a.cmd == "gate-check":
        print(gate_check(a.gate))
    elif a.cmd == "tier-required":
        print(tier_required(a.paths))
    elif a.cmd == "get":
        act = _active_task()
        v = _dig(act[1], a.field) if act else None
        print("null" if v is None else (",".join(v) if isinstance(v, list) else v))
    elif a.cmd == "active":
        print(f"{os.path.basename(act[0])} state={act[1].get('state')} risk={act[1].get('risk')}" if (act := _active_task()) else "none")
    elif a.cmd == "auto-status":
        st = _auto_state()
        print("on max_tier=%s allow_r2=%s expires=%s by=%s" % (
            st.get("max_auto_tier"), st.get("allow_r2"), st.get("expires_at") or "never", st.get("enabled_by"))
            if st.get("enabled") else "off" + (" (expired)" if st.get("expired") else ""))
    elif a.cmd == "auto-allows":
        st = _auto_state()
        ok = (st.get("enabled")
              and TIER_RANK.get(a.tier, 9) <= TIER_RANK.get(st.get("max_auto_tier", "R0"), 0)
              and (a.tier != "R2" or st.get("allow_r2")))
        print("yes" if ok else "no")
    elif a.cmd == "budget-tick":
        print(budget_tick(a.path))
    elif a.cmd == "budget-reset":
        print(budget_reset())
    elif a.cmd == "budget-status":
        print(budget_status())
    elif a.cmd == "config-get":
        v = _dig(_load_config(), a.field)
        print("null" if v is None else (",".join(v) if isinstance(v, list) else v))
    elif a.cmd == "verify-plan":
        print(verify_plan(a.risk))
    elif a.cmd == "selfcheck":
        sys.exit(selfcheck())
    elif a.cmd == "doctor":
        sys.exit(doctor())


if __name__ == "__main__":
    main()
