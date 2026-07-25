---
name: qa
description: Use when a task is approaching acceptance to run its configured verification profile, inspect the real log, and add regression coverage for every confirmed defect.
---

# QA

Run `vemo verify` for the active task, using `--no-cache` when the change or contract moved. Read the generated
`.vemo/run/*.log` and confirm the receipt's task, fingerprint, commands, and exit codes. Exercise one negative
case for a new guard or user path when practical.

Update acceptance only from executed evidence. Use `qa-only` judgment in the task notes when the user wants a
report without fixes; never replace a real receipt with a typed exit code.
