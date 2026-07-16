# Quickstart (5 minutes)

> Diátaxis: this is a **tutorial** — on rails, one destination, one "aha". For *why* it works see
> [MENTAL_MODEL.md](MENTAL_MODEL.md); for every option see [REFERENCE](../vemo.config.yaml) / `vemo explain`.

**The aha you're going for:** an out-of-scope edit gets *blocked automatically* — governance you don't have to remember.

## 1. Drop VEMO into your repo
```bash
cp -r VEMO/{AGENTS.md,vemo.config.yaml,specs,enforcement,agents,tasks,bin} your-repo/
cd your-repo
```

## 2. Preview the product path
```bash
python3 bin/vemo start --preset python    # or: node | cpp | docs
```
On Windows, use `python bin/vemo ...` if `python3` is not installed.

This command is read-only. It detects the stack, shows the files it would touch, and makes the first value
step explicit. Apply it after reviewing the plan:

```bash
python3 bin/vemo start --preset python --profile solo --apply
```

That applies the preset, installs local hooks + Git pre-commit/pre-push, and creates task storage. Use
`--profile team` when multiple people or Agents will edit the repository.

**Make it authoritative** (local hooks are fast feedback; the *guarantee* is server-side):
```bash
mkdir -p .github/workflows && cp enforcement/ci/vemo-ci.yml .github/workflows/
# then require the "vemo" check in your branch protection rules
```

## 3. Start a task, then code
```bash
cp tasks/_TASK_TEMPLATE.md tasks/T-myfirst.md
# edit the front-matter: set  scope_in: ["src/feature/**"]   and  risk: R1
```
Now ask your agent to make a change. Try to edit a file **outside** `src/feature/**`:

```
[VEMO] BLOCKED (safety.spec#1): '<that file>' is outside the active task's scope_in.
```

**That's the aha.** You didn't have to police it — the hook did. Everything else (risk tiers, the judge,
auto mode, run budgets) builds on this one idea: *the important rules are mechanical, not prose.*

## 4. See where you stand, any time
```bash
python3 bin/vemo status      # tier / enforcement / budget / auto mode / active task
python3 bin/vemo report      # observed events / verification / setup gaps / next best actions
python3 bin/vemo explain gates
```
On Windows, use `python bin/vemo status`.

## Next
- Going unattended (CI / overnight)? → [HOWTO: auto mode](MENTAL_MODEL.md#auto-mode) — but read the stop-rules note.
- Want the *why*? → [MENTAL_MODEL.md](MENTAL_MODEL.md). Want the full map? → [INDEX.md](INDEX.md).

> Tip: add `bin` to PATH (`export PATH="$PWD/bin:$PATH"`) so you can type `vemo status` directly.
