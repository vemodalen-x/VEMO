---
name: ship
description: Use when a reviewed task is ready to publish; run the authoritative local checks, prepare an intentional commit, and hand off to the repository's CI and branch protection.
---

# Ship

Confirm the task is accepted, the required judge provenance is contiguous, the diff is in scope, and the
receipt is fresh. Run the same pre-push gate CI runs. Commit only the intended files, push the current branch,
and report the PR/check URL.

This skill never uses `--no-verify`, force-push, or hidden policy changes. Publishing remains a user-approved
action; the CI workflow is the authoritative server-side gate.
