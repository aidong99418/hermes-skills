---
name: brain-team-architecture
description: 机器猫团队大脑架构 — 三层思考+神经网络+知识流转闭环
tags: [brain, neural, team, architecture]
version: 1.0
updated: 2026-05-23
---

# 机器猫团队协作架构 v1.0

## 三层思考架构

### ⚡ Tier1 快速通道
- **触发：** 简单确定，"帮我看/查/剩多少"
- **行为：** 直接回答，不检索brain

### 🧠 Tier2 思考通道
- **触发：** 复杂问题，含"思考/分析/区别/原理/怎么"
- **行为：** brain检索 → 无结果 → 外部获取 → 写brain → 回答

### 🔴 Tier3 团队协作
- **触发：** 重大决策，含"架构/设计/安全/权衡"
- **行为：** 派发各本地模型 → 汇总 → 整合判断

## 团队角色
- deepseek-r1:7b = 推理专家
- qwen2.5:7b = 工具专家
- qwen2.5:3b = 打工仔
- smollm2:1.7b = 快手

## 核心文件
- `/opt/data/scripts/brain_thinker.py` — 思考引擎
- `/opt/data/scripts/brain_retriever.py` — BM25+中文扩展检索
- `/opt/data/brain/neural/connections.json` v3.0
- `/opt/data/brain/neural/inference_paths.json` v3.0

## 知识闭环
外部获取 → 分析验证 → 存入brain → 重建缓存 → 本地模型学习
