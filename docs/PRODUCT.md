# VEMO Product Path

VEMO is the policy and evidence layer for AI-assisted software delivery. The product promise is simple:

> Let an Agent move quickly inside a known boundary, and make every important claim executable and reviewable.

VEMO is not a prompt pack, a legal certification, or a sandbox. The local Core uses hooks, Git gates, and CI
to make the controls durable. Use an OS or container sandbox when the host is untrusted.

## The user loop

### 1. Start without risk

```bash
python bin/vemo start --preset python
```

This is read-only. It detects the stack, shows the files the installer would touch, and explains the next step.
Apply only after reviewing the plan:

```bash
python bin/vemo start --preset python --profile solo --apply
```

The supported profiles are progressive adoption targets:

| Profile | Best for | User-visible outcome |
|---|---|---|
| `solo` | one developer or an experiment | local scope, secret, command, and evidence controls |
| `team` | shared repositories and multiple Agents | authoritative CI, ownership, review, and audit evidence |
| `regulated` | higher-assurance delivery | evidence-oriented controls and release provenance checks |

Profiles describe posture. They are not legal advice or a certification claim.

### 2. See value after the first session

```bash
python bin/vemo report
python bin/vemo report --days 7 --json
```

The report uses local telemetry, task state, Git setup, and verification receipts. It reports observed facts:
sessions, blocked actions, verification runs, accepted tasks, and setup gaps. It deliberately does not infer
prevented incidents, legal compliance, or monetary savings.

The report is local-only by default:

- source code and prompts are not uploaded;
- JSON output is stable enough for a local dashboard or scheduled check;
- malformed telemetry is counted instead of silently treated as proof;
- the next actions are recommendations, not hidden mutations.

### 3. Make the control authoritative

Local hooks are fast feedback. Team adoption requires the CI backstop and protected branches:

```bash
mkdir -p .github/workflows
cp enforcement/ci/vemo-ci.yml .github/workflows/
```

Require the `vemo` check on protected branches. The local report shows this as a setup gap until it is present.

## Commercial boundary

The current repository is the open Core. A commercial offering should charge for organization-level operations,
not for the basic scope guard:

| Layer | Core now | Paid product direction |
|---|---|---|
| Enforcement | local hooks, Git gates, CI | signed policy distribution and break-glass workflow |
| Evidence | local receipts and judge provenance | retention, export, dashboards, and audit integrations |
| Fleet | local project registry and readiness | organization inventory, SSO, RBAC, and central policy |
| Integrations | Claude wiring plus portable dispatcher | GitHub/GitLab, IDEs, coding agents, and MCP registry |
| Skills | repository-managed VEMO skills | signed registry, permission manifests, compatibility, and evaluation |

Do not add a paywall before the free path demonstrates value. The paid trigger is shared accountability: a team
needs policy ownership, audit retention, remote controls, and support across many projects.

## Product metrics

Use these measures with design partners before spending on broad promotion:

- time from install to first observed event;
- time from install to first blocked out-of-scope action;
- verification runs per repository per week;
- block rate and false-positive rate by control;
- acceptance-to-merge time for Agent-assisted changes;
- weekly active governed repositories;
- percentage of repositories with the CI backstop;
- conversion from `solo` to `team` after multi-user adoption.

The first commercial proof is not a larger rule catalog. It is repeated usage, lower review friction, and a
machine-readable evidence trail that a team is willing to retain.
