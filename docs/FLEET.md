# VEMO Fleet

VEMO Fleet is a private, user-local control plane for governing multiple Git projects on one PC. It inventories
projects, evaluates them against progressive policy profiles, and distributes VEMO-owned files without silently
overwriting project-owned work.

## Operating model

| Layer | Responsibility | Authority |
|---|---|---|
| Fleet control plane | registry, discovery, profiles, readiness reports, managed-file updates | local advisory and orchestration |
| Project execution plane | scope gates, task lifecycle, verification receipts, judge evidence | local hooks and Git gates |
| Repository authority | required CI, branch protection, review, release provenance | server-side source/build platform |

The local registry and audit log live under `%USERPROFILE%\.vemo` on Windows or `~/.vemo` on POSIX. Set
`VEMO_HOME` to relocate them. They may contain private project paths, are never committed by VEMO, and are written
with user-only permissions where the operating system supports POSIX modes.

## Install once

Preview the user-local launcher before writing it:

```powershell
python bin\vemo fleet install
python bin\vemo fleet install --apply
```

The apply command writes `vemo.cmd`, a POSIX `vemo` launcher, and `config.json` under `VEMO_HOME`. It does not edit
the machine PATH. Add the printed `bin` directory to PATH once, or invoke `vemo.cmd` directly.

Windows PowerShell 5 reads UTF-8 JSON with the system code page unless encoding is explicit. Use
`Get-Content -Raw -Encoding UTF8 "$env:USERPROFILE\.vemo\fleet.json"` for direct inspection; the VEMO CLI and Python
read the registry as UTF-8 automatically.

## Inventory projects

Discovery is always read-only and does not imply adoption:

```powershell
vemo fleet discover C:\Users\User\Documents --max-depth 6
vemo fleet register C:\work\product-a --profile solo
vemo fleet register C:\work\shared-service --profile team
vemo fleet status
vemo fleet status --json
vemo fleet status --strict
```

`status --json` is the stable machine-readable reporting surface. `--strict` exits non-zero when any registered
project misses a required profile control, making it suitable for scheduled local checks without changing projects.

## Adopt or update a project

Onboarding is preview-first:

```powershell
vemo fleet onboard C:\work\product-a --profile solo
vemo fleet onboard C:\work\product-a --profile solo --apply
vemo fleet onboard C:\work\product-a --profile solo --skills-root C:\frameworks\VEMO_SKILLS
```

Apply is refused when the target worktree is dirty or a VEMO-managed path contains project-owned content. On a
successful apply, Fleet records SHA-256 hashes for the managed files. A later update may replace a file only when its
current hash still equals the last Fleet-managed hash; local customization becomes a conflict that requires review.
Fleet does not install project Git hooks during this step. Run the target project's `vemo init --preset <stack>` after
reviewing and committing the adoption change.

Passing `--skills-root` is an explicit skill-adoption request. Fleet regenerates each registered source skill into
`.claude/skills/<name>/`, excludes local validation markers, and applies the same dry-run, dirty-worktree, managed-hash,
and project-owned conflict rules. Omit the option when the project should receive the framework without shared skills.

## Profiles

| Profile | Intended use | Required posture |
|---|---|---|
| `solo` | personal, prototype, local utility | repository memory, scope containment, secret gate |
| `team` | shared product or service | solo + hooks, authoritative CI, contribution/security policy, judge provenance |
| `regulated` | higher-assurance evidence needs | team + ownership, dependency automation, receipts, telemetry, release provenance |

Profiles are progressive adoption targets, not legal advice or certifications. A project can start with `solo`, close
the reported gaps, and move to `team` or `regulated` by explicitly updating its registry profile.

## Auditability

Mutating Fleet actions append privacy-minimized events to `fleet-audit.jsonl`. Events contain project ids rather than
project paths and form a SHA-256 hash chain:

```powershell
vemo fleet audit --limit 50
vemo fleet audit --verify
vemo fleet audit --repair          # preview only
vemo fleet audit --repair --apply  # preserve invalid log, then start a recovery chain
```

The chain detects local modification; it is not a cryptographic signature and does not protect against deletion by an
account that controls `VEMO_HOME`. Export or forward events to an independently controlled log system when stronger
retention guarantees are required.

Repair never deletes or rewrites an invalid chain. It renames the original log with an `invalid-<UTC>` suffix and
records its SHA-256 plus the first failing line in the new chain's recovery event.

Registry, audit, and per-project apply operations use cross-process local locks. Concurrent agent sessions serialize
their mutations; lock timeout is reported as an error, and locks left by a crashed process expire after five minutes.

## Boundaries

- Fleet does not auto-register discovered projects, auto-enable unattended mode, change branch protection, or claim
  that local checks are server-side guarantees.
- Fleet does not collect source code, prompts, secrets, command arguments, or project paths in audit events.
- Fleet readiness reflects configured checks at assessment time. It does not prove absence of vulnerabilities.
- Remote policy enforcement, SSO/RBAC, signed profile distribution, and centralized telemetry are enterprise control
  plane extensions, not hidden behavior in the local edition.
