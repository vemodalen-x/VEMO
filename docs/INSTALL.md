# VEMO 安装与维护

VEMO 是放进项目的 AI 开发治理框架。安装向导把框架文件、项目入口、Claude hooks、Git 门禁和 CI 工作流接入一个已有仓库，再运行本地验证。

本次提供的是**源码自带的本地浏览器安装器**，无需 Node.js、前端构建、账号或云服务。运行时使用本机 Python，尚未提供自带 Python 的 EXE、DMG 或签名安装包。

## 1. 安装前准备

| 条件 | 要求 |
|---|---|
| Python | 3.10 或更新版本；命令行能运行 `python3`，Windows 可用 `py -3` 或 `python` |
| Git | 已安装，目标目录已执行 `git init` |
| Bash | 4 或更新版本；现有 Git 门禁使用 Bash。Windows 使用 Git for Windows 的 Bash；macOS 自带 Bash 3 不满足要求 |
| 浏览器 | 能访问本机 HTTP 的现代浏览器 |
| 项目目录 | 当前用户可写、独立 `.git` 目录，支持中文与空格路径 |

安装器会检查 Python、Git、Bash，并实际验证 Bash 中的 `python3` 命令能运行 Python 3.10+，因为已发布的 Claude hooks 使用该命令。Windows 的 `py -3` 可以启动向导，但仍需让 Bash 找到 `python3`。独立 worktree、submodule、重定向 `core.hooksPath` 和链接到其他位置的安装路径会明确拒绝，避免改到共享配置。已有 Git hooks 若与 VEMO 不同，也会显示冲突。

已在 Linux、Python 3.12、Bash 和 Chrome 上执行安装、卸载及浏览器测试。Windows/macOS 启动入口已提供，但本次未在对应操作系统实测。

## 2. 获取完整源码

```bash
git clone https://github.com/vemodalen-x/VEMO.git
cd VEMO
```

这些新入口需要包含本次改动的 checkout。若远端尚未合入本次重构，请使用交付给你的完整工作目录；不要把远端旧版本当作已发布的新安装器。

## 3. 打开图形安装向导

Linux/macOS：

```bash
python3 bin/vemo ui
```

Windows PowerShell：

```powershell
py -3 bin/vemo ui
```

也可以双击 `ui/start.cmd`（Windows），或运行 `bash ui/start.command`（Linux/macOS）。后者在允许执行脚本的桌面环境中也可作为启动入口。

程序自动选择空闲端口并打开浏览器。如果浏览器没有打开，复制终端输出的**完整地址**，包括 `#token=...`。保持终端运行；关闭服务用 `Ctrl+C`。

```bash
python3 bin/vemo ui --no-browser        # 手动打开终端给出的地址
python3 bin/vemo ui --port 8765         # 需要固定端口时
```

服务只监听 `127.0.0.1`；无需管理员权限，也不会注册系统服务或修改全局 Git 配置。

## 4. 按向导安装

1. **选择项目**：粘贴目标 Git 仓库的绝对路径，选择技术栈和使用场景。
2. **检查并预览**：查看运行环境、待创建/合并/更新的文件及冲突。此步骤不写项目文件。
3. **确认安装并验证**：无冲突时执行。页面显示运行状态、检查结果和验证输出。
4. **完成宿主接入**：在项目中重新打开 AI 助手，按宿主自己的提示信任项目，并检查实际 hooks 加载状态。

使用场景（个人/团队/审计）保存在安装清单中，帮助识别部署用途；它不自动改变 VEMO 的风险等级、审批门槛或远端权限，也不代表合规认证。

安装还携带 CI 所需的 `eval/run.py` 和框架测试。框架测试放在 `eval/tests/`，与项目自己的 `tests/` 分开；CI 的框架检查只运行这份测试集。项目自己的 `README.md`、`LICENSE`、`SECURITY.md`、`docs/` 和 `assets/` 不属于载荷，安装器不读取也不修改它们；VEMO 源码仓库的这些文件同样不会被带入项目。只有 `AGENTS.md`、`CLAUDE.md`、`.gitignore` 和 `.claude/settings.json` 采用标记块或结构合并；其他同名且内容不同的受管文件会显示冲突供审查。不会携带源码仓库的历史任务或 `eval/out/` 运行结果。

技术栈预设写入 `vemo.config.preset.yaml`。Python 预设的 smoke 使用 `pytest`，Node 预设使用 `npm test`，C++ 预设使用 `ctest`；这些属于项目自己的构建环境，**安装检查不会代替业务测试，也不会安装这些依赖**。

