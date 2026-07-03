#!/usr/bin/env python3
"""eval/run.py — executable conformance runner for VEMO's own mechanisms.

Two layers, both real (no self-grading), written to eval/out/report.json:
  1. VALIDATOR conformance — exercises task_state.py with controlled fixtures in isolated sandboxes.
  2. HOOK end-to-end — pipes real PreToolUse/SessionStart payloads into enforcement/hooks/run.py and
     asserts the EXIT CODES (2=block, 0=allow). This is the layer that used to be untested — a validator
     that works but hooks that never fire is exactly the failure `vemo doctor`'s gates-heartbeat hunts.
Run: python3 eval/run.py
"""
import os, sys, json, tempfile, shutil, subprocess, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAL = os.path.join(ROOT, "enforcement", "validators", "task_state.py")
HOOK = os.path.join(ROOT, "enforcement", "hooks", "run.py")


def run(root, *args):
    env = dict(os.environ, VEMO_ROOT=root)
    return subprocess.run(["python3", VAL, *args], capture_output=True, text=True, env=env).stdout.strip()


def hook(root, guard, payload):
    """Feed a real hook payload to the dispatcher; return (exit_code, stderr)."""
    env = dict(os.environ, VEMO_ROOT=root)
    p = subprocess.run(["python3", HOOK, guard], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr.strip()


def sandbox(tier=None, task=None, cfg_sub=()):
    d = tempfile.mkdtemp(prefix="vemo_eval_")
    cfg = open(os.path.join(ROOT, "vemo.config.yaml")).read()
    # neutralize the host's paths.build/smoke (VEMO dogfoods eval as its own build): sandboxes must
    # not inherit a real build command — receipts are opted into per-check via cfg_sub on `build: ""`
    cfg = re.sub(r'(?m)^(\s*build:\s*).*$', r'\1""', cfg, count=1)
    cfg = re.sub(r'(?m)^(\s*smoke:\s*).*$', r'\1""', cfg, count=1)
    if tier:
        cfg = re.sub(r'(?m)^(\s*tier:\s*)\w+', r'\1' + tier, cfg, count=1)
    for pat, repl in cfg_sub:
        cfg = re.sub(pat, repl, cfg, count=1)
    open(os.path.join(d, "vemo.config.yaml"), "w").write(cfg)
    os.makedirs(os.path.join(d, "tasks"))
    os.makedirs(os.path.join(d, ".vemo"))
    if task:
        open(os.path.join(d, "tasks", "T.md"), "w").write(task)
    return d


def task(scope, state="ImplementationDone", risk="R1", status="not_run", build_exit="null",
         evidence="", trifecta="[]", verdict="null", approved="[]", task_id="T"):
    return (f"---\nid: {task_id}\nrisk: {risk}\nstate: {state}\nscope_in: {scope}\ntrifecta: {trifecta}\n"
            f"acceptance:\n  status: {status}\n  build_exit: {build_exit}\n  smoke_exit: 0\n  evidence: \"{evidence}\"\n"
            f"judge:\n  required: false\n  verdict: {verdict}\napproved_commands: {approved}\n"
            f"owning_chat: c\nheartbeat: 2026-06-16T20:00\n---\n")


CHECKS = []
def chk(name, got, want):
    ok = (want in got) if isinstance(want, str) else bool(want(got))
    CHECKS.append((name, ok, got))


SECRET_FIXTURE = 'api_' + 'key = "' + 'sk-' + '0123456789abcdef0123' + '"'


def vnum(s):
    m = re.search(r"verifiers=(\d+)", s); return int(m.group(1)) if m else -1


def edit_payload(path, content="x = 1\n"):
    return {"tool_name": "Edit", "session_id": "eval-s1", "tool_input": {"file_path": path, "new_string": content}}


def install_precommit_fixture(root):
    """Install just enough of the git backstop into a sandbox to exercise staged-diff checks."""
    os.makedirs(os.path.join(root, "enforcement", "validators"), exist_ok=True)
    os.makedirs(os.path.join(root, "enforcement", "ci"), exist_ok=True)
    shutil.copy2(VAL, os.path.join(root, "enforcement", "validators", "task_state.py"))
    shutil.copy2(os.path.join(ROOT, "enforcement", "ci", "pre-commit"),
                 os.path.join(root, "enforcement", "ci", "pre-commit"))
    subprocess.run(["git", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


# ═══ 1. VALIDATOR conformance ═══════════════════════════════════════════════
# scope containment
d = sandbox(task=task('["src/feature/**"]'))
chk("scope: in-scope allowed", run(d, "scope-check", "--path", d + "/src/feature/x.py"), "in-scope")
chk("scope: out-of-scope flagged", run(d, "scope-check", "--path", d + "/src/other/x.py"), "out-of-scope")
shutil.rmtree(d)

# diff-derived risk tier + fail-safe default + self-protection
d = sandbox()
chk("tier: README->R0", run(d, "tier-required", "--paths", "README.md"), lambda g: g == "R0")
chk("tier: src/app->R1", run(d, "tier-required", "--paths", "src/app/x.ts"), lambda g: g == "R1")
chk("tier: src/core->R2", run(d, "tier-required", "--paths", "src/core/k.cpp"), lambda g: g == "R2")
chk("tier: unmatched (Makefile) -> R1 fail-safe", run(d, "tier-required", "--paths", "Makefile"), lambda g: g == "R1")
chk("tier: enforcement/** is R2 (self-protection)", run(d, "tier-required", "--paths", "enforcement/hooks/run.py"), lambda g: g == "R2")
chk("tier: .claude/settings.json is R2 (self-protection)", run(d, "tier-required", "--paths", ".claude/settings.json"), lambda g: g == "R2")
chk("tier: vemo.config.yaml is R2 (self-protection)", run(d, "tier-required", "--paths", "vemo.config.yaml"), lambda g: g == "R2")
chk("tier: specs/** is R2 (self-protection)", run(d, "tier-required", "--paths", "specs/safety.spec.md"), lambda g: g == "R2")
shutil.rmtree(d)

# capability-monotonic: verifiers scale UP with tier
dh, df = sandbox(tier="high"), sandbox(tier="frontier")
chk("monotonic: frontier verifiers > high", "", lambda _: vnum(run(df, "verify-plan", "--risk", "R2")) > vnum(run(dh, "verify-plan", "--risk", "R2")))
shutil.rmtree(dh); shutil.rmtree(df)

# executed-ground-truth gate: claim without trace / with fake path / with real file
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed"))
chk("exec-evidence: 'passed' w/o run trace BLOCKED", run(d, "gate-check", "--gate", "acceptance-before-push"), "executed-evidence-missing")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed",
                      build_exit="0", evidence="totally/fake/nonexistent.log"))
chk("exec-evidence: FAKE evidence path BLOCKED", run(d, "gate-check", "--gate", "acceptance-before-push"), "evidence-file-missing")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed",
                      build_exit="0", evidence=".vemo/run/1.log"))
