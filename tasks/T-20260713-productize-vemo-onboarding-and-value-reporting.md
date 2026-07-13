---
id: T-20260713-productize-vemo-onboarding-and-value-reporting
risk: R2
change_class: standard
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_product.py", "bin/vemo_fleet.py", "tests/test_product.py", "eval/run.py", "docs/PRODUCT.md", "docs/QUICKSTART.md", "docs/FLEET.md", "README.md", "CHANGELOG.md", "tasks/T-20260713-productize-vemo-onboarding-and-value-reporting.md", ".vemo/judge.jsonl"]
scope_out: []
trifecta: []
verification:
  profile: full
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260713-productize-vemo-onboarding-and-value-reporting-20260713T121626Z.log"
judge:
  required: true
  verdict: pass
approved_commands: []
owning_chat: ""
heartbeat: 2026-07-13T12:19:28Z
---

# Productize VEMO onboarding and value reporting

## Goal
Make VEMO usable as a product: a new project can preview and apply onboarding through one CLI path, an existing user can inspect observed governance value locally, and the docs explain a credible solo-to-team-to-regulated adoption path without claiming certification.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else.

## Pass/Fail Criteria
- [x] [Correctness] WHEN `python bin/vemo start --preset python` runs, the command SHALL be read-only, identify the detected stack, show the planned changes, and exit 0.
- [x] [Correctness] WHEN `python bin/vemo start --preset python --apply` runs, the command SHALL apply the preset and hooks only through the existing init path and exit 0; a managed preset conflict SHALL fail with an actionable message without overwriting the file.
- [x] [Correctness] WHEN `python bin/vemo report --json` runs, the command SHALL emit valid JSON with schema version, observed event counts, verification status, adoption profile, and `data_local_only: true` without reading or transmitting source content.
- [x] [Quality] The report SHALL distinguish observed measurements from recommendations and SHALL not claim legal compliance, prevented incidents, or monetary savings without evidence.
- [x] [Build] `python eval/run.py` SHALL exit 0.
- [x] [Build] `python enforcement/validators/task_state.py selfcheck` SHALL exit 0.
- [x] [Build] `python -m unittest discover -s tests -p "test_*.py"` SHALL exit 0.

## Plan
- Add a thin `vemo_product.py` read-only product layer for stack detection, progressive onboarding, and local value reporting.
- Keep enforcement authoritative in existing mechanisms; wire the product layer through `bin/vemo`, then document the free Core, team control-plane, and regulated evidence paths.
- Add focused unit/eval coverage and run the repository's full receipt-producing verification.

## Execution Log
- 2026-07-13T12:07:29Z Task created by `vemo task create`.
- 2026-07-13T12:07:53Z Productization plan locked: add start/report thin layer, keep enforcement authoritative, document adoption tiers, and verify via eval/selfcheck/unit tests.
- 2026-07-13T12:17:28Z Acceptance passed from full receipt: vemo verify --no-cache build_exit=0 smoke_exit=0; product checks, selfcheck, and 19 unit tests passed.
- 2026-07-13T12:19:28Z Independent correctness and safety Judge passes recorded with separate sessions; verdict mirrored to front-matter.

## Acceptance Result
PASS: `python bin/vemo start --preset python` is read-only and returns a JSON preview with detected stack and planned actions.
PASS: `vemo start --apply` delegates setup to the existing init path; managed preset conflicts fail closed without overwrite.
PASS: `python bin/vemo report --json` emits schema-versioned, local-only observed metrics and omits event payloads.
PASS: The report labels measurements as observed and keeps recommendations separate from claims about incidents, compliance, or savings.
PASS: `python eval/run.py` and `python enforcement/validators/task_state.py selfcheck` pass in the full receipt.
PASS: `python -m unittest discover -s tests -p "test_*.py"` passes with 19 tests.

## Conclusion
Outcome: accepted · Decision: continue · Key Evidence: full VEMO receipt at `.vemo/run/T-20260713-productize-vemo-onboarding-and-value-reporting-20260713T121626Z.log` · Risk: med · Next Action: complete the required independent Judge passes, then publish the branch.