## 5. 安装后验证什么

安装器实际运行 CLI、`selfcheck`、`extensions --check`，检查所有 Claude hook 事件的接线、CI 文件、Git hooks 的 Bash 语法、内容与可执行权限。仅全部通过才保存成功安装清单。完整 conformance 套件由项目 CI 运行，也可在安装后手动执行 `python3 eval/run.py`。

安装清单位于 `.vemo/install.json`，包含版本、源码 checkout commit（存在时）、实际载荷 SHA-256、每个文件的安装摘要、原始内容备份和执行结果。源码存在未提交修改时，**载荷摘要**标识实际内容，commit 只标识其基础版本。请保留清单，用于升级和卸载。

这个清单用于安装验收。业务任务仍需 `vemo verify` 生成自己的验收证据；它与 `.vemo/run/receipt.json` 是不同的记录。

**远端权限需要在代码托管平台设置**：安装器写入 `.github/workflows/vemo-ci.yml`，但无法据此证明远端 CI 已运行或保护分支已要求 `vemo` 检查。完成业务项目的 CI 适配与分支保护后，服务端门禁才具有相应约束力。

## 升级

在新版完整 VEMO checkout 中打开 UI，选择同一项目、相同技术栈和场景，再次预览并安装。清单记录的文件未被用户修改时可以更新；用户修改过的文件显示冲突。重复安装当前内容保持幂等。

如果新版本删除了旧组件，安装器会要求单独迁移，不会静默保留旧运行文件。技术栈/场景迁移同样需要单独审查。这个版本不提供自动联网升级或跨版本配置迁移。

## 检查与卸载

UI 左侧选择“检查与维护”，填入项目路径：

- **运行安装检查**：验证已登记安装；运行代码摘要不匹配时，先报告漂移，不执行被修改的运行文件。
- **预览卸载**：列出要移除的新增文件和要恢复的原有文件。
- **确认卸载**：仅当清单内文件均未发生后续修改时执行。任何冲突都会停止整个卸载，避免移除运行组件后留下失效 hooks。

任务、验收日志、judge 记录、业务代码、项目自己的文档以及空目录保留。已有项目入口与设置恢复安装前内容。没有 `.vemo/install.json` 的历史手动安装不会被自动卸载。

卸载最好从独立保留的 VEMO 源码目录启动，以便卸载后仍可运行向导。接入其他项目也必须从独立 VEMO 源码目录启动，安装器会拒绝把已受管业务项目当作另一项目的框架来源，防止携带业务项目的规则和配置。

## 失败与恢复

普通写入或验证失败会自动按 `.vemo/setup-journal.json` 回退。恢复按内容摘要核对文件，后续修改的内容会保留并报告冲突。

如果进程被强制结束，先确认原安装进程已经退出；遗留 `.vemo/setup.lock` 时仅删除这个锁文件，然后在 UI 点击“恢复中断操作”。不要删除安装清单或恢复日志来跳过恢复。

```bash
python3 bin/vemo setup recover /absolute/project --apply
```

| 现象 | 处理 |
|---|---|
| 会话失效 / 403 | 使用当前终端输出的完整地址重新打开页面 |
| 目标不是 Git 根目录 | 在项目根运行 `git init`，填写绝对路径 |
| Bash 检查不通过 | 安装/配置 Bash 4+，重新打开终端后启动向导 |
| 已有 hooks 或配置冲突 | 备份并审查该文件，与项目维护者协调合并；安装器不会强制覆盖 |
| 预览后文件已变化 | 重新预览，确认新的变更清单 |
| 运行文件发生变化 | 审查漂移文件，恢复已知内容或进行受审查的升级 |
| 安装验证失败 | 展开错误和验证输出，处理根因；成功回退后可直接重试 |

## 无图形环境的相同流程

CLI 与 UI 调用同一个安装服务。下面的安装与卸载命令默认只预览；加入 `--apply` 执行。

```bash
python3 bin/vemo setup install /absolute/project --preset python --profile solo --json
python3 bin/vemo setup install /absolute/project --preset python --profile solo --apply
python3 bin/vemo setup check /absolute/project --json
python3 bin/vemo setup uninstall /absolute/project --json
python3 bin/vemo setup uninstall /absolute/project --apply
```

可以把预览返回的 `plan_id` 传给 `--plan-id`，要求执行时目标与预览一致。UI 自动执行这个核对。

下一步：[开始使用](USAGE.md) · [设计与治理](DESIGN_LITE.md)
