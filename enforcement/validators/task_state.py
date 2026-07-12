#!/usr/bin/env python3
"""VEMO task-state validator — the deterministic parser hooks/CI rely on.

Commands (each prints a machine-readable verdict the hooks/CI act on):
  * `tier-required --paths ...`  -> compute the required risk tier from vemo.config.yaml globs
                                    (closes the agent self-classification loophole; CI enforces it).
                                    Unmatched paths default to risk_tiers.unmatched (fail-safe R1).
  * `gate-check --gate required-judge`
                                -> tasks whose tier/capability require a judge must carry
                                   judge.verdict == pass AND enough contiguous pass records in
                                   .vemo/judge.jsonl. A front-matter-only pass, a later fail, or too
                                   few verifier passes does not open the gate.
  * `verify-run`                 -> execute paths.build/paths.smoke, write the evidence log and a
                                    machine-written receipt (.vemo/run/receipt.json). The gate reads
                                    the receipt — executed ground truth, not a self-reported number.
  * `judge-record`               -> append the judge's verdict to the append-only .vemo/judge.jsonl.
  * `bind --session --task`      -> bind a harness session to a task (scope checks then resolve the
                                    session's own task instead of "latest heartbeat wins").
  * `doctor` / `selfcheck`       -> health + internal-consistency (incl. ENFORCED-BY claims must map
                                    to existing mechanisms, and every config key must have a consumer).
Parses a YAML subset (nested maps, block/inline lists, inline {} maps) directly. Stdlib only
(no PyYAML) so it runs anywhere VEMO is dropped, incl. Windows.
Failure semantics: an internal error prints `error:<reason>` and exits 3 — callers treat that as
BLOCK for safety-critical gates (fail closed), never as silent pass.
"""
import sys, os, glob, fnmatch, argparse, re, json, subprocess, hashlib, shutil
from datetime import datetime, timedelta, timezone

ROOT = os.environ.get("VEMO_ROOT") or os.popen("git rev-parse --show-toplevel 2>/dev/null").read().strip() or "."
TASKS_DIR = os.path.join(ROOT, "tasks")
CONFIG = os.path.join(ROOT, "vemo.config.yaml")
CONFIG_OVERLAY = os.path.join(ROOT, "vemo.config.preset.yaml")  # per-stack preset overlay (vemo init)
AUTO_STATE = os.path.join(ROOT, ".vemo", "auto_mode.json")
SESSION_MAP = os.path.join(ROOT, ".vemo", "session_task.json")
JUDGE_LOG = os.path.join(ROOT, ".vemo", "judge.jsonl")
RUN_DIR = os.path.join(ROOT, ".vemo", "run")
RECEIPT = os.path.join(RUN_DIR, "receipt.json")
CACHE = os.path.join(RUN_DIR, "cache.json")
TIER_RANK = {"R0": 1, "R1": 2, "R2": 3}
CHANGE_CLASS_RANK = {
    "standard": 1, "ci-init": 1, "ci-narrow": 2,
    "security": 3, "permissions": 4, "release": 5,
}

# Binary / model-blob extensions safety.spec#6 forbids the agent to edit (vendor drops under
# exclusions.third_party are exempt — importing a prebuilt lib is a human supply-chain decision).
BLOB_EXT = (".a", ".so", ".dll", ".exe", ".lib", ".bin", ".o", ".obj", ".dylib",
            ".pt", ".pth", ".onnx", ".tflite", ".gguf", ".safetensors", ".caffemodel", ".weights")


def _utc_now():
    return datetime.now(timezone.utc)


def _utc_stamp(timespec="seconds"):
    return _utc_now().isoformat(timespec=timespec).replace("+00:00", "Z")


def _parse_timestamp(value):
    """Parse RFC3339 plus legacy naive local timestamps, returning aware UTC."""
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


def _auto_state():
    """Read .vemo/auto_mode.json, honoring TTL expiry. Returns {'enabled': bool, ...}."""
    try:
        st = json.load(open(AUTO_STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"enabled": False}
    exp = st.get("expires_at")
    if st.get("enabled") and exp:
        try:
            if _utc_now() > _parse_timestamp(exp):
                return {"enabled": False, "expired": True}
        except ValueError:
            pass
    return st


# ── run budget / stop rules ──
def _run_cfg():
    return _load_config().get("run_budget") or {}


def _run_state_path(session=None):
    # per-session counters: two concurrent sessions must not share one budget
    name = "run-%s.json" % re.sub(r"[^A-Za-z0-9_-]", "", session)[:32] if session else "run.json"
    return os.path.join(ROOT, ".vemo", name)


def _read_run(session=None):
    try:
        return json.load(open(_run_state_path(session), encoding="utf-8"))
    except (OSError, ValueError):
        return {"started": _utc_stamp(), "tool_calls": 0, "files": []}


def _save_run(r, session=None):
    p = _run_state_path(session)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(r, open(p, "w", encoding="utf-8"), indent=2)


def budget_reset(session=None):
    _save_run({"started": _utc_stamp(), "tool_calls": 0, "files": []}, session)
    return "reset"


STUCK_REPEATS = 3   # N identical consecutive Bash commands = a loop that stopped making progress


def budget_tick(path=None, write=False, session=None, sig=None):
    cfg, r = _run_cfg(), _read_run(session)
    r["tool_calls"] = int(r.get("tool_calls", 0)) + 1
    if path and write:   # only WRITE-type tools count as "touched" — reading is not touching
        files = set(r.get("files", [])); files.add(_rel(path)); r["files"] = sorted(files)
    if sig:              # duplicate-call chain (Bash only): repeated identical edits/reads are normal, retries are not
        r["recent_bash"] = (r.get("recent_bash", []) + [sig])[-(STUCK_REPEATS + 1):]
    _save_run(r, session)
    if not cfg.get("enabled"):
        return "ok"
    calls = r["tool_calls"]
    if calls > int(cfg.get("max_tool_calls", 10**9)):
        return "stop:max_tool_calls(%d)" % calls
    if len(r.get("files", [])) > int(cfg.get("max_files_touched", 10**9)):
        return "stop:max_files_touched(%d)" % len(r["files"])
    recent = r.get("recent_bash", [])
    if sig and len(recent) >= STUCK_REPEATS and len(set(recent[-STUCK_REPEATS:])) == 1:
        return ("stop:stuck-loop(same Bash command %dx — an agent that repeats itself has stopped making "
                "progress; change approach, or escalate to the human)" % STUCK_REPEATS)
    try:
        mins = (_utc_now() - _parse_timestamp(r.get("started"))).total_seconds() / 60
        if mins > float(cfg.get("max_wall_clock_min", 10**9)):
            return "stop:max_wall_clock_min(%d)" % mins
    except (ValueError, TypeError):
        pass
    # advisory cadence notes (non-blocking): checkpoint + re-anchor reminders for long runs
    every = int(cfg.get("reanchor_every_calls") or 0)
    if every and calls % every == 0:
        return "note:reanchor(calls=%d) — re-state the original task intent (long runs drift)" % calls
    every = int(cfg.get("checkpoint_every_calls") or 0)
    if every and calls % every == 0:
        return "note:checkpoint(calls=%d) — record progress to the task file" % calls
    return "ok"


def budget_status(session=None):
    cfg, r = _run_cfg(), _read_run(session)
    return "calls=%s/%s files=%s/%s enabled=%s started=%s" % (
        r.get("tool_calls", 0), cfg.get("max_tool_calls", "-"),
        len(r.get("files", [])), cfg.get("max_files_touched", "-"),
        bool(cfg.get("enabled")), r.get("started"))


# ── YAML-subset parser (mappings, nested-by-indent, inline lists, inline {} maps, block lists) ──
def _strip_comment(v):
    s = v.lstrip()
    if s.startswith('"') or s.startswith("'"):          # quoted scalar: keep quoted token, drop trailing comment
        end = s.find(s[0], 1)
        return s[:end + 1] if end != -1 else s
    if s.startswith("["):                               # inline list: keep up to closing ], drop trailing comment
        end = s.find("]")
        return s[:end + 1] if end != -1 else s
    if s.startswith("{"):                               # inline map: keep up to closing }, drop trailing comment
        end = s.find("}")
        return s[:end + 1] if end != -1 else s
    return re.split(r"\s+#", v, 1)[0]


def _scalar(v):
    v = v.strip()
    if v.startswith("["):                       # inline list; tolerate a trailing "# comment" after ]
        end = v.rfind("]")
        inner = (v[1:end] if end != -1 else v[1:]).strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
    if v.startswith("{"):                       # inline map: { k: v, k2: v2 } — the task.spec example style
        end = v.rfind("}")
        inner = (v[1:end] if end != -1 else v[1:]).strip()
        out = {}
        for pair in inner.split(","):
            if ":" not in pair:
                continue
            k, _, pv = pair.partition(":")
            out[k.strip().strip("\"'")] = _scalar(pv)
        return out
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
    """Base config + optional per-stack preset overlay (vemo.config.preset.yaml), deep-merged."""
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
    # resolve a relative input against ROOT (repo-relative), not the process CWD
    t = target if os.path.isabs(target) else os.path.join(ROOT, target)
    return os.path.relpath(os.path.abspath(t), ROOT)


def _match(rel, g):
    return fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g.replace("**/", "*").replace("**", "*"))


