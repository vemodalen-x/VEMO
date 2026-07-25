# Hackathon Playbook — governing a Devpost-style build under a deadline

This is a how-to for running a short, judged hackathon build (reference case: **OpenAI Build Week**,
`openai.devpost.com` — Codex + GPT-5.6, four tracks, a two-stage judged review) through VEMO without the
ceremony that a multi-week product needs. It does not replace `docs/QUICKSTART.md`; it tells you which knobs
to turn for this specific shape of project: solo/small team, ~1 week, one external judge you cannot talk to.

## 1. Rules digest (verify against the live `/rules` page before you rely on it — contest terms change)

| Area | What the official rules said (2026-07-14 snapshot) |
|---|---|
| Build with | Codex + GPT-5.6 — Stage One of judging is pass/fail on "reasonably applies the required APIs/SDKs"; a submission with no real Codex usage can be screened out before scoring even starts |
| Tracks (pick one) | Apps for Your Life · Work and Productivity · Developer Tools · Education |
| Judging (Stage Two, equally weighted) | Technological Implementation · Design · Potential Impact · Quality of the Idea |
| Required submission artifacts | working repo (public, testable) · demo video <3 min on YouTube with narration · text description · README describing the Codex collaboration/workflow acceleration/design decisions · **Codex Session ID** for the thread where most core functionality was built |
| Eligibility gate | age of majority · resident of a country/territory on OpenAI's supported-API list · excludes sponsor/Devpost employees, judges, sanctioned territories — **check this against your own situation before investing the week; VEMO cannot verify it for you** |
| Open source | allowed, but the submission must "enhance and build upon" the underlying project, not merely wrap it; third-party SDKs/APIs need their own license compliance |

## 2. What judges actually reward (reading between the four criteria)

- **Stage One is a hard gate, not a scoring input.** Weak/undocumented Codex usage risks disqualification
  before "Quality of the Idea" is ever read. Treat "prove the Codex usage" as its own acceptance criterion,
  not an afterthought for the README.
- **The four Stage-Two criteria are equally weighted — do not over-invest in one.** A technically deep
  project with a confusing demo scores no better than a polished one with thin substance; both leave points
  on the table versus a submission that clears a bar on all four.
- **"Problem, not model" wins Potential Impact + Quality of the Idea.** State the real problem first; Codex
  should be the answer to a stated need, not the premise.
- **Storytelling carries real weight.** The demo video and README are not paperwork — they are where
  "Design" and "Potential Impact" get judged, since the judge never uses your product live.

## 3. Map the four criteria to VEMO mechanism (what to actually do)

| Judging criterion | VEMO practice |
|---|---|
| Technological Implementation | Give the AI-core algorithm its own task file with a tight `scope_in` and real EARS acceptance criteria (`specs/verify.spec.md`) — depth shows in the diff and the evidence log, not in prose claims. Route it through Codex for real (§4), since this is the criterion Stage One screens on. |
| Design | `risk_tiers` R1 gate (`plan -> implement -> verify -> done`) on the frontend/backend tasks keeps "working, coherent" as a checked acceptance criterion (`paths.build`/`paths.smoke` + `vemo verify`), not a self-report. |
| Potential Impact | Write the problem statement into the task's `Goal` line *before* implementation — `task.spec.md` already asks for this; it becomes the seed of the README/demo narrative for free. |
| Quality of the Idea | `specs/coding.spec.md` "minimal, local, reversible changes" keeps you from cargo-culting a template; the PRD/idea itself is a judgment call VEMO does not automate — see `challenging-assumptions` if VEMO_SKILLS is bound (§6). |

## 4. Codex is mandatory — wire VEMO's fast-feedback ring to it, not just git/CI

VEMO enforces in three rings (`docs/ADAPTERS.md`); rings 2–3 (git + CI) are harness-agnostic already. Ring 1
(the fast, in-loop hook) ships wired to Claude Code. Because this contest requires the *majority of core
functionality* to be built in Codex — and asks for a **Codex Session ID** as evidence — do not build the
graded functionality entirely in a different harness and bolt Codex on at the end; that risks failing Stage
One even with a great product. Two supported shapes:

- **Build directly in Codex CLI** and wire VEMO's dispatcher to Codex's own hook events — see the new
  "Codex CLI" section added to `docs/ADAPTERS.md` in this same change. You keep ring-1 scope/secret/destructive
  checks live while coding in the harness the contest actually grades.
- **Plan/scaffold in one harness, implement the graded core in Codex.** Either way, the task file's
  `Execution Log` is where you note *which* Codex session id produced the core functionality — that line is
  what you copy into the submission form later, so record it as you go, not from memory at deadline time.

## 5. Suggested task decomposition (Python web app: frontend + backend + AI core)

Three tasks, not one — the AI core is the differentiator judges weight most, so it earns its own scope and
its own acceptance criteria rather than being a subtask of "the backend":

1. **Backend/API task** (R1, `scope_in: ["backend/**", "tests/backend/**"]`) — acceptance: build+smoke exit 0,
   one measurable criterion per endpoint you demo.
2. **Frontend task** (R1, `scope_in: ["frontend/**"]`) — acceptance: the demo flow's happy path is scripted
   and passes (this is the same claim the demo video makes — write it as a checkable criterion first).
3. **AI-core-algorithm task** (R1, escalate to R2 if it is the whole pitch — `human_review` + judge is cheap
   insurance the week before a deadline) — acceptance: falsifiable metric(s) for whatever the algorithm claims
   (accuracy/latency/quality threshold), not "works well."

Default to R1 for all three (`task.spec.md` — lowest tier that fits); a solo/duo team at `capability.tier=high`
self-verifies R1 without judge overhead. Reserve the judge pass for the AI-core task if you want an
independent check before you narrate it in the video.

## 6. Submission-readiness checklist (run this before you touch the submission form)

- [ ] Repo is public and a stranger can clone + run it from the README alone (Stage One needs this to even
      evaluate "applies the required APIs/SDKs").
- [ ] README has an explicit section naming Codex/GPT-5.6 and describing *how* they were used (not just "we
      used Codex").
- [ ] The Codex Session ID for the core-functionality thread is recorded (task Execution Log -> copy to the
      submission form).
- [ ] Demo video is <3 minutes, narrated, on YouTube, and shows the product running — not only slides.
- [ ] One category is picked and the description explicitly frames the project inside it.
- [ ] Every acceptance criterion across the three tasks (§5) is `passed` with real evidence
      (`vemo verify` receipt) — an unverified "done" is exactly what `agents/governance-judge.md` exists to
      catch, and a Devpost judge is even less forgiving of it.
- [ ] Run a **pre-submission judge pass**: point `agents/governance-judge.md` at the four official criteria
      (§3 table) instead of only the task's own acceptance criteria, as a dry run of what an external judge
      will see. It cannot evaluate creativity for you, but it will catch unverified claims and scope leaks
      before a real judge does.

## 7. What this playbook deliberately does not change

No edits to `specs/**`, `enforcement/**`, or `vemo.config.yaml` — a deadline is not a reason to weaken scope
containment, the acceptance-before-push gate, or the judge; those are exactly what keeps a rushed week from
shipping an unverified "done." This playbook only tells you which existing levers (risk tier, task
decomposition, the adapter contract) to reach for. See `docs/PLAYBOOK_ADOPTION.md` for the same
don't-copy-wholesale discipline applied to migrating a playbook in general.
