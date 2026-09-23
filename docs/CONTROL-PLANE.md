# Local governance control plane

VEMO separates enforcement from aggregation. Every repository owns and enforces its Policy, Task, Gate, Verify,
and Evidence contract. The optional Fleet plugin observes many repositories and presents their state; it does not
become a second policy engine.

## Architecture

```text
                         user-local control plane
  explicit roots         ~/.vemo/projects.json          loopback browser
  ┌─────────────┐       ┌──────────────────────┐       ┌──────────────────┐
  │ fleet       │──────▶│ registered projects  │──────▶│ overview         │
  │ discover    │       │ + hash-chained audit │       │ project details  │
  └─────────────┘       └──────────┬───────────┘       └─────────▲────────┘
                                   │ fixed read-only probes        │ JSON API
            ┌──────────────────────┼──────────────────────┐        │
            ▼                      ▼                      ▼        │
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
  │ repository A     │  │ repository B     │  │ repository C     ││
  │ policy/task      │  │ policy/task      │  │ not yet managed  ││
  │ gate/evidence    │  │ gate/evidence    │  │ install status   ││
  └──────────────────┘  └──────────────────┘  └──────────────────┘│
```

The data plane remains inside each repository. The control plane reads JSON contracts and evidence with this
trusted VEMO checkout's evaluator and invokes only fixed, non-mutating Git commands. It never imports target
repository Python, runs target verification commands, inherits target approval variables, or writes target files.

## Global and project responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| Repository core | authorization, action/merge decisions, verification execution, snapshot-bound evidence | machine-wide inventory or UI |
| Local control plane | discovery, explicit registry, health aggregation, local audit, visualization | policy decisions, approvals, installation, remote branch protection |
| Setup plugin | previewed install, upgrade, recovery, uninstall | continuous monitoring or governance decisions |
| Protected CI | authoritative merge gate and protected approval injection | local inventory |

This boundary prevents a broken dashboard from weakening a repository gate. A repository continues to work when
the control plane is stopped, and removing a registry entry never changes that repository.

## Data model

The private registry defaults to `~/.vemo/projects.json` or `$VEMO_HOME/projects.json`:

```json
{
  "schema_version": 1,
  "projects": [
    {
      "id": "stable-path-hash",
      "label": "project name",
      "path": "/absolute/project",
      "registered_at": "RFC3339",
      "updated_at": "RFC3339"
    }
  ]
}
```

Registry mutations append to `control-audit.jsonl`, linked by SHA-256 hashes. This audit proves local registry
history only; it is not a substitute for repository evidence or Git history.

## Operating flow

1. Discover candidate Git repositories below explicit roots. Discovery neither registers nor modifies them.
2. Register the projects that belong in the governance fleet.
3. Run `status` for machine-readable aggregation or `serve` for the browser console.
4. Select a project to inspect task authorization, current fail-closed gate result, Git state, adapters, policy
   summary, and verification evidence.
5. Use the setup plugin separately for any change. The console intentionally has no install or approval button.

## Commands

Enable the optional plugin in the VEMO source repository:

```bash
python3 bin/vemo plugin enable fleet
```

Or run its entry point directly without changing core policy:

```bash
python3 plugins/fleet/main.py discover /home/aimer/Project --max-depth 4 --json
python3 plugins/fleet/main.py register /home/aimer/Project/VEMO --label VEMO
python3 plugins/fleet/main.py status --json
python3 plugins/fleet/main.py inspect /home/aimer/Project/VEMO --json
python3 plugins/fleet/main.py serve
```

With the plugin enabled, the equivalent commands are `python3 bin/vemo fleet ...` and
`python3 bin/vemo dashboard`. macOS can launch `plugins/fleet/ui/start.command`; Windows can launch
`plugins\fleet\ui\start.cmd`.

## Visual console

The server listens only on `127.0.0.1`, chooses a free port by default, and serves three local assets with no CDN,
font download, cookies, or remote telemetry. The browser calls:

- `GET /api/health` — service and local audit health;
- `GET /api/overview` — aggregate counts and compact project rows;
- `GET /api/project?id=<id-or-path>` — one project's detailed controls and recent evidence.

The interface is responsive, keyboard accessible, printable, and remains understandable without decorative SVG.
It refreshes every 30 seconds; no background daemon is installed.

## Status semantics

- `ready`: required files exist and the repository gate currently returns `allow` without approval injection.
- `attention`: VEMO is installed but a control is missing, evidence is stale/missing, or the gate is fail-closed.
- `unmanaged`: the registered Git project has no `vemo.json`.
- `unavailable`: the registered path no longer exists.

The health score is an operational summary, not an authorization decision. Only the repository Gate can return
`allow`, `deny`, or `approval_required`.

## Security and privacy boundaries

- Discovery follows no symlink and scans only roots explicitly supplied on the command line.
- Registration changes only the private user-local registry; unregister never edits a project.
- Observation strips `VEMO_APPROVED_*` variables before evaluating a project, so the dashboard cannot display a
  transient approval as durable compliance.
- Target code, hooks, and verification commands are never executed.
- The console has read-only GET endpoints, loopback binding, a restrictive content security policy, and no write API.
- Filesystem permissions protect the registry. Multi-user or remote service deployment is intentionally unsupported.