# ── active task ──
def _session_bound_task(session):
    if not session:
        return None
    try:
        m = json.load(open(SESSION_MAP, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    fname = m.get(session)
    if not fname:
        return None
    path = os.path.join(TASKS_DIR, fname)
    fm = _parse_front_matter(path)
    if fm and fm.get("state") != "Archived":
        return (path, fm)
    return None


def _active_task(session=None):
    """The task scope/gates are checked against. A session-bound task wins (see `bind`);
    otherwise fall back to the freshest heartbeat among live tasks."""
    bound = _session_bound_task(session)
    if bound:
        return bound
    best, best_hb = None, ""
    for path in glob.glob(os.path.join(TASKS_DIR, "*.md")):
        if os.path.basename(path).startswith("_"):
            continue
        fm = _parse_front_matter(path)
        if not fm or fm.get("state") == "Archived":
            continue
        hb = str(fm.get("heartbeat", "") or "")
        if hb >= best_hb:
            best, best_hb = (path, fm), hb
    return best


def _task_from_file(path):
    """Load one live task file from an absolute or repo-relative path."""
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    p = os.path.abspath(p)
    try:
        rel = os.path.relpath(p, TASKS_DIR)
    except ValueError:
        return None
    if rel.startswith("..") or os.path.basename(p).startswith("_"):
        return None
    fm = _parse_front_matter(p)
    if fm and fm.get("state") != "Archived":
        return (p, fm)
    return None


def _tasks_from_files(task_files):
    tasks, seen = [], set()
    for path in task_files or []:
        task = _task_from_file(path)
        if task and task[0] not in seen:
            tasks.append(task)
            seen.add(task[0])
    return tasks


def _task_context(task_files=None, session=None):
    """Return explicit task files when provided; otherwise preserve active-task behavior."""
    tasks = _tasks_from_files(task_files)
    if tasks:
        return tasks
    act = _active_task(session)
    return [act] if act else []


def _max_task_risk(tasks):
    best = "R0"
    for _, fm in tasks:
        risk = str(fm.get("risk") or "R0")[:2]
        if TIER_RANK.get(risk, 1) > TIER_RANK.get(best, 1):
            best = risk
    return best


def _max_task_change(tasks):
    best = "standard"
    for _, fm in tasks:
        value = str(fm.get("change_class") or "standard")
        if CHANGE_CLASS_RANK.get(value, 3) > CHANGE_CLASS_RANK.get(best, 1):
            best = value
    return best


def bind_session(session, task_id):
    hit = None
    for path in glob.glob(os.path.join(TASKS_DIR, "*.md")):
        fm = _parse_front_matter(path)
        if fm.get("id") == task_id:
            hit = os.path.basename(path)
            break
    if not hit:
        return "error:no-task-with-id-%s" % task_id
    try:
        m = json.load(open(SESSION_MAP, encoding="utf-8"))
    except (OSError, ValueError):
        m = {}
    m[session] = hit
    os.makedirs(os.path.dirname(SESSION_MAP), exist_ok=True)
    json.dump(m, open(SESSION_MAP, "w", encoding="utf-8"), indent=2)
    return "bound:%s->%s" % (session, hit)


def _dig(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


# ── commands ──
def scope_check(target, session=None, task_files=None):
    tasks = _task_context(task_files, session)
    if not tasks:
        return "no-active-task"
    rel = _rel(target)
    has_scope = False
    for _, fm in tasks:
        globs = fm.get("scope_in") or []
        has_scope = has_scope or bool(globs)
        if any(_match(rel, g) for g in globs):
            return "in-scope"
    return "out-of-scope" if has_scope else "no-active-task"


def blob_check(target):
    """safety.spec#6 — the agent must not hand-edit binaries / model blobs.
    Vendor paths in exclusions.third_party are exempt (supply-chain drops are a human decision)."""
    rel = _rel(target)
    if not rel.lower().endswith(BLOB_EXT):
        return "ok"
    for g in (_load_config().get("exclusions", {}) or {}).get("third_party", []) or []:
        if _match(rel, g):
            return "ok"
    return "blob:%s" % rel


def _workflow_diff_lines(diff_text):
    """Return +/- hunk lines for workflow files only; diff metadata is excluded."""
    lines, current, saw_header = [], None, False
    for raw in (diff_text or "").splitlines():
        if raw.startswith("diff --git "):
            saw_header = True
            m = re.search(r" b/(.+)$", raw)
            current = m.group(1).replace("\\", "/") if m else None
            continue
        if raw.startswith("+++ "):
            saw_header = True
            value = raw[4:].strip()
            if value != "/dev/null":
                current = value[2:] if value.startswith("b/") else value
                current = current.replace("\\", "/")
            continue
        if raw.startswith(("--- ", "@@")) or not raw.startswith(("+", "-")):
            continue
        if not saw_header or (current and current.startswith(".github/workflows/")):
            lines.append((raw[0], raw[1:].strip()))
    return lines


def _workflow_removed(diff_text):
    current = None
    for raw in (diff_text or "").splitlines():
        if raw.startswith("diff --git "):
            m = re.search(r" a/(.+?) b/", raw)
            current = m.group(1).replace("\\", "/") if m else None
        elif raw.startswith("+++ /dev/null") and current and current.startswith(".github/workflows/"):
            return True
        elif raw.startswith("rename from ") and raw[len("rename from "):].replace("\\", "/").startswith(
                ".github/workflows/"):
            return True
    return False


def change_class(paths, diff_text=""):
    """Classify operational semantics. Metadata/docs never make a CI-only patch look broader."""
    rels = [_rel(p).replace("\\", "/") for p in paths]
    operational = [p for p in rels if not (p.startswith("tasks/") or p.startswith("docs/")
                                            or p.endswith(".md") or p.startswith(".vemo/"))]
    if not operational:
        return "standard"
    if _workflow_removed(diff_text):
        return "security"
    lowered = "\n".join(text.lower() for _, text in _workflow_diff_lines(diff_text))
    if any(p.startswith(("release/", ".github/actions/release")) for p in operational) or re.search(
            r"\b(release|deploy|publish|attest|provenance|environment:)\b|twine\s+upload|"
            r"npm\s+publish|docker\s+push|\bpypi\b", lowered):
        return "release"
    if re.search(r"\bpermissions\s*:|id-token\s*:|contents\s*:\s*write|packages\s*:\s*write", lowered):
        return "permissions"
    if re.search(r"pull_request_target|workflow_run|workflow_call|\bsecrets?\b|\btoken\b|git push|gh release|"
                 r"gate-check|pre-commit|pre-push|vemo verify|eval/run\.py|security[-_ ]?scan", lowered):
        return "security"

    workflows = [p for p in operational if p.startswith(".github/workflows/")]
    if workflows and len(workflows) == len(operational):
        changed = _workflow_diff_lines(diff_text)
        allowed = re.compile(
            r"^(?:|#.*|-?\s*name:\s*(?:set up python|setup python|install dependencies)|"
            r"-?\s*uses:\s*actions/setup-python@[^\s]+|with:|python-version:|cache:|"
            r"cache-dependency-path:|"
            r"-?\s*(?:with|python-version|cache|cache-dependency-path):.*|"
            r"-?\s*run:\s*(?:[|>-]\s*|(?:python(?:3)?\s+-m\s+pip|pip(?:3)?|uv|poetry)\s+.*(?:install|sync).*)|"
            r"(?:python(?:3)?\s+-m\s+pip|pip(?:3)?|uv|poetry)\s+.*(?:install|sync)|"
            r"(?:python(?:3)?\s+-m\s+pip|pip(?:3)?)\s+install.*|"
            r"(?:requirements[^:]*|pyproject\.toml|poetry\.lock|uv\.lock):?.*)$", re.I)
        def safe_init_line(sign, text):
            if sign != "+" or not allowed.match(text):
                return False
            if re.fullmatch(r"-?\s*run:\s*[|>-]\s*", text):
                return True
            return not any(token in text for token in ("&", "|", ";", "`", "$", "<", ">"))

        if changed and all(safe_init_line(sign, text) for sign, text in changed):
            return "ci-init"
        return "ci-narrow"

    if any(p.startswith(("enforcement/", "specs/", ".claude/"))
           or re.match(r"vemo\.config.*\.ya?ml$", p) for p in operational):
        return "security"
    return "standard"


def tier_required(paths, diff_text=""):
    """Highest risk tier any of the given paths falls into, per vemo.config.yaml risk_tiers.
    A path matching NO tier gets risk_tiers.unmatched (default R1) — unknown ≠ trivial."""
    cfg = _load_config()
    tiers = cfg.get("risk_tiers", {}) or {}
    default = str(_dig(cfg, "risk_tiers.unmatched") or "R1")
    ordered = sorted(((k, v) for k, v in tiers.items() if isinstance(v, dict)),
                     key=lambda kv: -TIER_RANK.get(kv[0].split("_")[0], 0))
    best = "R0"
    semantic = change_class(paths, diff_text) if diff_text else None
    for p in paths:
        rel = _rel(p)
        code = None
        for name, spec in ordered:
            if any(_match(rel, g) for g in (spec or {}).get("match_paths", []) or []):
                code = name.split("_")[0]
                break
        # Path-only classification stays fail-safe R2. A workflow is R1 only with affirmative
        # diff evidence that every changed line is additive Python/dependency initialization.
        if rel.replace("\\", "/").startswith(".github/workflows/") and semantic == "ci-init":
            code = "R1"
        code = code or default
        if TIER_RANK.get(code, 2) > TIER_RANK.get(best, 1):
            best = code
    return best


def _judge_records(task_id):
    """All judge provenance rows for a task from the append-only .vemo/judge.jsonl."""
    rows = []
    try:
        for line in open(JUDGE_LOG, encoding="utf-8"):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("task") == task_id:
                rows.append(row)
        return rows
    except OSError:
        return []


def _judge_snapshot(fm=None):
    """Hash only this task's staged/range patch, excluding the provenance log itself."""
    diff_range = os.environ.get("VEMO_DIFF_RANGE")
    if diff_range and (diff_range.startswith("-") or any(c in diff_range for c in ("\0", "\n", "\r"))):
        return "invalid-range"
    base = ["git", "-C", ROOT, "diff", "--no-renames"]
    if diff_range:
        base.append(diff_range)
    else:
        base.append("--cached")
    try:
        names = subprocess.run(base + ["--name-only", "-z", "--"], capture_output=True, timeout=30)
        if names.returncode != 0:
            return "unresolved-range" if diff_range else ""
        scopes = (fm or {}).get("scope_in") or []
        active_task_path = None
        if (fm or {}).get("id"):
            active_task_path = next((os.path.relpath(path, ROOT).replace("\\", "/")
                                     for path in glob.glob(os.path.join(TASKS_DIR, "*.md"))
                                     if _parse_front_matter(path).get("id") == fm.get("id")), None)
        paths = [raw.decode("utf-8", "surrogateescape").replace("\\", "/")
                 for raw in names.stdout.split(b"\0") if raw]
        paths = sorted(path for path in paths if path != ".vemo/judge.jsonl"
                       and (not scopes or any(_match(path, pattern) for pattern in scopes)))
        h = hashlib.sha256()
        for path in paths:
            if path == active_task_path:
                if diff_range:
                    target = diff_range.rsplit("...", 1)[-1].rsplit("..", 1)[-1]
                    obj = "%s:%s" % (target, path)
                else:
                    obj = ":%s" % path
                content = subprocess.run(["git", "-C", ROOT, "show", obj], capture_output=True, timeout=30)
                payload = content.stdout if content.returncode == 0 else b"<deleted>"
                text = payload.decode("utf-8", "surrogateescape")
                text = re.sub(r"(?ms)^judge:\s*\n(?:^[ \t]+.*\n)*",
                              "judge:\n  <verdict-cache-excluded>\n", text)
                payload = text.encode("utf-8", "surrogateescape")
            else:
                patch = subprocess.run(base + ["--binary", "--", path], capture_output=True, timeout=30)
                if patch.returncode != 0:
                    return "unresolved-range" if diff_range else ""
                payload = patch.stdout
            h.update(path.encode("utf-8", "surrogateescape") + b"\0" + payload + b"\0")
        return h.hexdigest()
    except OSError:
        return ""


def _judge_provenance(task_id):
    """Last recorded judge verdict for this task from the append-only .vemo/judge.jsonl."""
    rows = _judge_records(task_id)
    return rows[-1] if rows else None


def _required_judge_passes(risk, cfg=None, auto=False, fm=None, change=None):
    """Derive judge depth from risk, capability, and semantic change class."""
    cfg = cfg or _load_config()
    code = str(risk or "R0")[:2]
    klass = change or ((fm or {}).get("change_class")) or "standard"
    if code == "R0":
        return 0
    tier = _dig(cfg, "capability.tier") or "high"
    if code == "R2":
        if klass == "ci-narrow":
            return 1
        return int(_dig(cfg, "verification.independent_verifiers." + tier) or 1)
    if auto and _dig(cfg, "auto_mode.require_judge"):
        return 1
    return 1 if tier in ("medium", "low") else 0


def _judge_gate_result(fm, required):
    """Return ok/block for the front-matter verdict plus the required pass suffix in the judge log."""
    if required <= 0:
        return "ok"
    v = _dig(fm, "judge.verdict")
    if v != "pass":
        return f"block:judge-verdict={v} (requires {required} governance-judge pass record(s))"
    rows = _judge_records(fm.get("id"))
    if not rows:
        return "block:judge-no-provenance (front-matter says pass but .vemo/judge.jsonl has no record — the judge must write its verdict via `task_state.py judge-record`, a pasted verdict does not count)"
    suffix = 0
    snapshot = _judge_snapshot(fm)
    for row in reversed(rows):
        snapshot_ok = not snapshot or row.get("snapshot") == snapshot
        if row.get("verdict") == "pass" and snapshot_ok:
            suffix += 1
            continue
        break
    last = rows[-1]
    if last.get("verdict") != "pass":
        return "block:judge-provenance-mismatch (log says '%s', front-matter says 'pass')" % last.get("verdict")
    if suffix < required:
        return "block:judge-pass-count=%d (requires %d contiguous pass record(s) for this capability/risk tier)" % (suffix, required)
    return "ok"


def _read_receipt():
    try:
        return json.load(open(RECEIPT, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _verification_gate_result(fm):
    if str(fm.get("change_class") or "standard") == "release":
        profile = _dig(fm, "verification.profile")
        if profile != "release":
            return "block:release-requires-verification-profile=release (got %s)" % profile
    return "ok"


def _acceptance_gate_result(fm, cfg):
    """acceptance-before-push for ONE task (gate_check loops every task in the checked set —
    a multi-task push range must not let non-first tasks ride through unchecked)."""
    risk = str(fm.get("risk") or "R0")
    contract = _verification_gate_result(fm)
    if contract != "ok":
        return contract
    if risk.startswith("R0"):
        return "ok"                       # R0 lifecycle has no acceptance gate (velocity path)
    order = ["PlanCreated", "ReviewApproved", "ImplementationDone",
             "AcceptancePassed", "ProcedureCompleted", "Archived"]
    st = fm.get("state", "PlanCreated")
    if st not in order or order.index(st) < order.index("AcceptancePassed"):
        return f"block:state={st} (need AcceptancePassed before push)"
    if _dig(cfg, "verification.ground_truth_required"):
        acc = fm.get("acceptance")
        if not isinstance(acc, dict):
            return "block:unparseable-acceptance (front-matter `acceptance:` is not a map)"
        if acc.get("status") == "passed":
            if acc.get("build_exit") in (None, "null") or not acc.get("evidence"):
                return "block:executed-evidence-missing ('passed' acceptance lacks a run trace: need exit code + evidence log)"
            # If the project configured a real build/smoke, the gate trusts the machine-written receipt
            # produced by `verify-run` — not exit codes (or a log path) typed into front-matter. The
            # receipt's OWN log is the executed ground truth, freshly produced by the gate's side THIS run;
            # the front-matter `evidence:` path is a human cache that may point at a gitignored/rotated log
            # absent on a clean CI checkout (which is exactly where the guarantee must hold).
            if _dig(cfg, "paths.build") or _dig(cfg, "paths.smoke") or isinstance(fm.get("verification"), dict):
                rcpt = _read_receipt()
                if not rcpt:
                    return "block:no-verify-receipt (paths.build/smoke configured — run `vemo verify` so the gate gets executed ground truth)"
                if str(rcpt.get("task")) not in (str(fm.get("id")), "adhoc"):
                    return "block:receipt-task-mismatch (receipt is for '%s', checked task is '%s' — re-run `vemo verify`)" % (rcpt.get("task"), fm.get("id"))
                exits = rcpt.get("exit_codes")
                failed = any(value != 0 for value in exits.values()) if isinstance(exits, dict) \
                    else rcpt.get("build_exit") not in (0, None) or rcpt.get("smoke_exit") not in (0, None)
                if failed:
                    return "block:receipt-failed (verify-run recorded build_exit=%s smoke_exit=%s)" % (rcpt.get("build_exit"), rcpt.get("smoke_exit"))
                try:
                    profile, commands = _verification_contract(fm, cfg)
                    current, _ = _scope_fingerprint(fm, profile, commands)
                    if rcpt.get("fingerprint") and rcpt.get("fingerprint") != current:
                        return "block:receipt-stale (task scope or verification commands changed; re-run `vemo verify`)"
                except ValueError as e:
                    return "block:verification-contract (%s)" % e
                rlog = os.path.join(ROOT, str(rcpt.get("log") or ""))
                if not (os.path.isfile(rlog) and os.path.getsize(rlog) > 0):
                    return "block:receipt-log-missing (receipt references '%s' but it is absent/empty — re-run `vemo verify`)" % rcpt.get("log")
            else:
                # No build/smoke configured: the front-matter evidence file is the only run trace we have.
                ev = os.path.join(ROOT, str(acc.get("evidence")))
                if not (os.path.isfile(ev) and os.path.getsize(ev) > 0):
                    return "block:evidence-file-missing ('%s' does not exist or is empty — a claimed path is not a run trace)" % acc.get("evidence")
    # Under unattended auto mode the judge replaces the absent human reviewer on R1+ (automation.spec#3).
    if _auto_state().get("enabled") and _dig(cfg, "auto_mode.require_judge") and TIER_RANK.get(risk[:2], 1) >= 2:
        j = _judge_gate_result(fm, 1)
        if j != "ok":
            return "block:auto-mode-requires-judge (%s)" % j[len("block:"):]
    return "ok"


def gate_check(gate, session=None, task_files=None):
    tasks = _task_context(task_files, session)
    if not tasks:
        return "block:no-active-task"
    if gate == "acceptance-before-push":
        cfg = _load_config()
        for _, fm in tasks:
            v = _acceptance_gate_result(fm, cfg)
            if v != "ok":
                return v if len(tasks) == 1 else "%s [task=%s]" % (v, fm.get("id"))
        return "ok"
    if gate in ("r2-judge", "required-judge"):
        for _, candidate in tasks:
            required = _required_judge_passes(str(candidate.get("risk") or "R0"), fm=candidate)
            result = _judge_gate_result(candidate, required)
            if result != "ok":
                return result
        return "ok"
    if gate == "verification-contract":
        for _, candidate in tasks:
            result = _verification_gate_result(candidate)
            if result != "ok":
                return result
        return "ok"
    if gate == "plan-before-commit":
        return "ok" if all(candidate.get("state") for _, candidate in tasks) else "block:no-plan"
    return "ok"


def judge_record(task, verdict, evidence="", confidence=""):
    task_fm = next((fm for path in glob.glob(os.path.join(TASKS_DIR, "*.md"))
                    if (fm := _parse_front_matter(path)).get("id") == task), None)
    row = {"ts": _utc_stamp(), "task": task, "verdict": verdict,
           "session": os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("VEMO_SESSION") or "unknown",
           "snapshot": _judge_snapshot(task_fm), "evidence": evidence, "confidence": confidence}
    os.makedirs(os.path.dirname(JUDGE_LOG), exist_ok=True)
    with open(JUDGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return "recorded:%s=%s" % (task, verdict)


def _verification_contract(fm, cfg):
    verification = (fm or {}).get("verification")
    if not isinstance(verification, dict):
        commands = [("build", _dig(cfg, "paths.build")), ("smoke", _dig(cfg, "paths.smoke"))]
        return "legacy", [(name, cmd) for name, cmd in commands if cmd]
    profile = str(verification.get("profile") or "focused")
    if profile == "focused":
        local = verification.get("commands") or {}
        commands = [(name, local.get(name)) for name in ("test", "lint", "smoke")]
    elif profile == "full":
        commands = [("build", _dig(cfg, "paths.build")), ("smoke", _dig(cfg, "paths.smoke"))]
    elif profile == "release":
        commands = [("build", _dig(cfg, "paths.build")), ("smoke", _dig(cfg, "paths.smoke")),
                    ("package_scan", _dig(cfg, "paths.package_scan"))]
    else:
        raise ValueError("unknown verification.profile '%s'" % profile)
    missing = [name for name, cmd in commands if not cmd]
    if missing:
        raise ValueError("verification.profile '%s' requires command(s): %s" % (profile, ", ".join(missing)))
    return profile, commands


def _scope_fingerprint(fm, profile, commands):
    scopes = (fm or {}).get("scope_in") or []
    try:
        p = subprocess.run(["git", "-C", ROOT, "ls-files", "-co", "--exclude-standard", "-z"],
                           capture_output=True, timeout=30)
        candidates = [x.decode("utf-8", "surrogateescape").replace("\\", "/")
                      for x in p.stdout.split(b"\0") if x]
    except OSError:
        candidates = []
    selected = sorted(set(rel for rel in candidates
                          if not rel.startswith(("tasks/", ".vemo/"))
                          and any(_match(rel, pattern) for pattern in scopes)))
    h = hashlib.sha256()
    contract = {"profile": profile, "commands": commands, "files": selected}
    h.update(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for rel in selected:
        h.update(b"\0" + rel.encode("utf-8", "surrogateescape") + b"\0")
        try:
            with open(os.path.join(ROOT, rel), "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest(), selected


def _read_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _successful_exits(exits):
    return bool(exits) and all(value == 0 for value in exits.values())


def _runtime_command(command):
    """Use the running interpreter when a configured python3 launcher is absent (notably Windows)."""
    if (os.name == "nt" or shutil.which("python3") is None) \
            and re.match(r"^\s*python3(?:\.exe)?(?:\s|$)", command, re.I):
        return re.sub(r"^\s*python3(?:\.exe)?", lambda _m: '"%s"' % sys.executable,
                      command, count=1, flags=re.I)
    return command


def _receipt_from_run(task_id, profile, commands, exits, log_rel, fingerprint, files, cached=False,
                      source_ts=None):
    non_smoke = [value for name, value in exits.items() if name != "smoke"]
    build_exit = exits.get("build")
    if build_exit is None and non_smoke:
        build_exit = next((value for value in non_smoke if value != 0), 0)
    return {
        "ts": _utc_stamp(), "task": task_id, "profile": profile, "cached": cached,
        "source_ts": source_ts, "fingerprint": fingerprint, "scope_files": files,
        "commands": [{"name": name, "command": cmd, "exit": exits.get(name)} for name, cmd in commands],
        "exit_codes": exits, "build_exit": build_exit, "smoke_exit": exits.get("smoke"), "log": log_rel,
    }


def verify_run(session=None, no_cache=False):
    """Execute the configured build/smoke and write evidence + a machine receipt.
    This is the ONLY writer of .vemo/run/receipt.json — the acceptance gate trusts the receipt,
    not exit codes typed into front-matter (executed ground truth, produced by the gate's own side)."""
    cfg = _load_config()
    act = _active_task(session)
    task_id = act[1].get("id") if act else "adhoc"
    fm = act[1] if act else {}
    try:
        profile, commands = _verification_contract(fm, cfg)
    except ValueError as e:
        return "FAIL contract=%s" % e
    if not commands:
        return "no-build-configured (set paths.build / paths.smoke in vemo.config.yaml)"
    fingerprint, files = _scope_fingerprint(fm, profile, commands)
    os.makedirs(RUN_DIR, exist_ok=True)
    cache = _read_cache()
    cache_on = bool(_dig(cfg, "verification.cache_enabled")) and not no_cache
    if cache_on and cache and cache.get("fingerprint") == fingerprint \
            and cache.get("profile") == profile and _successful_exits(cache.get("exit_codes") or {}):
        log_rel = str(cache.get("log") or "")
        log_abs = os.path.join(ROOT, log_rel)
        if os.path.isfile(log_abs) and os.path.getsize(log_abs) > 0:
            receipt = _receipt_from_run(task_id, profile, commands, cache["exit_codes"], log_rel,
                                        fingerprint, files, True, cache.get("ts"))
            json.dump(receipt, open(RECEIPT, "w", encoding="utf-8"), indent=2)
            return "pass cached=true profile=%s log=%s receipt=.vemo/run/receipt.json" % (profile, log_rel)
    ts = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    log_rel = os.path.join(".vemo", "run", "%s-%s.log" % (task_id, ts))
    log_abs = os.path.join(ROOT, log_rel)
    exits = {}
    with open(log_abs, "w", encoding="utf-8") as log:
        for name, cmd in commands:
            actual = _runtime_command(cmd)
            log.write("$ %s\n" % actual); log.flush()
            p = subprocess.run(actual, shell=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            exits[name] = p.returncode
            log.write("[exit %d]\n" % p.returncode); log.flush()
    receipt = _receipt_from_run(task_id, profile, commands, exits, log_rel, fingerprint, files)
    json.dump(receipt, open(RECEIPT, "w", encoding="utf-8"), indent=2)
    if _successful_exits(exits):
        json.dump({"ts": receipt["ts"], "profile": profile, "fingerprint": fingerprint,
                   "exit_codes": exits, "log": log_rel}, open(CACHE, "w", encoding="utf-8"), indent=2)
    return "%s cached=false profile=%s build_exit=%s smoke_exit=%s log=%s receipt=.vemo/run/receipt.json" % (
        "pass" if _successful_exits(exits) else "FAIL", profile, receipt.get("build_exit"),
        receipt.get("smoke_exit"), log_rel)


def verify_plan(risk, change="standard"):
    """derive the required VERIFICATION depth from capability.tier × risk (the inverse coupling)."""
    cfg = _load_config()
    tier = _dig(cfg, "capability.tier") or "high"
    gt = "optional" if risk == "R0" else "required"
    panel = int(_dig(cfg, "verification.independent_verifiers." + tier) or 1)
    verifiers = _required_judge_passes(risk, cfg, change=change)
    narration = "required" if (_dig(cfg, "verification.require_intent_narration") and tier in ("frontier", "high")) else "advised"
    human = "intent + irreversible only" if tier in ("frontier", "high") else "intent + plan-review + irreversible"
    return f"tier={tier} risk={risk} change_class={change} ground_truth={gt} verifiers={verifiers} narration={narration} human_gate={human}"


def context_brief(session=None):
    """≤20-line machine brief replacing 'read the whole config + specs' at session start.
    Facts only, produced by the gate's own code — the token-economy rule: context is for judgment,
    subprocesses are for facts."""
    cfg = _load_config()
    lines = ["VEMO %s | tier=%s mode=%s auto=%s telemetry=%s" % (
        _dig(cfg, "vemo.version") or "?", _dig(cfg, "capability.tier"),
        _dig(cfg, "enforcement.mode"), "on" if _auto_state().get("enabled") else "off",
        _dig(cfg, "observability.telemetry"))]
    act = _active_task(session)
    if act:
        fm = act[1]
        scope = fm.get("scope_in") or []
        lines.append("task %s risk=%s state=%s heartbeat=%s" % (
            fm.get("id"), fm.get("risk"), fm.get("state"), fm.get("heartbeat")))
        lines.append("scope_in (%d globs): %s%s" % (len(scope), ", ".join(scope[:6]), " …" if len(scope) > 6 else ""))
    else:
        lines.append("task none — create from tasks/_TASK_TEMPLATE.md before editing (plan-before-commit gates commits)")
    for g in ("acceptance-before-push", "required-judge"):
        try:
            lines.append("gate %s: %s" % (g, gate_check(g, session)))
        except Exception as e:
            lines.append("gate %s: error:%s" % (g, type(e).__name__))
    rcpt = _read_receipt()
    lines.append("receipt: %s" % ("task=%s build_exit=%s smoke_exit=%s" % (
        rcpt.get("task"), rcpt.get("build_exit"), rcpt.get("smoke_exit")) if rcpt else "none (`vemo verify` writes it)"))
    lines.append("budget: %s" % budget_status(session))
    skdir = os.path.join(ROOT, "skill")
    if os.path.isdir(skdir):
        names = sorted(d for d in os.listdir(skdir)
                       if os.path.isdir(os.path.join(skdir, d)) and not d.startswith("_"))
        if names:
            lines.append("skills (%d): %s — `vemo skill-roster` for purpose+usage" % (len(names), ", ".join(names)))
    lines.append("rules: mechanical gates are non-negotiable (safety.spec); specs load on demand via "
                 "specs/_manifest.yaml; do NOT bulk-read vemo.config.yaml — ask `vemo tier/check/explain`")
    return "\n".join(lines)


LENS_CHECKS = {
    "correctness": [
        "re-run the acceptance commands YOURSELF (eval/selfcheck) — exit codes + fresh report mtime vs clock",
        "negative-test at least one NEW assertion (make it fail once — a check that cannot fail is fake)",
        "receipt log content matches the claims (open the .vemo/run/*.log, don't trust the summary)",
        "timestamp sanity: no log/heartbeat newer than the real clock; evidence not older than the change it proves",
        "evidence covers the FULL scope of each claim, not a convenient subset",
    ],
    "safety": [
        "scope: every changed path (table above) matches scope_in — spot-verify a sample yourself",
        "diff has no secrets / destructive side effects / out-of-scope deletions",
        "live-fire one guard per new pattern (pipe a payload; expect exit 2) + one benign no-false-positive",
        "judge history retained (no deleted fail rows); front-matter verdict mirrors the jsonl tail",
        "no reframing: bugs stay bugs in docs/CHANGELOG; safety invariant holds at tier=frontier (spot check)",
    ],
}


def judge_brief(session=None, lens="correctness", task_files=None, diff_range=None):
    """Dossier for the governance judge: machine-checked facts up front so judge tokens go to what
    machines cannot check (claims-vs-evidence semantics, completeness, gaming) instead of re-exploring."""
    tasks = _task_context(task_files, session)
    if not tasks:
        return "no-active-task"
    out = []
    for path, fm in tasks:
        out.append("TASK %s | risk=%s state=%s file=%s" % (fm.get("id"), fm.get("risk"), fm.get("state"),
                                                           os.path.relpath(path, ROOT)))
        acc = fm.get("acceptance") or {}
        out.append("CLAIMS: acceptance.status=%s build_exit=%s smoke_exit=%s evidence=%s | judge.verdict=%s" % (
            acc.get("status"), acc.get("build_exit"), acc.get("smoke_exit"), acc.get("evidence"),
            _dig(fm, "judge.verdict")))
        try:
            body = open(path, encoding="utf-8").read()
            m = re.search(r"## Pass/Fail Criteria[^\n]*\n(.*?)(?=\n## )", body, re.S)
            if m:
                out.append("CRITERIA:")
                out += ["  " + ln.strip() for ln in m.group(1).strip().splitlines() if ln.strip()][:12]
        except OSError:
            pass
        rows = _judge_records(fm.get("id"))
        out.append("JUDGE HISTORY (%d rows): %s" % (len(rows), "; ".join(
            "%s=%s" % (r.get("ts"), r.get("verdict")) for r in rows[-5:]) or "none"))
    out.append("GATES (machine-checked facts — do not re-derive, do verify their inputs):")
    for g in ("acceptance-before-push", "required-judge", "plan-before-commit"):
        try:
            out.append("  %s: %s" % (g, gate_check(g, session, task_files)))
        except Exception as e:
            out.append("  %s: error:%s" % (g, type(e).__name__))
    try:
        out.append("  trifecta: %s" % trifecta_check(session))
    except Exception:
        pass
    rcpt = _read_receipt()
    out.append("RECEIPT: %s" % (json.dumps(rcpt) if rcpt else "none"))
    explicit_range = diff_range is not None
    requested_range = diff_range if explicit_range else os.environ.get("VEMO_DIFF_RANGE")
    if explicit_range and not str(requested_range).strip():
        raise ValueError("explicit judge range must not be empty")
    if requested_range and (str(requested_range).startswith("-")
                            or any(c in str(requested_range) for c in ("\0", "\n", "\r"))):
        raise ValueError("unsafe judge range syntax")
    try:
        cmd = ["git", "-C", ROOT, "diff", "--no-renames", "--name-only"]
        source = "staged index"
        if requested_range:
            cmd.extend([requested_range, "--"])
            source = "range %s" % requested_range
        else:
            cmd.append("--cached")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            detail = p.stderr.strip() or "exit %d" % p.returncode
            if requested_range:
                raise RuntimeError("git diff failed for %s: %s" % (source, detail))
            raise OSError("git staged diff unavailable: %s" % detail)
        changed = [ln.strip().replace("\\", "/") for ln in p.stdout.splitlines() if ln.strip()]
        out.append("CHANGES (%d files from %s; unrelated untracked/worktree files excluded):" %
                   (len(changed), source))
        for f in changed[:50]:
            out.append("  %-14s %s" % (scope_check(os.path.join(ROOT, f), session, task_files), f))
        if len(changed) > 50:
            out.append("  ... %d more (inspect the same staged/range diff)" % (len(changed) - 50))
    except RuntimeError:
        raise
    except Exception:
        out.append("CHANGES: (git unavailable — inspect the diff yourself)")
    out.append("LENS %s — your checklist (disjoint from the other pass; do not redo its items):" % lens)
    out += ["  [ ] " + c for c in LENS_CHECKS.get(lens, LENS_CHECKS["correctness"])]
    out.append("RULES: record verdict FIRST via judge-record (a verdict without provenance is treated as "
               "forged); cite file:line or command+exit per violation; you judge, you do not fix.")
    return "\n".join(out)


def heartbeat_touch(session=None, task_files=None):
    """Mechanized heartbeat: update the task file's front-matter in place — zero agent context spent
    on read-modify-write. concurrency.spec liveness without the token tax."""
    tasks = _task_context(task_files, session)
    if not tasks:
        return "error:no-active-task"
    path, fm = tasks[0]
    now = _utc_stamp()
    txt = open(path, encoding="utf-8").read()
    new, n = re.subn(r"(?m)^heartbeat:.*$", "heartbeat: %s" % now, txt, count=1)
    if not n:
        return "error:no-heartbeat-field"
    _atomic_write(path, new)
    return "heartbeat:%s=%s" % (fm.get("id"), now)


def _atomic_write(path, text):
    tmp = path + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def _one_task(session=None, task_files=None):
    tasks = _task_context(task_files, session)
    return tasks[0] if tasks else None


def task_create(title, risk, change, scopes, profile="focused"):
    if risk not in TIER_RANK:
        return "error:invalid-risk"
    if change not in CHANGE_CLASS_RANK:
        return "error:invalid-change-class"
    if profile not in ("focused", "full", "release"):
        return "error:invalid-verification-profile"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "task"
    day = _utc_now().strftime("%Y%m%d")
    task_id = "T-%s-%s" % (day, slug)
    path = os.path.join(TASKS_DIR, task_id + ".md")
    n = 2
    while os.path.exists(path):
        task_id = "T-%s-%s-%d" % (day, slug, n)
        path = os.path.join(TASKS_DIR, task_id + ".md")
        n += 1
    now = _utc_stamp()
    scope_yaml = json.dumps([(_rel(p) if os.path.isabs(p) else p).replace("\\", "/") for p in scopes],
                            ensure_ascii=False)
    local_commands = ("  commands:\n    test: \"\"\n    lint: \"\"\n    smoke: \"\"\n"
                      if profile == "focused" else "")
    body = """---
id: {task_id}
risk: {risk}
change_class: {change}
state: PlanCreated
scope_in: {scope}
scope_out: []
trifecta: []
verification:
  profile: {profile}
{local_commands}acceptance:
  status: not_run
  build_exit: null
  smoke_exit: null
  evidence: ""
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: {now}
---

# {title}

## Goal
Define the accepted outcome.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else.

## Pass/Fail Criteria
- [ ] Add measurable acceptance criteria.

## Plan
- Add the implementation plan.

## Execution Log
- {now} Task created by `vemo task create`.

## Acceptance Result
Not run.

## Conclusion
Pending.
""".format(task_id=task_id, risk=risk, change=change, scope=scope_yaml, profile=profile,
           local_commands=local_commands, now=now, title=title)
    os.makedirs(TASKS_DIR, exist_ok=True)
    _atomic_write(path, body)
    return "created:%s" % os.path.relpath(path, ROOT).replace("\\", "/")


def task_note(message, session=None, task_files=None):
    task = _one_task(session, task_files)
    if not task:
        return "error:no-active-task"
    path, fm = task
    text = open(path, encoding="utf-8").read()
    match = re.search(r"(?m)^## Execution Log\s*$", text)
    if not match:
        return "error:no-execution-log"
    following = re.search(r"(?m)^## ", text[match.end():])
    pos = match.end() + (following.start() if following else len(text[match.end():]))
    note = "- %s %s\n" % (_utc_stamp(), message.strip())
    prefix = text[:pos].rstrip() + "\n" + note + "\n"
    _atomic_write(path, prefix + text[pos:].lstrip("\n"))
    heartbeat_touch(session, [path])
    return "noted:%s" % fm.get("id")


def task_state(state, session=None, task_files=None):
    allowed = {"PlanCreated", "ReviewApproved", "ImplementationDone", "AcceptancePassed",
               "ProcedureCompleted", "Archived"}
    if state not in allowed:
        return "error:invalid-state"
    task = _one_task(session, task_files)
    if not task:
        return "error:no-active-task"
    path, fm = task
    now = _utc_stamp()
    text = open(path, encoding="utf-8").read()
    text, n_state = re.subn(r"(?m)^state:.*$", "state: %s" % state, text, count=1)
    text, n_hb = re.subn(r"(?m)^heartbeat:.*$", "heartbeat: %s" % now, text, count=1)
    if not (n_state and n_hb):
        return "error:missing-state-or-heartbeat-field"
    _atomic_write(path, text)
    return "state:%s=%s at=%s" % (fm.get("id"), state, now)


def trifecta_check(session=None):
    """OWASP ASI01 / Meta 'Rule of Two': a session touching all 3 lethal-trifecta properties needs
    explicit human approval; unattended auto mode must STOP. Honors enforcement.rule_of_two."""
    if _dig(_load_config(), "enforcement.rule_of_two") is False:
        return "ok (rule_of_two disabled in config)"
    act = _active_task(session)
    if not act:
        return "ok (no active task)"
    props = set(act[1].get("trifecta") or []) & {"private_data", "untrusted_content", "external_comms"}
    if len(props) >= 3:
        return "block:rule-of-two (3/3 lethal-trifecta properties — requires explicit human approval; unattended auto mode must stop)"
    return "ok (%d/3 trifecta properties)" % len(props)


# ── selfcheck: the framework's claims must map to existing mechanisms ──
# Every config key must have a consumer (code, or an explicitly listed prose consumer).
# A knob that changes nothing is a false control surface — worse than no knob.
KNOWN_KEYS = {
    "vemo.version": "selfcheck", "vemo.upstream": "skill/governance-sync",
    "capability.tier": "verify_plan/specs",
    "model_routing": "ADVISORY (read by humans + agent prose; no mechanical router — see config note)",
    "verification.ground_truth_required": "gate_check", "verification.require_intent_narration": "verify_plan",
    "verification.cache_enabled": "verify-run", "verification.independent_verifiers": "verify_plan/gate_check",
    "risk_tiers.unmatched": "tier_required", "risk_tiers.*": "tier_required (match_paths) / specs (gates, judge)",
    "enforcement.mode": "hooks/run.py", "enforcement.hooks": "vemo status", "enforcement.ci_backstop": "vemo status",
    "enforcement.block_on": "hooks/run.py (guard enable list)",
    "enforcement.fail_closed": "hooks/run.py (fail-closed list)",
    "enforcement.degrade_gracefully": "hooks/run.py",
    "enforcement.safety_invariant_of_capability": "selfcheck (asserted true)",
    "enforcement.enforce_risk_tier": "ci/pre-commit", "enforcement.require_judge_on_R2": "ci/pre-commit",
    "enforcement.rule_of_two": "trifecta_check",
    "paths.tasks": "reserved", "paths.task_archive": "reserved", "paths.specs": "reserved",
    "paths.repo_root": "reserved", "paths.test_entry": "verify-run (docs)", "paths.build": "verify-run",
    "paths.smoke": "verify-run", "paths.package_scan": "verify-run (release profile)",
    "concurrency.stale_threshold_hours": "doctor (stale-task warning)",
    "run_budget.enabled": "budget_tick", "run_budget.max_tool_calls": "budget_tick",
    "run_budget.max_files_touched": "budget_tick", "run_budget.max_wall_clock_min": "budget_tick",
    "run_budget.checkpoint_every_calls": "budget_tick", "run_budget.reanchor_every_calls": "budget_tick",
    "auto_mode.default_max_auto_tier": "vemo-auto", "auto_mode.default_ttl_hours": "vemo-auto",
    "auto_mode.require_judge": "gate_check (auto push)", "auto_mode.keep_mechanical_guards": "selfcheck (asserted true)",
    "auto_mode.preauthorized_commands": "hooks/run.py (command guard)", "auto_mode.record_to": "vemo-auto",
    "observability.telemetry": "hooks/run.py", "observability.eval_on_release": "skill/governance-release",
    "exclusions.third_party": "blob_check",
    "project.*": "instance-owned (comment.spec author, etc.)",
}


def _flatten_keys(d, prefix=""):
    for k, v in d.items():
        dotted = prefix + k
        if isinstance(v, dict) and prefix.count(".") < 1:
            yield from _flatten_keys(v, dotted + ".")
        else:
            yield dotted


def _known(dotted):
    if dotted in KNOWN_KEYS:
        return True
    head = dotted.split(".")[0]
    return (head + ".*") in KNOWN_KEYS or head in KNOWN_KEYS


def selfcheck():
    """framework internal-consistency conformance — catch drift before it ships."""
    issues = []
    cfg = _load_config()
    if _dig(cfg, "capability.tier") not in ("frontier", "high", "medium", "low"):
        issues.append("config: capability.tier invalid")
    for k in ("risk_tiers", "enforcement", "verification", "run_budget"):
        if not cfg.get(k):
            issues.append("config: %s missing" % k)
    for flag in ("enforcement.safety_invariant_of_capability", "auto_mode.keep_mechanical_guards"):
        if _dig(cfg, flag) is False:
            issues.append("config: %s must stay true (safety is capability- and mode-invariant)" % flag)
    # every config key must have a consumer — no dead knobs / false control surfaces
    for dotted in _flatten_keys(cfg):
        if not _known(dotted):
            issues.append("config: key '%s' has no consumer (wire it or delete it)" % dotted)
    for s in ("safety.spec.md", "task.spec.md", "verify.spec.md", "capability.spec.md"):
        if not os.path.exists(os.path.join(ROOT, "specs", s)):
            issues.append("specs/%s missing" % s)
    skdir = os.path.join(ROOT, "skill")
    if os.path.isdir(skdir):
        for dd in sorted(os.listdir(skdir)):
            p = os.path.join(skdir, dd)
            if os.path.isdir(p) and not os.path.exists(os.path.join(p, "SKILL.md")):
                issues.append("skill/%s: no SKILL.md" % dd)
    # the single dispatcher must exist and be registered
    if not os.path.exists(os.path.join(ROOT, "enforcement", "hooks", "run.py")):
        issues.append("enforcement/hooks/run.py missing (the dispatcher)")
    settings = os.path.join(ROOT, ".claude", "settings.json")          # tamper-evidence
    if os.path.exists(settings):
        try:
            txt = open(settings, encoding="utf-8").read()
            # the edit guard (scope+blob+secret) must be registered — accept the pre-1.1 alias too
            if "run.py" not in txt or not re.search(r'run\.py[\\"\']*\s+(edit|scope)', txt):
                issues.append("tamper: .claude/settings.json present but the edit/scope guard is not registered (hooks disabled?)")
        except OSError:
            pass
    # the judge provenance log must be TRACKED by git — server-side CI is the authority for the
    # required-judge gate, and a gitignored audit log is invisible to it (and to reviewers)
    if os.path.isdir(os.path.join(ROOT, ".git")):
        try:
            r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", ".vemo/judge.jsonl"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                issues.append(".vemo/judge.jsonl is gitignored — CI cannot verify judge provenance "
                              "(track it: ignore `.vemo/*` with `!.vemo/judge.jsonl`)")
        except OSError:
            pass
    # every ENFORCED-BY claim in safety.spec must map to an existing mechanism file
    spec = os.path.join(ROOT, "specs", "safety.spec.md")
    if os.path.exists(spec):
        txt = open(spec, encoding="utf-8").read()
        for m in re.finditer(r"ENFORCED-BY:\s*([a-z+\-]+)`?[^\n]*\n[^\n]*", txt):
            claim_block = txt[m.start():m.end() + 200]
            for ref in re.findall(r"`(enforcement/[^`]+)`", claim_block):
                if "*" in ref:                       # glob (e.g. enforcement/**), not a file reference
                    continue
                if not os.path.exists(os.path.join(ROOT, ref)):
                    issues.append("safety.spec claims `%s` but the file does not exist (label fraud)" % ref)
        needs = {"hook": os.path.join(ROOT, "enforcement", "hooks", "run.py"),
                 "ci": os.path.join(ROOT, "enforcement", "ci", "pre-commit"),
                 "pre-push": os.path.join(ROOT, "enforcement", "ci", "pre-push")}
        for token, f in needs.items():
            if ("ENFORCED-BY: %s" % token in txt or "ENFORCED-BY: hook+ci" in txt and token in ("hook", "ci")) \
                    and not os.path.exists(f):
                issues.append("safety.spec claims ENFORCED-BY %s but %s is missing" % (token, os.path.relpath(f, ROOT)))
    print("VEMO selfcheck: OK — framework internally consistent" if not issues
          else "VEMO selfcheck: %d issue(s)\n  - %s" % (len(issues), "\n  - ".join(issues)))
    return 0 if not issues else 1


def doctor():
    issues, notes = [], []
    cfg = _load_config()
    if not cfg:
        issues.append("config: vemo.config.yaml not found or unparseable")
    else:
        tier = _dig(cfg, "capability.tier")
        if tier not in ("frontier", "high", "medium", "low"):
            issues.append(f"config: capability.tier='{tier}' invalid (want frontier|high|medium|low)")
        if not cfg.get("risk_tiers"):
            issues.append("config: risk_tiers missing")
    act = _active_task()
    if act:
        fm = act[1]
        for f in ("id", "risk", "state", "scope_in"):
            if fm.get(f) in (None, "", []):
                issues.append(f"active task {os.path.basename(act[0])}: field '{f}' empty/missing")
    # stale live tasks (concurrency.stale_threshold_hours)
    thr = float(_dig(cfg, "concurrency.stale_threshold_hours") or 0)
    if thr:
        for path in glob.glob(os.path.join(TASKS_DIR, "*.md")):
            if os.path.basename(path).startswith("_"):
                continue
            fm = _parse_front_matter(path)
            if not fm or fm.get("state") == "Archived":
                continue
            try:
                hb = _parse_timestamp(fm.get("heartbeat"))
                if _utc_now() - hb > timedelta(hours=thr):
                    notes.append("stale task %s (heartbeat %s > %.0fh old) — takeover candidate" %
                                 (os.path.basename(path), fm.get("heartbeat"), thr))
            except (ValueError, TypeError):
                pass
    # gates-heartbeat: hooks registered but telemetry has never seen a session → they may not be firing
    settings = os.path.join(ROOT, ".claude", "settings.json")
    tele = os.path.join(ROOT, ".vemo", "telemetry.jsonl")
    if os.path.exists(settings) and "hooks" in open(settings, encoding="utf-8").read():
        seen = os.path.exists(tele) and "session_start" in open(tele, encoding="utf-8").read()
        if not seen:
            notes.append("hooks are registered but telemetry has no session_start event — "
                         "gates may not be firing (start a session in this repo, then re-check)")
    out = ["VEMO doctor: OK — no issues" if not issues
           else "VEMO doctor: %d issue(s)\n  - %s" % (len(issues), "\n  - ".join(issues))]
    if notes:
        out.append("  notes:\n  * " + "\n  * ".join(notes))
    print("\n".join(out))
    return 0 if not issues else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope-check"); s.add_argument("--path", required=True); s.add_argument("--session", default=None)
    s.add_argument("--task-file", action="append", default=[])
    b = sub.add_parser("blob-check"); b.add_argument("--path", required=True)
    g = sub.add_parser("gate-check");  g.add_argument("--gate", required=True); g.add_argument("--session", default=None)
    g.add_argument("--task-file", action="append", default=[])
    t = sub.add_parser("tier-required"); t.add_argument("--paths", nargs="+", required=True)
    t.add_argument("--diff-file", default=None)
    cc = sub.add_parser("change-class"); cc.add_argument("--paths", nargs="+", required=True)
    cc.add_argument("--diff-file", default=None)
    tr = sub.add_parser("task-risk"); tr.add_argument("--task-file", action="append", default=[])
    tcx = sub.add_parser("task-change-class"); tcx.add_argument("--task-file", action="append", default=[])
    ge = sub.add_parser("get"); ge.add_argument("--field", required=True)
    sub.add_parser("active"); sub.add_parser("doctor"); sub.add_parser("auto-status")
    aa = sub.add_parser("auto-allows"); aa.add_argument("--tier", required=True)
    bt = sub.add_parser("budget-tick"); bt.add_argument("--path", default=None)
    bt.add_argument("--write", action="store_true"); bt.add_argument("--session", default=None)
    bt.add_argument("--sig", default=None)
    br = sub.add_parser("budget-reset"); br.add_argument("--session", default=None)
    bs = sub.add_parser("budget-status"); bs.add_argument("--session", default=None)
    cg = sub.add_parser("config-get"); cg.add_argument("--field", required=True)
    vp = sub.add_parser("verify-plan"); vp.add_argument("--risk", required=True)
    vp.add_argument("--change-class", default="standard", choices=sorted(CHANGE_CLASS_RANK))
    vr = sub.add_parser("verify-run"); vr.add_argument("--session", default=None)
    vr.add_argument("--no-cache", action="store_true")
    jr = sub.add_parser("judge-record"); jr.add_argument("--task", required=True)
    jr.add_argument("--verdict", required=True, choices=["pass", "fail"])
    jr.add_argument("--evidence", default=""); jr.add_argument("--confidence", default="")
    bd = sub.add_parser("bind"); bd.add_argument("--session", required=True); bd.add_argument("--task", required=True)
    cx = sub.add_parser("context"); cx.add_argument("--session", default=None)
    jb = sub.add_parser("judge-brief"); jb.add_argument("--lens", default="correctness", choices=sorted(LENS_CHECKS))
    jb.add_argument("--session", default=None); jb.add_argument("--task-file", action="append", default=[])
    jb.add_argument("--range", default=None)
    hb = sub.add_parser("heartbeat"); hb.add_argument("--session", default=None)
    hb.add_argument("--task-file", action="append", default=[])
    create = sub.add_parser("task-create"); create.add_argument("--title", required=True)
    create.add_argument("--risk", required=True, choices=sorted(TIER_RANK))
    create.add_argument("--change-class", default="standard", choices=sorted(CHANGE_CLASS_RANK))
    create.add_argument("--scope", nargs="+", required=True)
    create.add_argument("--profile", default="focused", choices=["focused", "full", "release"])
    note = sub.add_parser("task-note"); note.add_argument("--message", required=True)
    note.add_argument("--session", default=None); note.add_argument("--task-file", action="append", default=[])
    state = sub.add_parser("task-state"); state.add_argument("--state", required=True)
    state.add_argument("--session", default=None); state.add_argument("--task-file", action="append", default=[])
    sub.add_parser("selfcheck"); tc = sub.add_parser("trifecta-check"); tc.add_argument("--session", default=None)
    a = ap.parse_args()
    if a.cmd == "scope-check":
        print(scope_check(a.path, a.session, a.task_file))
    elif a.cmd == "blob-check":
        print(blob_check(a.path))
    elif a.cmd == "gate-check":
        print(gate_check(a.gate, a.session, a.task_file))
    elif a.cmd == "tier-required":
        diff = open(a.diff_file, encoding="utf-8").read() if a.diff_file else ""
        print(tier_required(a.paths, diff))
    elif a.cmd == "change-class":
        diff = open(a.diff_file, encoding="utf-8").read() if a.diff_file else ""
        print(change_class(a.paths, diff))
    elif a.cmd == "task-risk":
        print(_max_task_risk(_task_context(a.task_file)))
    elif a.cmd == "task-change-class":
        print(_max_task_change(_task_context(a.task_file)))
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
        print(budget_tick(a.path, a.write, a.session, a.sig))
    elif a.cmd == "budget-reset":
        print(budget_reset(a.session))
    elif a.cmd == "budget-status":
        print(budget_status(a.session))
    elif a.cmd == "config-get":
        v = _dig(_load_config(), a.field)
        print("null" if v is None else (",".join(v) if isinstance(v, list) else v))
    elif a.cmd == "verify-plan":
        print(verify_plan(a.risk, a.change_class))
    elif a.cmd == "verify-run":
        out = verify_run(a.session, a.no_cache); print(out)
        sys.exit(0 if out.startswith(("pass", "no-build-configured")) else 1)
    elif a.cmd == "judge-record":
        print(judge_record(a.task, a.verdict, a.evidence, a.confidence))
    elif a.cmd == "bind":
        print(bind_session(a.session, a.task))
    elif a.cmd == "context":
        print(context_brief(a.session))
    elif a.cmd == "judge-brief":
        print(judge_brief(a.session, a.lens, a.task_file, a.range))
    elif a.cmd == "heartbeat":
        print(heartbeat_touch(a.session, a.task_file))
    elif a.cmd == "task-create":
        print(task_create(a.title, a.risk, a.change_class, a.scope, a.profile))
    elif a.cmd == "task-note":
        print(task_note(a.message, a.session, a.task_file))
    elif a.cmd == "task-state":
        print(task_state(a.state, a.session, a.task_file))
    elif a.cmd == "selfcheck":
        sys.exit(selfcheck())
    elif a.cmd == "trifecta-check":
        print(trifecta_check(a.session))
    elif a.cmd == "doctor":
        sys.exit(doctor())


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail CLOSED: callers treat error output as block, never as silent pass
        print("error:%s:%s" % (type(e).__name__, e))
        sys.exit(3)
