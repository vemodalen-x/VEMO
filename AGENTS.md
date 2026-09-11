# VEMO agent contract

VEMO exists to ensure an AI-authored code change stays inside an explicit task boundary and cannot be merged
without executed verification evidence.

For a coding task:

1. Run `python3 bin/vemo status`.
2. Read `vemo.json` and `vemo.task.json`; these are the only machine policy and current authorization.
3. Keep writes inside `vemo.task.json.scope`.
4. Before completion, stage the intended diff, run `python3 bin/vemo verify`, stage the evidence file, then run
   `python3 bin/vemo check`.
5. A decision other than `allow` is a blocker. Fix its stated reason; do not bypass hooks or CI.

Only five concepts are mandatory: Policy, Task, Gate, Verify, Evidence. Commands not shown by `vemo --help`
belong to explicitly enabled plugins and are not part of the governance contract.
