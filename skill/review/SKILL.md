---
name: review
description: Use when implementation is complete or a pull request is open to find correctness, scope, safety, and completeness bugs that can pass a superficial check.
---

# Review

Act as the skeptical Staff Engineer. Start with `vemo judge-brief --lens correctness` and inspect only the
staged diff or explicit PR range. Check the acceptance criteria, changed-file scope, error paths, and evidence.
Use the safety lens for secrets, destructive behavior, permission changes, and provenance.

Record required independent verdicts through `task_state.py judge-record`; the front-matter mirror is only a
human-readable cache. Do not call a task done from a self-report alone.
