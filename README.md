# VEMO

VEMO is a small governance kernel for AI-authored code changes.

It answers five questions with five concepts:

| Concept | Question |
|---|---|
| Policy | What rules does this repository enforce? |
| Task | What change is currently authorized? |
| Gate | Is this action or diff allowed? |
| Verify | Were the required commands actually executed? |
| Evidence | Which exact diff did those commands verify? |

The core does not route models, manage fleets, run a UI, maintain a workflow state machine, or model itself as
a platform. Those capabilities are optional local plugins.

## Quick start

```bash
python3 bin/vemo init
python3 bin/vemo task create --id T-example --scope 'src/**' 'tests/**'
# edit and stage the intended change
python3 bin/vemo verify
git add .vemo/evidence/T-example.json
python3 bin/vemo check
```

For a different repository, run the optional setup plugin from this checkout:

```bash
python3 plugins/setup/entry.py setup install /absolute/project --json
# copy plan_id from the reviewed preview
python3 plugins/setup/entry.py setup install /absolute/project --apply --plan-id '<plan-id>' --json
python3 plugins/setup/entry.py setup check /absolute/project --json
```

Read [the installation guide](docs/INSTALL.md), [platform matrix](docs/PLATFORMS.md), and
[complete usage guide](docs/USAGE.md) before enabling it in a shared repository. For agent-operated setup, use the
[AI installation protocol](docs/AI-INSTALL.md); for copyable workflows, see [the examples](docs/EXAMPLES.md).

`check` returns one of three decisions:

- `allow`
- `deny`
- `approval_required`

Normal changes need scope compliance and matching verification evidence. Critical paths and dangerous actions
also need approval injected by the CI or Harness environment (`VEMO_APPROVED_TASK`,
`VEMO_APPROVED_TASK_DIGEST`, and `VEMO_APPROVED_BY`). The digest binds approval to the exact normalized task
scope and risk, so changing repository authorization invalidates an earlier approval.
Dangerous command categories additionally require an exact value in comma-separated `VEMO_APPROVED_ACTIONS`. A PR
cannot approve itself by editing repository files. Model names and subjective capability tiers never weaken this rule.
Use `python3 bin/vemo task show` to obtain the current approval digest.

For GitHub Actions, configure those names as protected repository or environment variables. CI performs a no-exec
preflight before running repository verification commands, so a PR cannot modify `vemo.json` and immediately execute
its replacement command list without external approval.

## Files

```text
vemo.json                 repository policy
vemo.task.json            current task authorization
enforcement/core.py       the only policy evaluator
enforcement/hooks/run.py  thin pre-action adapter
enforcement/ci/*          thin Git/CI adapters
.vemo/evidence/*.json     snapshot-bound verification results
plugins/*/plugin.json     optional feature commands
```

## CLI

The default CLI exposes exactly six entry points:

```text
task  check  verify  status  init  plugin
```

Run `python3 bin/vemo --help` for their purpose. See [the usage guide](docs/USAGE.md),
[platform support](docs/PLATFORMS.md), [AI installation guide](docs/AI-INSTALL.md),
[examples](docs/EXAMPLES.md), [plugin documentation](docs/PLUGINS.md), and the
[1.x migration guide](docs/MIGRATION.md).

For governance across all projects on one workstation, use the optional Fleet control plane and visual dashboard
described in [docs/CONTROL-PLANE.md](docs/CONTROL-PLANE.md). It observes repository-local gates without replacing
them or executing project code.

```bash
python3 plugins/fleet/main.py register /absolute/project --label ProjectName
python3 plugins/fleet/main.py status --json
python3 plugins/fleet/main.py serve
```

Registration is an inventory action, not installation or a compliance claim. Use the setup plugin separately for
repository changes, and keep the dashboard on its default loopback listener.

## Enforcement model

The harness hook provides early feedback before a write or dangerous command. Git hooks provide local feedback.
CI reruns verification and makes the merge decision over the server-visible range. All three call the same
evaluator; only the adapters differ.

Verification commands are JSON argv arrays, not shell strings. CI first loads the evaluator from the trusted
base commit and uses it for the no-execution preflight; only an accepted preflight may run candidate code. The
first 2.0 installation has no trusted base evaluator and therefore needs an explicitly reviewed bootstrap merge.

VEMO is not an OS sandbox. Pair it with containers or another isolation boundary when executing untrusted code.
