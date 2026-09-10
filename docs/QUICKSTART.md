# Quickstart：通过 UI 接入项目

> Diátaxis: this is a **tutorial** — on rails, one destination, one "aha". For *why* it works see
> [MENTAL_MODEL.md](MENTAL_MODEL.md); for every option see [REFERENCE](../vemo.config.yaml) / `vemo explain`.

**The aha you're going for:** an out-of-scope edit gets *blocked automatically* — governance you don't have to remember.

## 1. 打开安装向导

准备 Python 3.10+、Git、Bash 4+ 和现有 Git 仓库。在完整 VEMO checkout 中运行：

```bash
python3 bin/vemo ui
```

Windows 可使用 `py -3 bin/vemo ui` 或双击 `ui/start.cmd`。
若浏览器未自动打开，复制终端输出的完整地址。

## 2. 选择项目并安装

粘贴 Git 项目根目录的绝对路径，选择技术栈，点击“检查并预览”。
检查无冲突后点击“确认安装并验证”，查看真实运行结果。之后在目标项目重新打开助手，
确认宿主加载了项目 hooks。完整条件、平台限制和恢复办法见 [INSTALL.md](INSTALL.md)。

没有浏览器时使用同一服务：

```bash
python3 bin/vemo setup install /absolute/your-project --preset python
python3 bin/vemo setup install /absolute/your-project --preset python --apply
```

CI 文件会随安装接入；远端需另外配置保护分支的必需 `vemo` 检查。

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
python3 bin/vemo workflow    # Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect
python3 bin/vemo explain gates
```
On Windows, use `python bin/vemo status`.

## Next

Use the delivery loop when the request is larger than a one-file fix: `vemo workflow`, then `/office-hours`,
`/plan-ceo-review`, `/plan-eng-review`, `/review`, `/qa`, `/ship`, and `/retro`. Each role is a thin skill;
the task file, receipt, judge log, and CI remain authoritative.
- 中文首次任务与验收流程 → [USAGE.md](USAGE.md)。
- Going unattended (CI / overnight)? → [HOWTO: auto mode](MENTAL_MODEL.md#auto-mode) — but read the stop-rules note.
- Want the *why*? → [MENTAL_MODEL.md](MENTAL_MODEL.md). Want the full map? → [INDEX.md](INDEX.md).

> Tip: add `bin` to PATH (`export PATH="$PWD/bin:$PATH"`) so you can type `vemo status` directly.
