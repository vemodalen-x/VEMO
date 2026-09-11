# Security & threat model

VEMO is a governance layer for AI coding agents. It is honest about what it does and does not defend.

## What VEMO defends against (and how)
| Threat | Control |
|---|---|
| Agent edits files outside its task | edit guard (hook, session-bound) + git pre-commit + CI (authoritative) |
| Shell-write scope bypass (`>` / `tee` / `sed -i`) | hook warns (blacklists can't contain an open command space — honestly labeled); **contained at commit/CI**, where the diff shows every write |
| Destructive / out-of-repo command | command guard (hook): `rm -rf`, `git reset --hard`, `git clean -f`, plain `--force` push, `find -delete`, out-of-repo redirects, privilege escalation, pipe-to-shell. Escape hatch = user-approved `approved_commands:` in the task file |
| Git-gate evasion / tamper | command guard (hook) blocks `--no-verify` on commit/push/merge, `core.hooksPath` redirection, and writes into `.git/`; CI re-runs the same gates server-side regardless |
| Hand-editing binaries / model weights | blob guard (hook); vendor drops under `exclusions.third_party` exempt |
| Secret committed | edit guard (hook) + pre-commit/CI diff scan |
| "Verified" without running it | acceptance gate requires an evidence file that **exists**, and — when `paths.build/smoke` are configured — the machine receipt written by `vemo verify` (the gate executes the build; typed exit codes do not count) |
| Forged, altered, or under-counted judge verdict | `judge.verdict` in front-matter must match the judge's own `judge-record` entries. New rows form a schema-v1 SHA-256 chain anchored to the exact historical legacy prefix; malformed links and diff-visible deletion/reordering block `selfcheck` and the judge gate. A pasted `pass`, later `fail`, or too few content-bound passes also blocks. The ledger is tracked so CI can verify it |
| Self-classifying a risky change as trivial | diff-derived risk tier at pre-commit/CI blocks a downgrade; unmatched paths default **R1**, the governance layer itself is **R2** |
| Agent removes its own oversight | `vemo auto on` refuses without an interactive TTY + typed human confirmation; the skill exposes status/off only; `off` (restoring oversight) is always allowed |
| Runaway unattended run | `run_budget` hard-stop when auto mode is ON (write-touched files counted, per-session counters) |
| Silently disabling governance | `enforcement/**`, `.claude/**`, `.github/**`, `vemo.config*.yaml`, `specs/**` are R2 (review + capability-scaled judge depth to change); `selfcheck` (run in CI) flags deregistered hooks and `ENFORCED-BY` labels pointing at missing mechanisms |

## Tamper-evidence (the "can the agent disable the hooks?" question)
- **Server-side CI is the authority** (`enforcement/ci/vemo-ci.yml` + branch protection): it re-runs the same
  validator on the pushed/PR range, so `--no-verify` and a tampered client change nothing on a protected main.
  Local hooks + git gates are fast feedback for it. **Without branch protection, CI is advisory — set it.**
- `vemo selfcheck` detects hooks removed from `.claude/settings.json` and label/mechanism drift; CI runs it.
- Changing the framework files themselves takes the R2 path (human review + judge) by default tiering.

## Honest limits (what VEMO does NOT promise)
- A fully adversarial host that runs neither the client hooks nor the CI can bypass everything — VEMO is a
  cooperative-host control surface, not a sandbox. Pair it with real OS/container isolation for untrusted code.
- The session-start bootstrap ("the agent chooses to read config") is irreducibly prose — enforcement shrinks
  the trust surface but cannot remove that first step.
- Locally, an agent with shell access could in principle fabricate the receipt/provenance files too — they
  raise the bar from "type a number" to "actively forge an audit artifact" (visible in the diff/telemetry).
  The layer that cannot be forged from the client is CI, which re-executes build/smoke itself.
- Hash linking detects mutation/reordering and, through Git/CI range inspection, deletion in a proposed change;
  it is tamper-evidence, not an external timestamp/signature or immutable off-repository retention service.
- The command blacklist and secret regexes are best-effort pattern matching, not a sandbox or a scanner.
- `trifecta:` (Rule of Two) is self-declared; it bounds honest mistakes, not a determined injection —
  deriving it from observed tool usage is ROADMAP.
- The takeover protocol is convention + audit trail; git cannot verify "the committing session" (see
  `concurrency.spec §3`).
- VEMO provides controls + an audit trail; it is not a certification of legal/regulatory compliance.

## Reporting
Open a private security advisory (or issue, if low-severity) with: what you ran, expected vs actual, and
`vemo doctor` / `vemo selfcheck` output. Do not include secrets in the report.
