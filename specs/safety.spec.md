# safety.spec — Non-negotiables (MECHANICALLY ENFORCED)

> Every rule here is tagged with **who enforces it** — a hook or CI, not the model's goodwill.
> "Hooks execute deterministic code. They cannot hallucinate." This is the only spec loaded at every session
> start, and it is the shortest.

## Enforcement legend
- `ENFORCED-BY: hook` — blocked client-side in the agent loop (fast feedback).
- `ENFORCED-BY: ci` — blocked server-side / pre-commit (authoritative; survives `--no-verify` only if CI is the gate).
- `ENFORCED-BY: hook+ci` — defense in depth (both).

## The list

1. **Scope containment.** No create/edit/delete outside the active task's `scope_in` globs.
   `ENFORCED-BY: hook+ci` → `enforcement/hooks/guard-scope.sh`, `enforcement/ci/pre-commit`.
   Rationale: out-of-scope edits are the most common way agents cause collateral damage.

2. **Plan-before-commit.** No commit touching code unless a task file with a matching plan + `scope_in` exists and is `PlanCreated`+.
   `ENFORCED-BY: ci` → `enforcement/ci/pre-commit` (reads task front-matter via `validators/task_state.py`).

3. **Acceptance-before-push.** No push of a code task whose task state is below `AcceptancePassed`.
   `ENFORCED-BY: ci` → blocks on `state` / `acceptance.status` mismatch.

4. **No destructive / out-of-repo commands** without explicit same-session user approval:
   `rm -rf` on broad paths, `git reset --hard`, `git checkout -- <file>`, writes outside `repo_root`, privilege escalation, network install of unknown binaries.
   `ENFORCED-BY: hook` → `enforcement/hooks/guard-command.sh` (PreToolUse on Bash).

5. **No secrets in a diff.** Staged changes are scanned for credential/key patterns.
   `ENFORCED-BY: hook+ci` → `enforcement/hooks/guard-secret.sh`.

6. **No editing generated binaries / model blobs** (`*.a *.lib *.dll *.exe *.bin` model weights).
   `ENFORCED-BY: hook`.

## When a gate fires
- The action is refused with a one-line reason + the rule id. The agent must address the **cause**, not retry verbatim, and must not attempt to disable the hook.
- Disabling/bypassing enforcement is itself a blocked action (`ENFORCED-BY: ci` checks the hook/CI config is intact).

## Graceful degradation
If `enforcement.degrade_gracefully: true` and a validator/tool is missing, the gate **warns loudly and logs**
to telemetry rather than silently passing — a missing guard is surfaced, never assumed safe.

## Guardrail elements & rollout (v1.7)
The rules above are the **Permission** + **Audit** elements; the other two canonical guardrail elements:
- **Approval** — human-in-loop gates (plan/review by risk tier; the human owns intent + irreversible). See `task.spec` / `capability.spec`.
- **Kill switch** — `vemo auto off`, `run_budget` hard-stop (unattended), and `enforcement.mode: monitor` (observe-only).

**Action-chaining:** a low-risk action (e.g. a read) chained into a high-risk one (exec / push / destructive)
does not escape these guards — each action is checked, and the high-risk step still hits its risk-tier gate + the judge.

**Monitoring mode:** `enforcement.mode: monitor` logs violations without blocking (for onboarding/tuning); flip
to `enforce` once calibrated. Safety-critical guards always *log* either way — you get the audit trail first.

## Why so short
Non-negotiables you can enforce are few. Everything else is advice and belongs in the domain specs,
loaded on demand. A long safety spec is a smell: if it can't be a hook, it isn't really "hard".