os.makedirs(os.path.join(d, ".vemo", "run")); open(os.path.join(d, ".vemo", "run", "1.log"), "w").write("$ true\n[exit 0]\n")
chk("exec-evidence: real evidence file ok", run(d, "gate-check", "--gate", "acceptance-before-push"), lambda g: g == "ok")
shutil.rmtree(d)

# R0 velocity path: no acceptance gate
d = sandbox(task=task('["docs/**"]', state="ImplementationDone", risk="R0"))
chk("R0: acceptance-before-push exempt", run(d, "gate-check", "--gate", "acceptance-before-push"), lambda g: g == "ok")
shutil.rmtree(d)

# verify-run receipt: the gate trusts the machine receipt, not typed numbers
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed",
                      build_exit="0", evidence=".vemo/run/1.log"),
            cfg_sub=[(r'(?m)^(\s*build:\s*)""', r'\1"true"')])
os.makedirs(os.path.join(d, ".vemo", "run")); open(os.path.join(d, ".vemo", "run", "1.log"), "w").write("x\n")
chk("receipt: build configured + NO receipt -> BLOCKED", run(d, "gate-check", "--gate", "acceptance-before-push"), "no-verify-receipt")
chk("receipt: verify-run executes and passes", run(d, "verify-run"), lambda g: g.startswith("pass"))
chk("receipt: gate ok after verify-run", run(d, "gate-check", "--gate", "acceptance-before-push"), lambda g: g == "ok")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed",
                      build_exit="0", evidence=".vemo/run/1.log"),
            cfg_sub=[(r'(?m)^(\s*build:\s*)""', r'\1"false"')])   # build command that FAILS
os.makedirs(os.path.join(d, ".vemo", "run")); open(os.path.join(d, ".vemo", "run", "1.log"), "w").write("x\n")
run(d, "verify-run")
chk("receipt: failing build -> receipt-failed BLOCKED", run(d, "gate-check", "--gate", "acceptance-before-push"), "receipt-failed")
shutil.rmtree(d)

