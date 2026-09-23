# VEMO usage guide

VEMO is a repository-local governance framework for AI-authored changes. The smallest useful operating loop is:

1. Policy defines critical paths, denied actions, and verification argv in `vemo.json`.
2. Task authorizes one change in `vemo.task.json` with an explicit id, scope, and risk.
3. Gate checks each write/command and the staged or CI diff.
4. Verify executes the policy commands and writes `.vemo/evidence/<task-id>.json`.
5. Evidence binds the successful commands to the exact diff snapshot.

## New repository or existing checkout

VEMO needs Python 3.10+, Git, and Bash 4+ for Git hooks. In a VEMO checkout or a copied core payload:

```bash
python3 bin/vemo init
python3 bin/vemo task create --id T-feature --scope 'src/**' 'tests/**'
```

`task create` may replace only the untouched `vemo.task.example.json` placeholder. It never overwrites a real
authorization. Use `python3 bin/vemo task show` to inspect the task and its approval digest.

## Daily change loop

```bash
# edit only files matching the task scope, then stage them
git add src tests
python3 bin/vemo check --no-evidence
python3 bin/vemo verify
git add .vemo/evidence/T-feature.json
python3 bin/vemo check
```

An `allow` decision is required. `deny` means fix the stated contract violation. `approval_required` means an
external CI or harness approval is missing; repository files cannot grant that approval.

Use action checks from an agent harness:

```bash
printf '%s' 'new content' | python3 bin/vemo check --action write --path src/app.py --content-stdin
python3 bin/vemo check --action command --command 'python3 -m unittest discover -s tests'
```

## Claude Code and Git integration

`enforcement/install.sh` installs `.git/hooks/pre-commit`, `.git/hooks/pre-push`, the canonical workflow, and
the Claude `PreToolUse` settings. It is idempotent and does not replace a custom `core.hooksPath`.

The hook is early feedback, not the authority. Protected CI must require the `vemo` check. Keep
`vemo.json`, `vemo.task.json`, `enforcement/**`, and `.github/**` behind branch protection and CODEOWNERS review.

## Critical paths and approvals

Changes touching `critical_paths`, destructive actions, or out-of-repository writes require environment-provided:

```text
VEMO_APPROVED_TASK=<task id>
VEMO_APPROVED_TASK_DIGEST=<digest from vemo task show>
VEMO_APPROVED_BY=<reviewer or trusted service>
VEMO_APPROVED_ACTIONS=<comma-separated action categories, when needed>
```

Do not store these values in `vemo.json`, task files, prompts, or committed workflow text. Configure them as
protected CI variables or inject them from the execution harness.

## Installing into another repository

The setup plugin is optional and transactional. From a VEMO source checkout:

```bash
python3 plugins/setup/entry.py setup install /absolute/project --preset python --profile solo --json
python3 plugins/setup/entry.py setup install /absolute/project --preset python --profile solo --apply --plan-id '<plan-id>' --json
python3 plugins/setup/entry.py setup check /absolute/project --json
```

Always review the preview before `--apply`. A legacy root `vemo.config.yaml` makes the preview fail closed until
critical paths and verification commands are explicitly mapped to the 2.0 JSON policy. Recovery and uninstall:

```bash
python3 plugins/setup/entry.py setup recover /absolute/project --apply
python3 plugins/setup/entry.py setup uninstall /absolute/project --json
python3 plugins/setup/entry.py setup uninstall /absolute/project --apply --plan-id '<plan-id>'
```

The setup plugin installs the 14-file core payload; it does not install optional plugins or business tests.

## Optional plugins

```bash
python3 bin/vemo plugin list
python3 bin/vemo plugin enable fleet
python3 bin/vemo --help
python3 bin/vemo plugin disable fleet
```

Plugins are trusted local code, not sandboxes. Keep the default `plugins: []` unless the repository explicitly
needs a plugin and its command is reviewed.

For workstation-wide governance, register projects with the optional Fleet plugin and start its loopback-only
dashboard. The registry is user-local and the dashboard is read-only; installation remains a separate setup plugin
operation. See [CONTROL-PLANE.md](CONTROL-PLANE.md).

```bash
python3 plugins/fleet/main.py discover /absolute/root --max-depth 4 --json
python3 plugins/fleet/main.py register /absolute/project --label ProjectName
python3 plugins/fleet/main.py status --json
python3 plugins/fleet/main.py inspect /absolute/project --json
python3 plugins/fleet/main.py serve
```

Discovery is read-only and does not register every repository it finds. Registration adds inventory metadata only;
it does not install VEMO or change the target.

## CI range checks and bootstrap

On pull requests CI first loads `enforcement/core.py` from the trusted base commit and performs a no-execution
preflight. Only then does candidate code run verification. The first merge that introduces VEMO 2.0 has no
trusted base evaluator and must be approved through protected repository bootstrap procedure.

## Troubleshooting

- `configuration_invalid`: check JSON syntax and use only the documented fields.
- `contract_unstaged`: stage changes to `vemo.json` or `vemo.task.json` before checking.
- `verification_missing`: run `vemo verify`, stage the generated evidence, then check again.
- `verification_stale`: rerun verification after changing code, scope, risk, or policy commands.
- `critical_approval_missing`: obtain external approval; do not add an approval field to the task file.
- setup reports a conflict: use the preview output, resolve the named file, and preview again.

For 1.x conversion, follow [MIGRATION.md](MIGRATION.md). For the manifest contract, see [PLUGINS.md](PLUGINS.md).
For operating-system and harness boundaries, see [PLATFORMS.md](PLATFORMS.md). Agent-driven setup must follow
[AI-INSTALL.md](AI-INSTALL.md), and complete command sequences are collected in [EXAMPLES.md](EXAMPLES.md).
