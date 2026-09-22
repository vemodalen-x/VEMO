# VEMO installation guide

## Requirements

- Python 3.10 or newer
- Git
- Bash 4 or newer for Git hooks
- A protected branch and required CI check for authoritative server-side enforcement

VEMO has no runtime dependency outside the Python standard library. It is not an OS sandbox; use a container or
another isolation boundary when executing untrusted code.

## Install the core in the current repository

```bash
python3 bin/vemo init
python3 bin/vemo check --self
```

This creates the evidence directory, installs local Git adapters and Claude `PreToolUse` hooks, and checks the
core contract. Create or edit the explicit task authorization, then follow [USAGE.md](USAGE.md).

## Install into another repository

Do not copy files manually. Use the optional transactional setup plugin:

```bash
python3 plugins/setup/entry.py setup install /absolute/project --json
# inspect the JSON plan
python3 plugins/setup/entry.py setup install /absolute/project --apply --json
python3 plugins/setup/entry.py setup check /absolute/project --json
```

The preview is the approval boundary. The installer preserves unrelated project content, refuses custom
`core.hooksPath`, rejects symlinked installation paths, records hashes, and rolls back on failed probes.

## Enable a bundled plugin

The core intentionally ships with all optional plugin source available but disabled:

```bash
python3 bin/vemo plugin list
python3 bin/vemo plugin enable setup
python3 bin/vemo setup install /absolute/project --json
```

For a first installation into a repository that does not yet contain VEMO, invoke
`plugins/setup/entry.py` directly as shown above; the target cannot enable a command it has not installed yet.

## GitHub Actions

Copying or installing VEMO does not configure branch protection. Require the `vemo` workflow check and CODEOWNERS
review for policy, task, enforcement, and workflow files. Store approval variables as protected repository or
environment variables. The first 2.0 bootstrap merge is intentionally fail-closed when the base commit has no
VEMO evaluator; approve that one merge through the repository's protected process.

## Upgrade, rollback, and uninstall

Preview every upgrade and keep a rollback branch or tag. For 1.x repositories, read [MIGRATION.md](MIGRATION.md);
VEMO refuses to guess at legacy YAML policy. The setup plugin's uninstall restores only files recorded in its
install manifest and refuses to remove files changed after installation.
