---
name: workflow
description: >
triggers: ["配置触发规则时激", "调度", "测试到", "需要将脚本接入", "脚本接入", "验证命令", "定时任务", "每日运行"]
  工作流自动化技能库 — 覆盖脚本→Cron调度→Playwright E2E→代码插件→Git学习→触发配置的完整自动化链路。
  触发场景：需要将脚本接入Cron、编写E2E测试、GitHub技能学习、配置触发规则时激活。
tags: [workflow, cron, playwright, automation, testing, git, trigger]
owner: hermes
created: 2026-05-24
version: 1.0
updated: 2026-05-24
---

# Workflow — 工作流自动化

覆盖从脚本开发、Cron调度、E2E测试到Git学习、触发配置的完整自动化链路。

---

## 核心文档

### script-to-cron-integration
> 新脚本接入 `auto_learning.py` 主流程的标准步骤。含标准插入模板（try-except包裹）、subprocess调用模式、验证命令。
触发词：脚本接入Cron、cron自动化、每日运行、定时任务。
详细文档：`script-to-cron-integration/SKILL.md`

### playwright-development-workflow
> Playwright E2E测试开发工作流 — 安装、页面对象模型、常用API（click/fill/screenshot/pause）、调试技巧、配合vision分析失败截图。
触发词：E2E测试、Playwright、端到端测试、Web测试、自动化测试。
详细文档：`workflow/playwright-development-workflow.md`

### git_learning_workflow.md
> GitHub技能学习→本地模型同步工作流 — 克隆→扫描→并行读取→知识沉淀→索引重建→验证检索→推送hermes-addons。
触发词：把Git里的好东西都学习掌握、仓库同步、skill学习。

### claude-code-plugin-creation.md
> Claude Code插件创建指南（addyosmani/OpenCode Skill驱动执行模型）。
技能优先原则、Intent→Skill映射、生命周期隐式命令、Personas/Skills/Commands三层编排。

### opencode-skill-model.md
> OpenCode skill驱动执行模型设计 — 技能优先原则、生命周期（DEFINE→PLAN→BUILD→VERIFY→REVIEW→SHIP）、并行扇出+合并编排规则。

### trigger_config.md
> 机器猫大脑自适应触发机制v2.0 — P0每次必检→P1问题解决后沉淀→P2每日自动更新→P3定期维护。
关键词→模块映射表（P0-P3优先级）、自检清单、brain内容质量标准。

---

## 覆盖范围速查

| 阶段 | 工具/文档 |
|------|----------|
| **脚本开发** | 独立Python/Shell脚本 |
| **Cron调度** | `script-to-cron-integration`（接入auto_learning.py）|
| **E2E测试** | `playwright-development-workflow` |
| **代码助手集成** | `claude-code-plugin-creation`（Claude Code插件）|
| **Git学习** | `git_learning_workflow` |
| **Skill模型** | `opencode-skill-model`（OpenCode执行模型）|
| **触发配置** | `trigger_config`（brain自适应触发机制）|

### unified_learning.py 锁文件维护

`unified_learning.py` 使用 PID-based lock (`/tmp/unified_learning.lock`) 防重复运行。进程意外退出时锁残留，导致后续所有 cron 静默跳过（日志只显示 `已有实例在跑，跳过`）。

**诊断命令**：
```bash
# 查看是否有残留锁
cat /tmp/unified_learning.lock
pgrep -fa "python3.*unified"

# 如果锁中PID已死，手动清理
rm -f /tmp/unified_learning.lock
rm -f /tmp/unified_learning_daemon.pid  # 可能同时残留
```

**触发条件**：cron 执行但日志反复出现 `[WARN] 已有实例在跑，跳过` 且无对应 Python 进程

**完整修复流程**：锁清理 → 确认无残留进程 → 重新运行

### script-to-cron-integration

## 触发词

- 脚本接入Cron、cron自动化、每日运行
- E2E测试、Playwright、端到端
- 把Git里的好东西都学习掌握
- Claude Code插件、OpenCode
- 触发机制、关键词触发、自适应触发
