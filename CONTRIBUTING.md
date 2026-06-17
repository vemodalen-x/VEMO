# Contributing to VEMO

Thanks for helping! VEMO is small on purpose — keep changes tight and well-scoped.

## The short version
- **VEMO governs itself.** Changes flow through VEMO's own task lifecycle, and the same hooks + CI that protect
  consumers run on this repo. So: start a task file, declare its `scope_in`, keep edits inside it.
- **Every PR includes:** a `CHANGELOG.md` entry under the current version, a `VERSION`/`vemo.config.yaml`
  version bump if it's a release, and a `Co-Authored-By:` trailer in at least one commit.
- **Keep the brevity discipline.** Specs have line caps; a long safety spec is a smell (if it can't be a hook,
  it isn't really "hard"). Advice goes in `coding.spec` / docs, not in `safety.spec`.

## Dev setup
```bash
git clone https://github.com/vemodalen-x/VEMO.git && cd VEMO   # (adjust owner to your fork)
python3 bin/vemo doctor          # config + tooling sanity
python3 bin/vemo init            # install hooks + git pre-commit locally
```
- Validators/CLI are **stdlib-only Python** (no third-party deps) — keep them that way for portability.
- Enforcement scripts derive their repo root from their own location (not `git`), so they work even when VEMO
  is nested inside another repo. Preserve that.

## Good first contributions
- A new **preset**: `presets/<stack>.yaml` (build/smoke/test/exclusions for a stack).
- A new **eval scenario**: `eval/scenarios/SC*.md` asserting a gate fires (or doesn't false-fire).
- A **Windows hook runner** (pure-Python) so hooks run natively without git-bash (tracked limitation F5).
- A `vemo explain` topic, or a docs clarification (keep each doc to its one Diátaxis job).

## What to avoid
- Adding a "hard gate" that is only prose — if it matters, make it a hook/CI check + a machine-readable field.
- Weakening a mechanical guard to make something convenient. Convenience belongs in risk tiers / capability
  tiers / auto mode, never in removing a safety rail.
- Third-party runtime dependencies in the core enforcement path.

## Reporting issues
Tell us: what you ran (`vemo …`), what you expected, what happened, and `vemo doctor` output. For a gate that
fired wrongly, include the task front-matter and the offending path.
