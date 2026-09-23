# Migrating from VEMO 1.x

Create a rollback point first:

```bash
git branch backup/vemo-1x
python3 bin/vemo init --migrate
```

Migration reads the newest live `tasks/T-*.md` record and writes `vemo.task.json` when the new file does not
already exist. It preserves:

- task id;
- `scope_in` as `scope`;
- R2 as `critical`, R0/R1 as `normal`;
- the task risk and scope without importing self-asserted verification or approval state.

If a root `vemo.config.yaml` still exists, migration stops. Map its R2 `match_paths` to
`vemo.json.critical_paths` and its required build/smoke commands to argv arrays under `verification`, review the
result, then archive the old file under `plugins/legacy/`. The minimal core intentionally has no partial YAML
reader: silently dropping an unfamiliar 1.x rule would be a security downgrade.

Review `vemo.json` and `vemo.task.json`, stage the intended migration, run `vemo verify`, stage the evidence,
and run `vemo check`.

The first merge that installs VEMO 2.0 cannot load a trusted 2.0 evaluator from its base commit. The CI adapter
fails closed in that case. Approve that bootstrap through the repository's protected merge process; subsequent
changes use the evaluator extracted from the base commit for the initial no-execution preflight.

Concepts removed from the core have no automatic security meaning:

| 1.x concept | 2.x treatment |
|---|---|
| R0/R1/R2 and change classes | `normal` or `critical` |
| lifecycle state | derived from task, evidence, and approval |
| capability/model tier | removed; harness or plugin concern |
| judge ledger | optional review/plugin concern; CI evidence is authoritative |
| telemetry, budgets, auto mode | optional plugins |
| legacy Fleet and UI | replaced by the optional read-only Fleet control plane |
| Product/platform reports | removed; workstation and single-project views are consolidated in Fleet |
| extension composition | removed; explicit data-only plugin manifests replace it |

Legacy Fleet state is not migrated automatically. Register each desired absolute project path in the new user-local
registry after confirming its repository-level installation. This avoids treating stale discovery or historical
profiles as current authorization. Setup UI and Fleet UI also remain separate: setup may apply a reviewed
`plan_id`, while Fleet has no target-write endpoint.

Rollback is `git switch backup/vemo-1x` or reverting the migration commit. VEMO never rewrites task history or
deletes the old task records during migration.
