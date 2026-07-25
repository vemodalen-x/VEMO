---
name: plan-eng-review
description: Use after product scope is chosen and before coding when architecture, data flow, failure modes, or acceptance evidence need to be made explicit.
---

# Engineering Review

Lock the technical part of Plan: entry points, data flow, state transitions, failure modes, security boundary,
test matrix, and rollback or recovery. Prefer VEMO's deterministic tools such as `call-graph` when tracing is
needed. Keep the plan proportional to the task risk.

Add the decisions and measurable commands to the task file. Do not widen `scope_in` silently. R2 plans need the
appropriate approval and judge depth before implementation continues.
