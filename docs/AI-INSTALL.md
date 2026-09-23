# AI-assisted installation

An AI coding agent may operate the installer, but it must not become its own approver. Installation is a governed
repository change: preview first, let a human or trusted automation approve the exact plan, apply that plan, then
run the installed contract checks.

## Safe installation protocol

From a trusted VEMO source checkout, ask the agent to perform these stages:

1. Confirm the target is the intended Git repository and inspect its working tree without changing it.
2. Run a preview without `--apply` and return the JSON plan and `plan_id`.
3. Stop if the preview reports conflicts, symlinks, a custom `core.hooksPath`, legacy policy, or an unexpected
   target. Do not delete or overwrite the conflicting files.
4. After approval of the exact plan, apply it with the same `plan_id`.
5. Run setup `check`, core `check --self`, and the repository's own tests.
6. Show the final diff and list any platform or CI steps that still require an owner.

```bash
python3 plugins/setup/entry.py setup install /absolute/project --preset python --profile team --json
python3 plugins/setup/entry.py setup install /absolute/project --preset python --profile team --apply --plan-id '<preview-plan-id>' --json
python3 plugins/setup/entry.py setup check /absolute/project --json
python3 /absolute/project/bin/vemo check --self
```

Presets (`python`, `node`, `cpp`, `docs`) choose initial verification commands. Profiles (`solo`, `team`,
`regulated`) choose conservative policy defaults. They are starting points, not proof that the target's actual
build and test commands are correct.

## Prompt template for Claude Code, Codex, or another coding agent

```text
Install VEMO into <absolute target repository> from this trusted VEMO checkout.

Rules:
- inspect the target AGENTS.md and CLAUDE.md first;
- do not modify the VEMO source checkout;
- first run setup install without --apply and show me the JSON preview and plan_id;
- do not apply until I approve that exact plan;
- never overwrite conflicts, bypass hooks, alter Git configuration, or set VEMO_APPROVED_* values;
- after approval, apply using the approved plan_id, run setup check and bin/vemo check --self;
- create an explicit task for any follow-up repository edits;
- show the final git diff and report tests not run or platform behavior not verified;
- do not push unless I explicitly request it.
```

For unattended enterprise provisioning, replace the conversational approval with a trusted service that validates
the preview artifact and passes its `plan_id`. Do not interpret "AI installation" as permission for the model to
approve critical paths or dangerous actions.

## Installing from the optional local UI

The setup plugin includes a local-only browser UI. Start it from the trusted VEMO checkout:

```bash
python3 plugins/setup/entry.py ui
```

macOS can use `plugins/setup/ui/start.command`; Windows can use `plugins\setup\ui\start.cmd`. The UI is another
client of the same preview/apply/check service, not an alternative policy engine. Keep the browser bound to the
local machine and review the preview before applying.

## Failure and recovery

The setup service records a journal and rolls back failed probes. If an operation was interrupted, inspect the
target first and use:

```bash
python3 plugins/setup/entry.py setup recover /absolute/project --apply
python3 plugins/setup/entry.py setup check /absolute/project --json
```

For removal, preview before apply:

```bash
python3 plugins/setup/entry.py setup uninstall /absolute/project --json
python3 plugins/setup/entry.py setup uninstall /absolute/project --apply --plan-id '<preview-plan-id>' --json
```

Uninstall removes only files recorded by the setup manifest and refuses files changed since installation. Keep a
branch or tag for larger upgrades and read [MIGRATION.md](MIGRATION.md) before converting a 1.x repository.

## Post-install owner checklist

- Review `vemo.json` verification argv against the real build and test commands.
- Replace the placeholder task with a narrowly scoped task before making code changes.
- Require the GitHub `vemo` check or implement an equivalent trusted-base check in another CI system.
- Protect policy, task, evaluator, hook, and workflow files with external review controls.
- Store approval variables outside the repository and outside model-controlled prompts.
- Add an OS sandbox when repository commands or dependencies are not trusted.
- Record which operating systems were actually exercised; consult [PLATFORMS.md](PLATFORMS.md).
