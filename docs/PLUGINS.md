# Plugins

Plugins keep non-essential product features out of the governance kernel. They are disabled by default and add
commands only after explicit enablement in `vemo.json`.

```bash
python3 bin/vemo plugin list
python3 bin/vemo plugin enable product
python3 bin/vemo --help
python3 bin/vemo plugin disable product
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

Bundled plugins expose a product report/platform view, Fleet, setup UI/service, skill tooling, optional review
guides, and automation commands. Their implementation files remain outside the default payload. The former
extension-composition subsystem was deleted rather than preserved: plugin discovery itself replaces it.
