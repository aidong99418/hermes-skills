---
name: brain-optimization-methodology
description: 机器猫大脑系统优化方法论——多轮迭代架构推演，从散架齿轮到高效大脑的完整思考路径。核心：按响应时间分配资源、5层架构、推理→检索反转。
tags: [brain, architecture, optimization, system-design]
owner: hermes
created: 2026-05-23
version: 1.0
validate: none
---

# 机器猫大脑优化方法论

## 背景

2026-05-23下午与董哥进行的多轮架构推演，从"本地vs云"选边站，到最终形成5层高效混合架构。过程经历6次迭代、3次被否定、3次被肯定。

---

## 架构演进史（6轮迭代）

### 第1轮 ❌ 被否定
- **方案：** 本地全做，GitHub只备份
- **问题：** 没有利用云端能力

### 第2轮 ❌ 被否定
- **方案：** GitHub Actions替代本地计算
- **问题：** 变成"云电脑"，网络差时体验崩塌，NAS白买

### 第3轮 ✅ 被肯定（接近正确）
- **方案：** 智能混合，按响应时间分配
  - 实时层100%本地（brain检索3ms）
  - 离线层GitHub Actions（批量预处理）
  - 结果备份GitHub

### 第4轮 ✅ 被肯定
- **方案：** 三层最优组合
  - 实时层：本地brain(3ms) + Ollama推理
  - 准实时：本地抓取→分析→写brain→备份
  - 离线层：GitHub Actions做算力消耗大的预处理
- **关键数据：**
  - 本地brain检索：3ms（加载2.4ms + 搜索0.7ms）
  - GitHub API查文件：866ms（慢300倍）
  - HN API：0.6s，ArXiv：1.2s

### 第5轮 ✅ 被肯定（补充）
- **方案：** 5个被忽视的深层维度
  1. 知识新鲜度+置信度（带时间戳和confidence字段）
  2. 盲区检测（主动标记"我不懂的部分"，不装懂）
  3. 工作记忆层（对话上下文写入brain/working_memory.json）
  4. 检索→推理反转（先推理假设再精准检索，不是拼凑）
  5. 好奇心引擎（空闲时主动推知识给用户）

### 第6轮 ✅ 最终落地
- **方案：** 5层完整架构
  - 工作记忆层（上下文）
  - 元认知层（监控自己：知道什么/不知道什么/知识新鲜吗）
  - 推理引擎（先假设后验证）
  - 检索引擎（精准拉取，不拼凑）
  - 长期记忆层（带置信度+新鲜度+热度）

---

## 核心设计原则

### 1. 响应时间驱动分配
```
<100ms（必须本地）：brain检索、Ollama推理、用户交互
>1s（可用云）：外部获取、批量预处理、备份
事件驱动（Actions）：GitHub网页更新时触发通知
```

### 2. 推理→检索反转
```
传统（拼凑）：
  检索brain → 把所有命中扔给Ollama → 拼凑答案

更优（因果链）：
  先推理"加载慢可能原因" → 按假设精准检索 → 验证 → 回答
  检索量：397块 → 可能5块
```

### 3. 元认知监控
```
每个知识碎片带：
  - created/updated（新鲜度）
  - confidence（置信度，1-10分）
  - source（external/internal）
  - validated（是否被验证过）
  - usage_count（被调用次数）

权重 = freshness_decay(时间) × confidence × usage_count
```

---

## 推荐落地顺序

| 优先级 | 改动 | 难度 | 预期收益 |
|--------|------|------|---------|
| **P0** | 对话自动触发brain_think（每条消息先判tier） | 中 | 大脑从手动变自动 |
| **P0** | tier3真实并行派发3模型 | 小 | 复杂问题3→10秒 |
| **P1** | 工作记忆层（上下文写入brain/） | 小 | 检索精准度提升 |
| **P1** | 检索→推理反转 | 中 | 检索量减少100倍 |
| **P1** | brain写完自动rebuild | 小 | 新知识立刻可检索 |
| **P2** | 好奇心引擎（空闲推知识） | 中 | 用户粘性增加 |
| **P2** | GitHub增量备份 | 小 | 知识不丢 |
| **P3** | 60MB无效索引清理 | 极小 | 干净 |

---

## 关键文件

- `/opt/data/brain/` — 核心知识目录
- `/opt/data/brain/neural/connections.json` — 推理路径（10条连接）
- `/opt/data/brain/problem_types/` — 5个问题类型决策树（debugging/coding/architecture/research/decision/data_analysis）
- `/opt/data/scripts/brain_thinker.py` — 思考引擎
- `/opt/data/scripts/brain_retriever.py` — BM25检索（397块缓存）
- `/opt/data/scripts/external_fetcher.py` — 外部获取（ArXiv/HN/SO）
- `/opt/data/scripts/brain_invoke.py` — 轻量包装
