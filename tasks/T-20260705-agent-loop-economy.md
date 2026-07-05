---
id: T-20260705-agent-loop-economy
risk: R2
state: AcceptancePassed
scope_in: ["enforcement/**", "specs/**", "vemo.config.yaml", "bin/**", "eval/**", "agents/**", "docs/**", "tasks/**", "AGENTS.md", "SECURITY.md", "README.md", "CHANGELOG.md", "VERSION", ".vemo/**", ".claude/**", ".github/**", ".gitignore", ".gitattributes"]
scope_out: ["presets/**", "assets/**", ".internal/**", "skill/**"]
trifecta: []
acceptance:
  status: passed
  build_exit: 0
  smoke_exit: 0
  evidence: ".vemo/run/T-20260705-agent-loop-economy-20260705-223057.log"
judge:
  required: true
  verdict: pass
  violations: []
  evidence_checked: ["eval-68/68-exit0", ".vemo/run/T-20260705-agent-loop-economy-20260705-223057.log", "desensitization-clean-safe-to-publish", "stuck-loop-live-fire-exit0/exit2", "version-all-1.2.0"]
  confidence: high
approved_commands: []
owning_chat: chat-20260705-fable-loop-econ
heartbeat: 2026-07-05T22:37
---

# T-agent-loop-economy — 2026 同行对标复审：loop 经济性 + 缺口修复（v1.2.0）

## Goal
按 2026 agent-harness 同行实践（Anthropic 长时程 harness、OpenAI Codex 守护栏/AGENTS.md、OWASP Agentic
Top10）修复本轮 code review 发现的缺口，并落地 token 经济性 P0：治理开销随风险缩放，不随活动量缩放。

## Scope (In / Out)
- In: validator 新 verbs（context/judge-brief/heartbeat）、budget 卡死检测、多任务 acceptance 门修复、
  R2 提级（.gitignore/.gitattributes，judge-2 前轮建议）、specs/docs/CLI/eval 同步。
- Out: skill 体系、presets、消费方项目。

## Pass/Fail Criteria (EARS, measurable)
- [Build] `python3 eval/run.py` SHALL exit 0（全部用例 PASS，含本轮新增）。
- [Correctness] `task_state.py context` SHALL 输出含 tier/mode/task/gate 状态的机读简报（≤20 行）。
- [Correctness] `task_state.py judge-brief --lens correctness` SHALL 输出含 claims/gates/scope 表的案卷。
- [Correctness] `task_state.py heartbeat` SHALL 原位更新活动任务 heartbeat（无需 agent 编辑文件）。
- [Correctness] `gate-check acceptance-before-push --task-file A --task-file B` SHALL 对 B（低于
  AcceptancePassed 的 R1+）返回 block（多任务 range 全覆盖，修复 7ed211f 只查 tasks[0] 的缺口）。
- [Safety] 连续 3 次相同 Bash 命令 SHALL 触发 stuck-loop：人在环 → advisory note；auto ON → exit 2。
- [Safety] `tier-required --paths .gitignore` SHALL 返回 R2（judge-2 建议落地：审计可见性文件提级）。
- [Correctness] `task_state.py selfcheck` SHALL OK（新 verbs 不引入死键/断标签）。

## Plan
1. validator: `context`（机读简报）、`judge-brief --lens`（judge 案卷）、`heartbeat`；budget_tick 增
   recent-bash 签名链（3 连同 → stop:stuck-loop，guard 按 auto 状态转 advisory/硬停）。
2. gate_check("acceptance-before-push") 遍历 task_files 全集；pre-push 从 stdin refs/VEMO_DIFF_RANGE
   收集 range 内变更任务文件并传 --task-file。
3. config: R2_critical.match_paths += .gitignore/.gitattributes；run_budget 注释补 stuck 语义。
4. 接线: bin/vemo（context/judge-brief/heartbeat verbs + HELP）、hooks session-start 打印 context 简报、
   AGENTS.md 第一步改跑 context、governance-judge.md 改为案卷优先、task.spec 日志一行制。
5. eval: +7 用例（context/judge-brief/heartbeat/stuck×2/multi-task acceptance/.gitignore R2）；
   README CLI 表 + CHANGELOG/VERSION 1.2.0。

## Execution Log
- 2026-07-05T11:42 计划创建（code review + 同行对标结论驱动；judge-brief 本轮 judge 即狗粮）。
- 2026-07-05T17:14 validator 新 verbs（context/judge-brief/heartbeat）接线 + budget stuck-loop 签名链落地。
- 2026-07-05T17:14 pre-push 读 stdin refs 收集 range 内任务；两份 CI yml 共享 VEMO_DIFF_RANGE；config R2 提级。
- 2026-07-05T22:30 发布级 code review（3 只读 agent：脱敏/文档符合设计/架构可加载）：脱敏内部项目名、
  README CLI 表补 3 verb + demo 68/68、VERSION/config/badge→1.2.0、CHANGELOG 1.2.0、.gitignore 补 IDE、
  docs/html 全量重生成。eval 68/68、selfcheck OK、verify 收据 build0/smoke0。

## Acceptance Result
- [Build] `python3 eval/run.py` → **68/68 PASS, exit 0**（新增 7 用例：context/judge-brief/heartbeat/
  multi-task-acceptance/.gitignore-R2/stuck×2），evidence `eval/out/report.json` + verify 收据
  `.vemo/run/T-20260705-agent-loop-economy-20260705-223057.log`（build_exit 0, smoke_exit 0）。
- [Correctness] `vemo context` → 8 行机读简报（tier/mode/task/gate/budget/rules），≤20 行达标。
- [Correctness] `vemo judge-brief --lens correctness` → 输出 CLAIMS/CRITERIA/JUDGE HISTORY/GATES/RECEIPT/
  CHANGES(逐文件 scope 判定)/LENS 清单/RULES；git-less sandbox 优雅降级（eval 断言覆盖）。
- [Correctness] `vemo heartbeat` → 原位改写 front-matter heartbeat（eval 断言旧值消失）。
- [Correctness] 多任务 `gate-check acceptance-before-push --task-file A --task-file B` → 对未验收 B 返回
  `block:… [task=TB]`（eval 断言）。
- [Safety] stuck-loop：3 连同 Bash → 人在环 advisory exit 0 / auto ON hard-stop exit 2（eval 双断言）。
- [Safety] `vemo tier .gitignore` / `.gitattributes` → **R2**。
- [Correctness] `vemo selfcheck` → OK（新 verbs 无死键/断标签）；`vemo selfcheck` 现正确透传退出码。

## Auto-Mode Decisions
（无 — 人在环。）

## Conclusion
Outcome: **accepted**（1.2.0 首个公开 release 就绪）· Decision: **continue**（commit/push by vemodalen-x）·
Key Evidence: eval 68/68 exit 0 + `vemo verify` 收据（build0/smoke0，log 20260705-223057）+ selfcheck OK +
两轮独立 judge 均 pass（22:34 correctness / 22:35 safety，溯源 `.vemo/judge.jsonl`，各自负向测试/live-fire
确认断言可失败、守卫完好、脱敏干净可发布）· Risk: low（治理面 R2 变更，双 judge + CI 服务端复核兜底）·
Next Action: vemodalen-x 账号 commit/push；本地 judge-brief 狗粮实测省 ~3-4× judge 探索成本。
