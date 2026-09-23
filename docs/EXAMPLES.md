# End-to-end examples

These examples use the core contract only unless they explicitly invoke the optional setup plugin. Replace sample
paths and verification commands with repository-specific values.

## 1. Initialize a new repository

```bash
python3 bin/vemo init
python3 bin/vemo task create --id T-bootstrap --scope 'src/**' 'tests/**' 'README.md'
python3 bin/vemo task show
python3 bin/vemo check --self
```

Review `vemo.json` before the first governed code change. `init` installs local adapters, but protected CI remains
the merge authority.

## 2. Add VEMO to an existing repository

From a trusted VEMO checkout:

```bash
python3 plugins/setup/entry.py setup install /srv/project --preset python --profile team --json
# review and retain the returned plan_id
python3 plugins/setup/entry.py setup install /srv/project --preset python --profile team --apply --plan-id '<plan-id>' --json
python3 plugins/setup/entry.py setup check /srv/project --json
```

Commit the installed payload through a reviewed bootstrap pull request. Then make the `vemo` workflow a required
check. The installer does not configure remote GitHub settings.

## 3. Complete an AI-authored fix

```bash
python3 bin/vemo status
python3 bin/vemo task create --id T-fix-parser --scope 'src/parser.py' 'tests/test_parser.py'

# The agent checks each planned write through its harness adapter, edits only authorized paths,
# and the operator stages only the intended files.
git add src/parser.py tests/test_parser.py
python3 bin/vemo check --no-evidence
python3 bin/vemo verify
git add .vemo/evidence/T-fix-parser.json
python3 bin/vemo check
```

Completion requires `allow`. A later edit changes the diff snapshot and makes the evidence stale, so verification
must be run again.

## 4. Guard a critical path

Suppose `vemo.json` includes `.github/**` and `enforcement/**` in `critical_paths`. A task touching those paths
returns `approval_required` until a trusted environment injects approval bound to the task digest:

```bash
python3 bin/vemo task create --id T-ci-change --risk critical --scope '.github/workflows/vemo-ci.yml'
python3 bin/vemo task show
```

The reviewer obtains the digest from `task show` and configures protected CI values:

```text
VEMO_APPROVED_TASK=T-ci-change
VEMO_APPROVED_TASK_DIGEST=<exact digest>
VEMO_APPROVED_BY=<reviewer or trusted approval service>
```

Do not commit these values. If task scope or risk changes, the digest changes and the old approval no longer
matches.

## 5. Gate a dangerous harness command

Before execution, the harness asks the core for a decision:

```bash
python3 bin/vemo check --action command --command 'python3 -m unittest discover -s tests'
```

Commands classified under a denied action require an externally supplied `VEMO_APPROVED_ACTIONS` entry as well as
task approval. The exact command is still subject to the execution sandbox and operating-system permissions; VEMO
does not execute or isolate it on behalf of the harness.

## 6. Enforce pull requests in GitHub Actions

After installing `.github/workflows/vemo-ci.yml`:

1. open a bootstrap pull request reviewed through the repository's protected process;
2. after bootstrap, require the workflow's `vemo / gate` check;
3. require owner review for governance files;
4. keep approval variables in protected repository or environment variables;
5. test the gate with a pull request that edits an out-of-scope file and confirm CI denies it.

A positive test alone is insufficient. Also test missing evidence, stale evidence, a critical change without
approval, and a candidate change that modifies its own verification commands.

## 7. Enable and remove an optional plugin

```bash
python3 bin/vemo plugin list
python3 bin/vemo plugin enable setup
python3 bin/vemo --help
python3 bin/vemo plugin disable setup
```

Plugins are trusted repository code and are disabled by default. Enabling one changes `vemo.json`, which is a
critical path in the default policy and therefore follows the critical approval flow.

## 8. Upgrade, recover, or uninstall

```bash
python3 plugins/setup/entry.py setup install /srv/project --json
# review the upgrade plan before applying it with its plan_id
python3 plugins/setup/entry.py setup recover /srv/project --apply
python3 plugins/setup/entry.py setup uninstall /srv/project --json
```

Keep a rollback branch or tag. For 1.x policy conversion, follow [MIGRATION.md](MIGRATION.md); the installer refuses
to infer a 2.0 policy from legacy YAML.

## Acceptance tests for an installation

An installation is demonstrated, not merely configured, when all applicable checks are observable:

| Test | Expected evidence |
|---|---|
| Self contract | `python3 bin/vemo check --self` exits 0 |
| In-scope normal change | verification evidence is generated and final decision is `allow` |
| Out-of-scope change | local or CI decision is `deny` with the offending path |
| Missing/stale evidence | decision is `deny` until verification is rerun |
| Critical change without approval | decision is `approval_required` |
| Protected approval | exact task digest allows only the approved authorization |
| CI policy tampering | trusted-base preflight rejects an unapproved replacement policy |
| Interrupted setup | recovery restores a checkable state without overwriting unrelated files |