# CI must create the verify-run receipt before the push gate checks it.
for wf in ("enforcement/ci/vemo-ci.yml", ".github/workflows/vemo-ci.yml"):
    txt = open(os.path.join(ROOT, wf), encoding="utf-8").read()
    chk(f"ci workflow: verify-run before pre-push ({wf})", txt,
        lambda g: "verify-run" in g and "bash enforcement/ci/pre-push" in g
        and g.index("verify-run") < g.index("bash enforcement/ci/pre-push"))

# judge provenance: a verdict pasted into front-matter alone does not open the gate
d = sandbox(task=task('["src/**"]', risk="R2", verdict="pass"))
chk("judge: front-matter pass w/o provenance BLOCKED", run(d, "gate-check", "--gate", "r2-judge"), "judge-no-provenance")
run(d, "judge-record", "--task", "T", "--verdict", "pass", "--evidence", "e2e")
chk("judge: high-tier R2 one pass still BLOCKED", run(d, "gate-check", "--gate", "required-judge"), "judge-pass-count=1")
run(d, "judge-record", "--task", "T", "--verdict", "pass", "--evidence", "e2e-2")
chk("judge: high-tier R2 required pass count ok", run(d, "gate-check", "--gate", "required-judge"), lambda g: g == "ok")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', risk="R2", verdict="pass"))
run(d, "judge-record", "--task", "T", "--verdict", "fail")
chk("judge: provenance says FAIL, front-matter says pass -> BLOCKED", run(d, "gate-check", "--gate", "r2-judge"), "judge-provenance-mismatch")
shutil.rmtree(d)
d = sandbox(tier="low", task=task('["src/**"]', risk="R1", verdict="pass"))
chk("judge: low-tier R1 requires provenance", run(d, "gate-check", "--gate", "required-judge"), "judge-no-provenance")
run(d, "judge-record", "--task", "T", "--verdict", "pass", "--evidence", "low-r1")
chk("judge: low-tier R1 one pass ok", run(d, "gate-check", "--gate", "required-judge"), lambda g: g == "ok")
shutil.rmtree(d)
d = sandbox(tier="high", task=task('["src/**"]', risk="R1", verdict="null"))
chk("judge: high-tier R1 self-verifies (no judge required)", run(d, "gate-check", "--gate", "required-judge"), lambda g: g == "ok")
shutil.rmtree(d)

# inline-map front-matter (the task.spec §2 example style) parses
d = sandbox(task=("---\nid: T\nrisk: R1\nstate: ImplementationDone\nscope_in: [\"src/**\"]\n"
                  "acceptance: { status: passed, build_exit: 0, smoke_exit: 0, evidence: \".vemo/run/1.log\" }\n"
                  "judge: { required: false, verdict: null }\nowning_chat: c\nheartbeat: 2026-06-16T20:00\n---\n"))
chk("parser: inline-map acceptance parses (spec example)", run(d, "get", "--field", "acceptance.status"), lambda g: g == "passed")
chk("parser: inline-map gate-check does not crash", run(d, "gate-check", "--gate", "acceptance-before-push"), "block:")
shutil.rmtree(d)

# session binding: a bound session is checked against ITS task, not freshest-heartbeat
d = sandbox(task=task('["src/a/**"]', task_id="TA"))
open(os.path.join(d, "tasks", "T2.md"), "w").write(
    task('["src/b/**"]', task_id="TB").replace("heartbeat: 2026-06-16T20:00", "heartbeat: 2026-06-17T09:00"))
chk("bind: unbound falls back to freshest heartbeat (TB)", run(d, "scope-check", "--path", d + "/src/b/x.py"), "in-scope")
run(d, "bind", "--session", "s-A", "--task", "TA")
chk("bind: bound session checked against ITS OWN task", run(d, "scope-check", "--path", d + "/src/a/x.py", "--session", "s-A"), "in-scope")
chk("bind: bound session out-of-scope on the other task's area", run(d, "scope-check", "--path", d + "/src/b/x.py", "--session", "s-A"), "out-of-scope")
shutil.rmtree(d)

# safety flags + Rule of Two
d = sandbox()
chk("safety_invariant_of_capability=true", run(d, "config-get", "--field", "enforcement.safety_invariant_of_capability"), lambda g: str(g).lower() == "true")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', trifecta='[private_data, untrusted_content, external_comms]'))
chk("rule-of-two: 3/3 trifecta BLOCKED", run(d, "trifecta-check"), "block:rule-of-two")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', trifecta='[private_data, external_comms]'))
chk("rule-of-two: 2/3 allowed", run(d, "trifecta-check"), lambda g: g.startswith("ok"))
shutil.rmtree(d)

