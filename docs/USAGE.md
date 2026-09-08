# VEMO 使用指南

安装完成后，在**目标项目**中使用 VEMO。它把任务边界、风险分类、验证证据和交付约束放进项目，帮助人和 AI 助手围绕同一份可核查记录协作。

## 第一次使用

先按[安装说明](INSTALL.md)接入项目，再在项目根目录运行：

```bash
python3 bin/vemo context
python3 bin/vemo status
```

`context` 提供简短的当前任务、范围、门禁和预算摘要。Windows 可把 `python3` 替换成可用的 `python` 或 `py -3`。无需修改 PATH。

重新打开项目中的 AI 助手。项目 `AGENTS.md` 包含 VEMO 的入口协议，`CLAUDE.md` 指向该入口；Claude 的 hooks 配置合并进 `.claude/settings.json`。其他宿主需要匹配的 hook 适配器才能获得工具调用前拦截，详见 [ADAPTERS.md](ADAPTERS.md)。

## 开始一个有明确验收标准的任务

可以直接告诉助手：

> 为订单导出功能修复中文文件名。范围是 `src/export/` 和 `tests/export/`。完成标准是已有测试通过，并新增中文文件名的回归用例。请按项目 AGENTS.md 执行并给出真实验证结果。

助手应先做任务分类、风险分级、创建计划与范围，然后执行。手工创建任务也可使用：

```bash
python3 bin/vemo tier src/export/ tests/export/
python3 bin/vemo task create --title "修复导出中文文件名" --risk R1 \
  --scope 'src/export/**' 'tests/export/**' --profile full
```

这是 Bash 示例。PowerShell 请写成一行，并使用相同的路径字符串。将创建结果中的任务 ID 用于会话绑定：

```bash
python3 enforcement/validators/task_state.py bind --session YOUR_SESSION_ID --task TASK_ID
```

打开新建任务文件，补充 Goal、Scope、可测量的 Pass/Fail Criteria 和 Plan。`R1` 只是本例，实际必须采用 `vemo tier` 判定；不要把高风险任务改成 R1 来绕过审查。

## 三档风险意味着什么

| 风险 | 适用情况 | 工作流程 |
|---|---|---|
| R0 | 小型文档等低影响改动 | 简短计划、执行、完成 |
| R1 | 常规功能与缺陷修复 | 计划、实现、真实验证 |
| R2 | 核心、权限、治理规则等关键改动 | 计划审查、实现、独立评审、验证与交付程序 |

风险与模型能力共同决定流程深度。更强的模型可减少操作说明，但不能放宽范围、验收或审计约束。完整规则以项目 `specs/` 和机器检查结果为准。

## 验证并提交交付结果

先检查 `vemo.config.preset.yaml` 中的 build/smoke 是否适合自己的项目，再执行：

```bash
python3 bin/vemo verify
python3 bin/vemo report
```

`verify` 实际运行任务对应的验证命令，并生成日志与机器回执。`report` 汇总观察到的门禁事件、验证记录与接入缺口。仅仅修改任务文件中的 `passed` 不能代替执行。

提交、推送仍由项目自己的 Git 和审批流程处理。需要独立评审的任务必须提供合规的 judge 记录。UI 安装不会自动提交、推送、开启全自动模式或修改 Git 身份。

## 被门禁拦截时

先读错误给出的规则和文件名，再修正原因：

- 范围外修改：确认是否属于目标；需要扩展时更新经过确认的任务范围。
- 缺少计划：补充任务计划和可验证标准。
- 验收未通过：运行规定验证，处理失败，保留证据。
- 缺少独立评审：按照项目风险/能力矩阵运行独立 judge。

不要禁用 hooks 或用忽略验证的参数把错误藏起来。`vemo explain gates`、`vemo explain verify` 可以查看简短解释。

## 常用入口

| 想做什么 | 命令 / 页面 |
|---|---|
| 安装到另一项目或维护安装 | `python3 bin/vemo ui` |
| 当前任务与约束 | `python3 bin/vemo context` |
| 确认路径所需风险 | `python3 bin/vemo tier <paths...>` |
| 执行验收 | `python3 bin/vemo verify` |
| 查看观察结果 | `python3 bin/vemo report` |
| 查看职责与能力边界 | `python3 bin/vemo platform --check` |
| 检查扩展装配 | `python3 bin/vemo extensions --check` |
| 安装、升级、卸载故障 | [INSTALL.md](INSTALL.md) |

`vemo start` / `vemo init` 保留为历史接入命令，旧安装方式不会自动获得新的安装清单或回退能力。新项目统一使用 UI 或 `vemo setup`。`vemo eval` 检查框架本身；安装器将所需框架测试放在 `eval/tests/`，不会把业务项目的 `tests/` 当作框架 conformance 测试集。业务测试继续由 `vemo verify` 按项目自己的命令执行。

下一步：[理解设计](DESIGN_LITE.md) · [完整文档索引](INDEX.md)
