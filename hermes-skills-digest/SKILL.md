---
name: hermes-skills-digest
description: 从herrmes-skills GitHub仓库学到的最佳实践摘要——模型分层、主动思维、自进化、MCP集成、多Agent协作
version: 1.0.0
author: Hermes Agent
tags: [brain, architecture, ollama, mcp, multi-agent]
---

# hermes-skills 精华摘要

从 aidong99418/hermes-skills 仓库学到的核心知识体系，已内化为本地brain知识。

## 1. Ollama模型四层架构（已写入brain/knowledge/model_tier_system.md）

- **fast层**: smollm2:1.7b — 简单查询，<1秒
- **worker层**: qwen2.5:3b — 工具调用/后台任务
- **expert层**: deepseek-r1:7b — 复杂推理/架构分析
- **tool层**: qwen2.5:7b-instruct-q4 — 工具调用链

降级链：expert → worker → fast，自动降级保可用。

## 2. 三层思考引擎（brain_thinker）

- **tier1**: 直接执行，0检索
- **tier2**: brain检索+外部获取，<5秒
- **tier3**: 3模型并行团队派发，<15秒

核心：问题先判断难度，再分配资源，避免"简单问题用大模型浪费，复杂问题用小模型太浅"。

## 3. 主动思维规范（machine-cat-guardian）

每次对话前自检：
- 容器状态/磁盘空间/日志错误/僵尸进程
- vision工具可用性
- 同类问题反复出现

两层自愈：静默修复优先，失败才通知用户。

## 4. 自进化五层架构

```
好奇心动 → 盲区检测 → 反馈闭环 → 知识沉淀 → 质量评估
```

- dialog_watchdog: 监控sessions，触发brain思考
- self_observer: 记录行为日志
- feedback_tracking: 收集用户反馈
- confidence_tracking: 量化置信度

## 5. MCP集成（native-mcp）

通过config.yaml配置MCP服务器，工具自动注册为`mcp_{服务器}_{工具}`格式：
- github: npx @modelcontextprotocol/server-github
- filesystem: npx @modelcontextprotocol/server-filesystem
- time: uvx mcp-server-time

## 6. 多Agent协作模式

| 场景 | 方案 |
|------|------|
| 快速并行子任务 | delegate_task（子agent） |
| 长时间独立任务 | tmux + hermes独立进程 |
| 团队思考 | 3模型并行派发（deepseek/qwen/smollm） |

## 7. 静默运行原则

- cron任务默认deliver=local
- 只在连续失败/紧急情况才weixin通知
- 用户不应被正常的系统运行打扰

## 使用方式

当需要执行相关任务时，自动检索这些brain文件获取最佳实践：
- `/opt/data/brain/knowledge/model_tier_system.md`
- `/opt/data/brain/reasoning_pattern/multi_agent_patterns.md`
- `/opt/data/brain/reasoning_pattern/self_evolution_pattern.md`
- `/opt/data/brain/principles/cron_silent_mode.md`
- `/opt/data/brain/tool_templates/mcp_integration.md`