# ═══ 2. HOOK end-to-end (payload -> dispatcher -> exit code) ═══════════════
d = sandbox(task=task('["src/feature/**"]'))
rc, err = hook(d, "edit", edit_payload(d + "/src/feature/x.py"))
chk("hook e2e: in-scope edit exit 0", "", lambda _: rc == 0)
rc, err = hook(d, "edit", edit_payload(d + "/src/other/x.py"))
chk("hook e2e: out-of-scope edit exit 2 + reason", "", lambda _: rc == 2 and "safety.spec#1" in err)
rc, err = hook(d, "edit", edit_payload(d + "/src/feature/model.onnx"))
chk("hook e2e: binary blob exit 2 (safety#6)", "", lambda _: rc == 2 and "safety.spec#6" in err)
rc, err = hook(d, "edit", edit_payload(d + "/src/feature/cfg.py", SECRET_FIXTURE))
chk("hook e2e: secret content exit 2 (safety#5)", "", lambda _: rc == 2 and "safety.spec#5" in err)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~3"}})
chk("hook e2e: destructive command exit 2 (safety#4)", "", lambda _: rc == 2 and "safety.spec#4" in err)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
chk("hook e2e: benign command exit 0", "", lambda _: rc == 0)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "echo pwned >> ~/.bashrc"}})
chk("hook e2e: out-of-repo write exit 2", "", lambda _: rc == 2 and "outside repo_root" in err)
# git-gate evasion / tamper (safety#4): the agent must not bypass or redirect VEMO's own git ring
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "git commit -m wip --no-verify"}})
chk("hook e2e: git --no-verify gate evasion exit 2", "", lambda _: rc == 2 and "no-verify" in err)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "echo ok > .git/hooks/pre-push"}})
chk("hook e2e: write into .git/ (hook tamper) exit 2", "", lambda _: rc == 2 and "git-gate tamper" in err)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "git config core.hooksPath /tmp/nohooks"}})
chk("hook e2e: core.hooksPath redirect exit 2", "", lambda _: rc == 2 and "hooksPath" in err)
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "ls -la .git/hooks"}})
chk("hook e2e: reading .git/hooks allowed (no false positive)", "", lambda _: rc == 0)
# harness-neutral adapter contract (docs/ADAPTERS.md): a minimal payload from a NON-Claude harness —
# no session_id, unknown extra fields — must be guarded identically, not crash or fail open
rc, err = hook(d, "edit", {"tool_name": "Write", "tool_input": {"file_path": d + "/src/feature/ok.py"}, "harness": "generic"})
chk("hook e2e: foreign minimal payload in-scope exit 0", "", lambda _: rc == 0)
rc, err = hook(d, "edit", {"tool_name": "Write", "tool_input": {"file_path": d + "/src/other/no.py"}, "harness": "generic"})
chk("hook e2e: foreign minimal payload out-of-scope exit 2", "", lambda _: rc == 2 and "safety.spec#1" in err)
rc, err = hook(d, "session-start", {"session_id": "eval-s1"})
chk("hook e2e: session-start exit 0 + orientation", "", lambda _: rc == 0)
tele = open(os.path.join(d, ".vemo", "telemetry.jsonl")).read()
chk("hook e2e: telemetry recorded blocks + session_start", "", lambda _: "scope_block_out" in tele and "session_start" in tele)
shutil.rmtree(d)

# pre-commit secret scan must not miss matches because of grep -q + pipefail SIGPIPE behavior
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R1", status="passed",
                      build_exit="0", evidence=".vemo/run/1.log"))
