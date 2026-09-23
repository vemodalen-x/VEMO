# Plugins

Plugins keep non-essential product features out of the governance kernel. They are disabled by default and add
commands only after explicit enablement in `vemo.json`.

```bash
python3 bin/vemo plugin list
python3 bin/vemo plugin enable fleet
python3 bin/vemo --help
python3 bin/vemo plugin disable fleet
```

A plugin has one data-only manifest:

```json
{
  "version": 1,
  "name": "example",
  "commands": {
    "example-command": ["plugins/example/main.py", "fixed-argument"]
  }
}
```

Rules are intentionally small:

- plugins are never enabled implicitly;
- names and commands must be unique;
- entry paths must be safe, repository-relative existing files;
- plugins cannot modify core policy decisions;
- no dependency graph, lifecycle hooks, capability seams, or executable manifest expressions;
- plugin code is trusted and unsandboxed.

Bundled plugins expose a Fleet control plane, setup UI/service, skill tooling, optional review guides, and
automation commands. Their implementation files remain outside the default payload. The former
extension-composition subsystem was deleted rather than preserved: plugin discovery itself replaces it.

| Plugin | Commands | Purpose |
|---|---|---|
| `setup` | `setup`, `ui` | Transactional install, check, recover, uninstall, and local browser UI |
| `fleet` | `fleet`, `dashboard` | User-local multi-project governance control plane and read-only visual console |
| `review` | `judge-guide` | Independent-review guidance; no core policy authority |
| `skills` | `skill-score`, `skill-audit`, `skill-roster` | Optional skill catalog tooling |
| `automation` | `auto` | Legacy unattended-mode helper; review carefully before enabling |

Bundled does not mean supported by the core contract. Each plugin owns its compatibility and documentation;
disabled plugin code is not imported or validated during core startup.

See [CONTROL-PLANE.md](CONTROL-PLANE.md) for the machine-wide registry, single-project inspection model, local
dashboard, API, security boundaries, and cross-platform launch commands.

The two browser surfaces have different authority: setup UI writes only through a reviewed preview and matching
`plan_id`, while the Fleet dashboard has no write API. Fleet's registry defaults to `~/.vemo/projects.json` (or
`$VEMO_HOME/projects.json`) and can be used directly without enabling repository commands:

```bash
python3 plugins/fleet/main.py register /absolute/project --label ProjectName
python3 plugins/fleet/main.py status --json
python3 plugins/fleet/main.py serve
```
