# VEMO ⟶ built on Wildpanda, but a different framework (and how we keep it that way)

> The honest way to *not* be "a Wildpanda ripoff" is not to hide the lineage — it's to **credit it openly,
> contribute back, and ship a substantively different core.** This page is that statement.

## 1. Attribution (loud, on purpose)
VEMO began from **[Wildpanda](https://github.com/BST-AII/Wildpanda)** (MIT) — its philosophy and several of its
designs are excellent and we reuse them with credit. Wildpanda is named in the README, the CHANGELOG, this doc,
and the skill that **contributes improvements back upstream** (`governance-contribute`). Same license (MIT);
no attribution stripped. Hiding a derivation is what makes it plagiarism; crediting it is what makes it lineage.

## 2. What we KEPT (and credit)
Four principles (evidence over assertion, repo-as-truth, template/instance split, human-decides-irreversible);
the multi-session **concurrency / takeover** model; the spec-driven, drop-in, zero-runtime-dependency shape.

## 3. What makes it a *different framework*, not a fork
A fork tweaks; VEMO **changes the architecture**. Wildpanda's governance is **prose the model is trusted to
obey**; VEMO's load-bearing layer doesn't exist in Wildpanda at all:

| Distinct in VEMO (absent in Wildpanda) | Why it's transformative, not copied |
|---|---|
| **`enforcement/`** — hooks + CI backstop + a machine-readable task-state validator | the gates are *mechanism*, not text — a different control model |
| **Capability-monotonic governance** (`capability.spec`, `verify-plan`) | ceremony↓ / verification↑ as models strengthen — a novel design axis |
| **Executable conformance harness** (`eval/run.py`) | the framework *proves* its gates fire (and caught a real bug doing so) |
| **`vemo` CLI + per-stack presets + Diátaxis docs** | a different adoption/UX surface |
| **Auto-mode + run-budget stop rules** | unattended-run safety Wildpanda has no concept of |

Different **identity** too: a different name and origin story (*vemödalen*), a **velocity-first** thesis, and
the "two dials" (risk × capability) mental model. The overlap is the *vocabulary of good governance*; the
implementation is ours.

## 4. The "is this just a copy?" test — and our answer
- *Could you produce VEMO by find/replacing names in Wildpanda?* No — `enforcement/`, the validator, the CLI,
  the eval harness, and the capability-monotonic specs are new code with no Wildpanda counterpart.
- *Did you take Wildpanda's text verbatim?* The kept *ideas* are re-expressed and slimmed (e.g. Wildpanda's 7
  skills, ~1006 lines of prose, became ~205 lines + 2 real scripts); the new layers are original.
- *Do you compete with or starve Wildpanda?* No — `governance-contribute` exists precisely to push reusable
  improvements **back** to Wildpanda. Healthy lineage, not extraction.

## 5. If you maintain Wildpanda and want changes merged back
Open an issue; the `governance-contribute` skill drafts the PR (template-owned files only, `Co-Authored-By`).
We'd rather strengthen the upstream than divergently clone it.

> Bottom line: VEMO is to Wildpanda what a production engine is to a great blueprint — same intent, a different
> machine, full credit to the drafter.