os.makedirs(os.path.join(d, ".vemo", "run")); open(os.path.join(d, ".vemo", "run", "1.log"), "w").write("ok\n")
install_precommit_fixture(d)
os.makedirs(os.path.join(d, "src")); open(os.path.join(d, "src", "secret.py"), "w").write(SECRET_FIXTURE + "\n")
subprocess.run(["git", "add", "src/secret.py"], cwd=d, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
p = subprocess.run(["bash", "enforcement/ci/pre-commit"], cwd=d, capture_output=True, text=True)
chk("pre-commit e2e: staged secret exits 1 + reason", p.stdout + p.stderr,
    lambda g: p.returncode == 1 and "secret-scan" in g)
shutil.rmtree(d)

# approved_commands escape hatch (user-approved destructive cmd in the task file)
d = sandbox(task=task('["src/**"]', approved='["git reset --hard HEAD~1"]'))
rc, err = hook(d, "command", {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~1"}})
chk("hook e2e: task-approved destructive cmd allowed + logged", "", lambda _: rc == 0)
shutil.rmtree(d)

# stop + subagent-stop guards: advisory (exit 0) but must FIRE and leave a telemetry trail
d = sandbox(task=task('["src/**"]'))   # ImplementationDone R1 -> below AcceptancePassed
rc, err = hook(d, "stop", {"session_id": "eval-s1"})
chk("hook e2e: Stop below acceptance -> exit 0 + reminder", "", lambda _: rc == 0 and "not yet push-ready" in err)
rc2, _ = hook(d, "subagent-stop", {"session_id": "eval-s1"})
tele = open(os.path.join(d, ".vemo", "telemetry.jsonl")).read()
chk("hook e2e: Stop/SubagentStop telemetry recorded", "",
    lambda _: rc2 == 0 and "stop_below_acceptance" in tele and "subagent_stop" in tele)
shutil.rmtree(d)

# monitor mode: observed, not blocked — honored by the dispatcher (used to be honored nowhere on the bash path)
d = sandbox(task=task('["src/feature/**"]'), cfg_sub=[(r'(?m)^(\s*mode:\s*)enforce', r'\1monitor')])
rc, err = hook(d, "edit", edit_payload(d + "/src/other/x.py"))
chk("hook e2e: monitor mode logs but does NOT block", "", lambda _: rc == 0 and "monitor mode" in err)
shutil.rmtree(d)

# budget stop rule: hard only when unattended (auto ON)
d = sandbox(task=task('["src/**"]'))
json.dump({"enabled": True, "max_auto_tier": "R1"}, open(os.path.join(d, ".vemo", "auto_mode.json"), "w"))
json.dump({"started": "2026-06-16T20:00", "tool_calls": 9999, "files": []}, open(os.path.join(d, ".vemo", "run.json"), "w"))
rc, err = hook(d, "budget", {"tool_name": "Read", "tool_input": {"file_path": d + "/src/x.py"}})
chk("hook e2e: budget exceeded + auto ON -> hard stop exit 2", "", lambda _: rc == 2 and "STOP RULE" in err)
json.dump({"enabled": False}, open(os.path.join(d, ".vemo", "auto_mode.json"), "w"))
rc, err = hook(d, "budget", {"tool_name": "Read", "tool_input": {"file_path": d + "/src/x.py"}})
chk("hook e2e: budget exceeded + human present -> advisory exit 0", "", lambda _: rc == 0 and "advisory" in err)
shutil.rmtree(d)

# budget counts only WRITE-touched files (reading is not touching)
d = sandbox(task=task('["src/**"]'))
hook(d, "budget", {"tool_name": "Read", "tool_input": {"file_path": d + "/src/r.py"}, "session_id": "s9"})
hook(d, "budget", {"tool_name": "Edit", "tool_input": {"file_path": d + "/src/w.py"}, "session_id": "s9"})
st = run(d, "budget-status", "--session", "s9")
chk("budget: files counts writes only (1, not 2)", st, lambda g: "files=1/" in g)
shutil.rmtree(d)

# auto-mode enable is human-only: no TTY -> refuse
p = subprocess.run(["python3", os.path.join(ROOT, "enforcement", "automation", "vemo-auto"), "on"],
                   input="", capture_output=True, text=True, env=dict(os.environ, VEMO_ROOT=tempfile.mkdtemp(prefix="vemo_eval_")))
chk("auto: enable w/o TTY REFUSED (agent cannot self-enable)", p.stdout, "REFUSED")

passed = sum(1 for _, ok, _ in CHECKS if ok); total = len(CHECKS)
rep = {"passed": passed, "total": total, "rate": round(passed / total, 3),
       "checks": [{"name": n, "pass": ok, "got": (g if isinstance(g, str) else "")[:200]} for n, ok, g in CHECKS]}
os.makedirs(os.path.join(ROOT, "eval", "out"), exist_ok=True)
json.dump(rep, open(os.path.join(ROOT, "eval", "out", "report.json"), "w"), indent=2)
for n, ok, _ in CHECKS:
    print(f"  [{'PASS' if ok else 'FAIL'}] {n}")
print(f"[eval] conformance {passed}/{total} = {int(rep['rate']*100)}%  -> eval/out/report.json")
sys.exit(0 if passed == total else 1)
