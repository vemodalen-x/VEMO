#!/usr/bin/env python3
"""eval/run.py — executable conformance runner for VEMO's own mechanisms.

Turns eval/ from prose scenarios into a RUNNABLE harness: it exercises the validator with controlled
fixtures in isolated sandboxes and asserts the gate outcomes the SC scenarios describe. Produces real
conformance metrics (no self-grading), written to eval/out/report.json. Run: python3 eval/run.py
"""
import os, sys, json, tempfile, shutil, subprocess, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAL = os.path.join(ROOT, "enforcement", "validators", "task_state.py")


def run(root, *args):
    env = dict(os.environ, VEMO_ROOT=root)
    return subprocess.run(["python3", VAL, *args], capture_output=True, text=True, env=env).stdout.strip()


def sandbox(tier=None, task=None):
    d = tempfile.mkdtemp(prefix="vemo_eval_")
    cfg = open(os.path.join(ROOT, "vemo.config.yaml")).read()
    if tier:
        cfg = re.sub(r'(?m)^(\s*tier:\s*)\w+', r'\1' + tier, cfg, count=1)
    open(os.path.join(d, "vemo.config.yaml"), "w").write(cfg)
    os.makedirs(os.path.join(d, "tasks"))
    if task:
        open(os.path.join(d, "tasks", "T.md"), "w").write(task)
    return d


def task(scope, state="ImplementationDone", risk="R1", status="not_run", build_exit="null", evidence="", trifecta="[]"):
    return (f"---\nid: T\nrisk: {risk}\nstate: {state}\nscope_in: {scope}\ntrifecta: {trifecta}\n"
            f"acceptance:\n  status: {status}\n  build_exit: {build_exit}\n  smoke_exit: 0\n  evidence: \"{evidence}\"\n"
            f"owning_chat: c\nheartbeat: 2026-06-16T20:00\n---\n")


CHECKS = []
def chk(name, got, want):
    ok = (want in got) if isinstance(want, str) else bool(want(got))
    CHECKS.append((name, ok, got))


def vnum(s):
    m = re.search(r"verifiers=(\d+)", s); return int(m.group(1)) if m else -1


# 1-2 scope containment
d = sandbox(task=task('["src/feature/**"]'))
chk("scope: in-scope allowed", run(d, "scope-check", "--path", d + "/src/feature/x.py"), "in-scope")
chk("scope: out-of-scope flagged", run(d, "scope-check", "--path", d + "/src/other/x.py"), "out-of-scope")
shutil.rmtree(d)
# 3-5 diff-derived risk tier
d = sandbox()
chk("tier: README->R0", run(d, "tier-required", "--paths", "README.md"), lambda g: g == "R0")
chk("tier: src/app->R1", run(d, "tier-required", "--paths", "src/app/x.ts"), lambda g: g == "R1")
chk("tier: src/core->R2", run(d, "tier-required", "--paths", "src/core/k.cpp"), lambda g: g == "R2")
shutil.rmtree(d)
# 6 capability-monotonic: verifiers scale UP with tier
dh, df = sandbox(tier="high"), sandbox(tier="frontier")
chk("monotonic: frontier verifiers > high", "", lambda _: vnum(run(df, "verify-plan", "--risk", "R2")) > vnum(run(dh, "verify-plan", "--risk", "R2")))
shutil.rmtree(dh); shutil.rmtree(df)
# 7-8 executed-ground-truth gate
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R2", status="passed"))
chk("exec-evidence: 'passed' w/o run trace BLOCKED", run(d, "gate-check", "--gate", "acceptance-before-push"), "executed-evidence-missing")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', state="AcceptancePassed", risk="R2", status="passed", build_exit="0", evidence=".vemo/run/1.log"))
chk("exec-evidence: 'passed' WITH run trace ok", run(d, "gate-check", "--gate", "acceptance-before-push"), lambda g: g == "ok")
shutil.rmtree(d)
# 9 safety is capability-invariant (config contract)
d = sandbox()
chk("safety_invariant_of_capability=true", run(d, "config-get", "--field", "enforcement.safety_invariant_of_capability"), lambda g: str(g).lower() == "true")
shutil.rmtree(d)

# 10-11 Rule of Two (lethal trifecta — OWASP ASI01)
d = sandbox(task=task('["src/**"]', trifecta='[private_data, untrusted_content, external_comms]'))
chk("rule-of-two: 3/3 trifecta BLOCKED", run(d, "trifecta-check"), "block:rule-of-two")
shutil.rmtree(d)
d = sandbox(task=task('["src/**"]', trifecta='[private_data, external_comms]'))
chk("rule-of-two: 2/3 allowed", run(d, "trifecta-check"), lambda g: g.startswith("ok"))
shutil.rmtree(d)

passed = sum(1 for _, ok, _ in CHECKS if ok); total = len(CHECKS)
rep = {"passed": passed, "total": total, "rate": round(passed / total, 3),
       "checks": [{"name": n, "pass": ok, "got": g} for n, ok, g in CHECKS]}
os.makedirs(os.path.join(ROOT, "eval", "out"), exist_ok=True)
json.dump(rep, open(os.path.join(ROOT, "eval", "out", "report.json"), "w"), indent=2)
for n, ok, _ in CHECKS:
    print(f"  [{'PASS' if ok else 'FAIL'}] {n}")
print(f"[eval] conformance {passed}/{total} = {int(rep['rate']*100)}%  -> eval/out/report.json")
sys.exit(0 if passed == total else 1)
