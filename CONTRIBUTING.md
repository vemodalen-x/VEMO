# Contributing

Keep VEMO smaller than the problem it solves.

1. Create `vemo.task.json` with the smallest useful scope.
2. Put policy behavior only in `enforcement/core.py`; adapters may translate inputs and exit codes only.
3. Add a positive and negative test for every policy change.
4. Stage the intended diff, run `python3 bin/vemo verify`, stage the evidence file, and run
   `python3 bin/vemo check`.
5. Critical changes require approval supplied outside the proposed repository diff.

New functionality belongs in the core only when an unauthorized or unverified code change cannot be prevented
with the existing Policy, Task, Gate, Verify, or Evidence concepts. Everything else belongs in a plugin—or is
better left out.

## Plugin and Fleet changes

- Keep plugin policy authority at zero: plugins may present or automate workflows but must not override a core
  `deny` or `approval_required` decision.
- Fleet must not import or execute target repository code, hooks, plugin entry points, or verification commands.
- Keep Fleet APIs read-only and loopback-only unless a separate security design and threat review is accepted.
- Keep browser assets self-contained and offline; do not add CDNs, remote fonts, telemetry, or required cloud
  services.
- Add CLI/API positive and negative tests for changed behavior, including approval-environment stripping and
  mutation attempts where relevant.
- Update [docs/CONTROL-PLANE.md](docs/CONTROL-PLANE.md), platform guidance, security boundaries, and embedded setup
  help whenever the user-facing contract changes.
