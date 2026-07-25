---
id: T-20260725-add-gstack-inspired-vemo-delivery-loop
risk: R1
change_class: standard
state: AcceptancePassed
scope_in: ["bin/vemo", "bin/vemo_product.py", "bin/vemo_fleet.py", "skill/_catalog.md", "skill/office-hours/**", "skill/plan-ceo-review/**", "skill/plan-eng-review/**", "skill/review/**", "skill/qa/**", "skill/ship/**", "skill/retro/**", "docs/PRODUCT.md", "docs/QUICKSTART.md", "README.md", "CHANGELOG.md", "tests/test_product.py", "tests/test_fleet.py", "tasks/T-20260725-add-gstack-inspired-vemo-delivery-loop.md"]
scope_out: []
trifecta: []
verification:
  profile: focused
  commands:
    test: "python -m unittest discover -s tests -p test_*.py"
    lint: "python -m py_compile bin/vemo bin/vemo_product.py bin/vemo_fleet.py"
    smoke: "python bin/vemo workflow --json"
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260725-add-gstack-inspired-vemo-delivery-loop-20260725T155630Z.log"
judge:
  required: false
  verdict: null
approved_commands: []
owning_chat: ""
heartbeat: 2026-07-25T15:56:48Z
---

# Add gstack-inspired VEMO delivery loop

## Goal
Make VEMO's product loop as easy to repeat as gstack's role-based sprint: a user can see the next stage,
invoke a focused skill, and leave evidence in the existing VEMO task/receipt/judge/telemetry records.

## Scope (In / Out)
- In: mirror `scope_in` above.
- Out: everything else.

## Pass/Fail Criteria
- [ ] `vemo workflow --json` SHALL be read-only, emit schema version, local-only status, the active task, seven
  ordered stages, and exactly one next stage.
- [ ] The workflow SHALL map `PlanCreated`, `ImplementationDone`, and `AcceptancePassed` to actionable next
  stages without changing task state or bypassing any gate.
- [ ] Seven thin role skills SHALL be discoverable through `skill-audit` and `skill-roster`, with no dangling
  backing scripts or generated-copy edits.
- [ ] Fleet onboarding SHALL treat `skill/` as a managed framework directory so the role skills reach registered
  projects without hand-copying.
- [ ] Documentation SHALL explain the Think -> Reflect loop and distinguish it from gstack's browser-specific
  runtime; no new network service or dependency SHALL be required.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` SHALL exit 0.
- [ ] `python enforcement/validators/task_state.py selfcheck` SHALL exit 0.
- [ ] `python eval/run.py` SHALL exit 0.

## Plan
- Add a read-only workflow report to the existing product CLI and cover state mapping with unit tests.
- Add thin role skills and catalog entries that route to existing VEMO artifacts and gates.
- Update the product/tutorial/changelog surfaces, then run skill audit, tests, selfcheck, and conformance eval.

## Execution Log
- 2026-07-25T15:44:25Z Task created by `vemo task create`.
- 2026-07-25T15:51:28Z Implemented read-only workflow dashboard, seven gstack-inspired role skills, skill registry parity, and fleet-managed skill propagation. Unit, selfcheck, skill audit, and eval are green; fleet regression now asserts skill catalog propagation.
- 2026-07-25T15:53:22Z Focused receipt passed with test, lint, and workflow smoke; full eval is 110/110, selfcheck is OK, skill audit is clean, and fleet regression asserts skill catalog propagation.
- 2026-07-25T15:55:46Z Rejected the first receipt because quoted unittest glob was parsed incorrectly and ran 0 tests; replaced it with a portable unquoted glob, re-ran focused verification, and confirmed all 22 tests execute with exit 0.
- 2026-07-25T15:56:48Z Final focused verification after onboarding docs sync passed: 22 tests executed, py_compile passed, and workflow JSON smoke passed; latest evidence is the 15:56:30Z receipt log.

## Acceptance Result
PASS: workflow contract, skill audit, unit tests, selfcheck, conformance eval, focused verification, and fleet
skill propagation regression all pass. The workflow is read-only and the receipt records test, lint, and smoke exits.

## Conclusion
Outcome: accepted | Decision: continue | Key Evidence: `.vemo/run/T-20260725-add-gstack-inspired-vemo-delivery-loop-20260725T155630Z.log` | Risk: low | Next Action: complete review and publish.
