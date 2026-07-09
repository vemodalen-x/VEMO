# Adopting an Agent Playbook into VEMO

This note captures the portable parts of a repo-local agent playbook and maps them to VEMO's mechanisms. The rule is:
do not copy another project's playbook wholesale. Convert stable workflow rules into VEMO controls, and re-measure all
project facts inside the consuming repo.

## Mapping

| Playbook idea | VEMO mechanism |
| --- | --- |
| Thin root instruction file | `AGENTS.md` stays a router; detailed rules live in `specs/` and load through `specs/_manifest.yaml`. |
| Start by checking context and repository state | `vemo context`, `vemo status`, `vemo doctor`; avoid bulk-reading config and large files. |
| Explore -> plan -> implement -> submit | `tasks/_TASK_TEMPLATE.md` plus `specs/task.spec.md`; the task file stores scope, plan, evidence, and acceptance. |
| "Done" requires executed evidence | `paths.build`, `paths.smoke`, and `vemo verify`; the push gate trusts the machine receipt, not typed exit codes. |
| Model routing and escalation | `capability.tier`, `model_routing`, and judge depth in `verify.spec.md`; keep vendor names advisory. |
| Fresh reviewer for sign-off | `agents/governance-judge.md` and `.vemo/judge.jsonl` for high-risk gates. |
| Repeated lessons become rules | One-off lessons stay in task logs; repeated, mechanical lessons become specs, validators, hooks, or VEMO skills. |
| Prose is not enough | Hooks, git gates, and CI backstop enforce the non-negotiables. |

## What Must Be Rebuilt per Consumer

These are not portable and must be measured or written in the target repo:

- actual build and smoke commands in `vemo.config.preset.yaml`
- noisy generated paths and ignore rules
- authoritative source paths versus historical copies
- domain-specific completion definitions
- risk-tier path patterns
- any project identities, group ids, URLs, secrets, or notification routes

If a migrated playbook says "run these tests", that statement is only a template until the target repo has run and
recorded its real commands.

## When to Use VEMO_SKILLS Instead

Put reusable, prompt-triggered procedures in VEMO_SKILLS when they are generic and do not own an acceptance gate:
publishing deliverables, reviewing decisions, structuring solution docs, rendering reports, or packaging common
artifacts.

Keep project acceptance in VEMO. A skill may guide how to run an evaluation, but the consuming project's task file and
`vemo verify` receipt decide whether the work is accepted.

## Anti-Patterns

- Copying another repo's diagnostic numbers or completion commands.
- Expanding `AGENTS.md` into a long rulebook.
- Adding a prose rule when a validator, hook, or CI check can enforce it.
- Claiming completion without `vemo verify` or equivalent executed evidence.
- Letting several agents write the same file set concurrently; parallelize read-only discovery and review, keep writes
  single-threaded unless file ownership is explicitly partitioned.

