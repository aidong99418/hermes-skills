---
name: brain-retriever-usage
description: 机器猫大脑检索系统使用规范 — 三层思考+外部获取+知识沉淀完整闭环
tags: [brain, rag, thinking, external-fetch]
version: 4.0
updated: 2026-05-23
---

# brain-retriever-usage

## 重大更新 v4.0（2026-05-23）
外部知识获取→分析→存入brain的完整闭环已打通。

## 思考三层架构

### ⚡ Tier1 快速通道
- **触发：** "帮我看/查/剩多少/在哪"，简单确定
- **行为：** 直接回答，不检索brain

### 🧠 Tier2 思考通道
- **触发：** 含"思考/分析/区别/原理/怎么/为什么"
- **行为：** brain检索 → 不足 → 外部获取(ArXiv+HN+SO) → Ollama分析 → 存brain → 回答
- **阈值：** brain最高分 < 5.0 时触发外部获取

### 🔴 Tier3 团队协作
- **触发：** 含"架构/设计/安全/权衡"
- **行为：** 派发各模型 → 汇总 → 整合判断

## 核心文件

| 文件 | 作用 |
|------|------|
| `/opt/data/scripts/brain_thinker.py` | 思考引擎，三层判断+自动外部获取 |
| `/opt/data/scripts/brain_retriever.py` | BM25检索+中文扩展（388块缓存） |
| `/opt/data/scripts/external_fetcher.py` | 外部获取(ArXiv+HN+SO)→Ollama分析→存brain |
| `/tmp/brain_bm25_cache.json` | 缓存 |

## 外部获取数据源

- **ArXiv** — 学术论文（最可靠）
- **HackerNews** — 行业热帖
- **StackOverflow** — 技术问答

## 知识闭环

```
问题 → brain检索 → 不足 → 外部获取 → Ollama分析 → 写brain → 重建缓存
          ↓                                              ↓
    tier1直接答 ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

## 重要原则
1. 不乱答：拿不准先思考（检索brain+外部获取）
2. 外部获取→必须存brain：下次直接命中
3. 每次解决难问题 → 团队成员都能学到

