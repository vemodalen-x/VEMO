# Optional independent review guide

Review a staged diff from a fresh context and try to disprove completion.

Check only evidence:

1. `vemo.task.json` authorizes every changed path.
2. `vemo check --no-evidence` allows the exact staged/range diff.
3. `.vemo/evidence/<task>.json` names the same snapshot and command list.
4. Re-run the verification commands and one negative test.
5. Confirm critical approval came from the environment, not the proposed diff.
6. Confirm no secret, destructive side effect, or unreviewed plugin activation is present.

Return `pass` or `fail`, violations with file/line or command evidence, and confidence. The core does not require
a local judge ledger; teams may publish the verdict as a CI check or review attestation.
