---
name: hackathon-submission
description: Prepare a Devpost-style hackathon entry for submission — verify the required artifacts exist (public/testable repo, README AI-usage section, demo video, session/thread id evidence), map the project's acceptance evidence onto the contest's own judging criteria, and run a pre-submission judge pass against them. Use when a deadline-bound contest submission (e.g. OpenAI Build Week) is close to done and needs a readiness check before the submission form is filled in.
---

# Hackathon Submission Readiness

A pre-flight check for a judged hackathon entry — turns the contest's own rules page into a checklist VEMO
can verify against, instead of trusting memory at deadline time. Companion to
`docs/HACKATHON_PLAYBOOK.md` (the fuller how-to); this skill is the short, repeatable "are we ready" pass.

## When to use
- A hackathon/Devpost-style submission is functionally done and the deadline is close.
- Trigger phrases: "check hackathon submission readiness", "黑客松提交自查", "pre-submission check".

## Inputs
- The contest's official rules page (re-read it — terms change; do not rely on a stale summary).
- The project's task file(s) (`tasks/*.md`) and their acceptance evidence.
- The demo video, README, and repo visibility state.

## Procedure
1. **Re-derive the checklist from the rules, don't assume last week's.** Pull the current judging criteria
   and required artifacts fresh — a contest can revise categories/prizes/deadlines mid-run.
2. **Artifact check** (mechanical, no judgment needed):
   - Repo is public and buildable from the README alone.
   - README has an explicit section naming the required AI tool(s) and *how* they were used.
   - Session/thread id evidence for the core-functionality work is recorded (pull it from the task
     Execution Log — see `docs/HACKATHON_PLAYBOOK.md` §4 — not from memory).
   - Demo video exists, is under the contest's time limit, is narrated, and is on the required host.
   - A single category/track is selected and named in the description.
3. **Evidence check (reuse VEMO's own gate, don't re-invent one).** Every task's acceptance criteria must be
   `passed` with a real evidence file (`vemo verify` receipt) — an unverified "done" here is the same failure
   mode `agents/governance-judge.md` exists to catch, and a contest judge is not more forgiving of it than
   VEMO is.
4. **Pre-submission judge pass.** Invoke `agents/governance-judge.md` with the contest's own judging criteria
   (not only the task's Pass/Fail Criteria) as the checklist — ask it to score/flag against each criterion
   using only verifiable evidence, the same way it would flag a scope leak or an unrun check. This is a dry
   run of what an external judge sees; it cannot judge creativity, but it catches unverified claims early.
5. **Report gaps, don't paper over them.** Anything missing is a checklist item, not a rationalization —
   flag it to the user rather than deciding it doesn't matter.

## Output
A short readiness report: artifact checklist (pass/fail per item), acceptance-evidence status per task, and
the judge pass's per-criterion notes. Gaps are listed explicitly, not silently dropped.

## Rules
- **Read-only / advisory** — this skill does not edit the submission, write the video, or file the form; it
  reports readiness. The human submits.
- **Does not replace `vemo verify` or the judge** — it composes them against the contest's criteria; it is
  not a second acceptance mechanism.
- Contest facts (rules URL, category chosen, artifact locations) are read fresh each run, never hardcoded
  here — a contest's terms and dates are exactly the kind of fact that goes stale (`docs/HACKATHON_PLAYBOOK.md`
  §1 makes the same point about the rules snapshot).
