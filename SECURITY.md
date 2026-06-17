# Security & threat model

VEMO is a governance layer for AI coding agents. It is honest about what it does and does not defend.

## What VEMO defends against (and how)
| Threat | Control |
|---|---|
| Agent edits files outside its task | scope guard (hook) + git pre-commit/CI (authoritative) |
| Destructive / out-of-repo command | command guard (hook) — `rm -rf`, `git reset --hard`, privilege escalation, pipe-to-shell |
| Secret committed | secret guard (hook) + CI diff scan |
| "Verified" without running it | executed-ground-truth gate — `passed` acceptance needs exit codes + a log |
| Self-classifying a risky change as trivial | diff-derived risk tier in CI blocks a downgrade |
| Skipping the independent check on critical work | R2 requires `judge.verdict == pass` (separate context) |
| Runaway unattended run | `run_budget` hard-stop when auto mode is ON |
| Silently disabling governance | `selfcheck` flags hooks removed from settings; CI is the authority |

## Tamper-evidence (the "can the agent disable the hooks?" question)
- **CI / git pre-commit is the authority**, not the client hooks. It survives `git commit --no-verify` (run it
  server-side / in CI), so disabling the *client* hooks does not let an unverified change reach the protected branch.
- `vemo selfcheck` detects hooks removed from `.claude/settings.json`.
- The framework files (`enforcement/`, `specs/`) are template-owned; treat edits to them as a separate,
  reviewed task — and (GitHub best practice) protect CI/workflow files from agent edits.

## Honest limits (what VEMO does NOT promise)
- A fully adversarial host that runs neither the client hooks nor the CI can bypass everything — VEMO is a
  cooperative-host control surface, not a sandbox. Pair it with real OS/container isolation for untrusted code.
- The session-start bootstrap ("the agent chooses to read config") is irreducibly prose — enforcement shrinks
  the trust surface but cannot remove that first step.
- Client hooks are best-effort/fast-feedback; the *guarantee* lives in CI.
- VEMO provides controls + an audit trail; it is not a certification of legal/regulatory compliance.

## Reporting
Open a private security advisory (or issue, if low-severity) with: what you ran, expected vs actual, and
`vemo doctor` / `vemo selfcheck` output. Do not include secrets in the report.
