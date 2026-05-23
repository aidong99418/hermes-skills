---
name: mem0-design
description: Mem0长期记忆层设计 — 三层记忆架构(user/agent/run)+多信号检索(语义+BM25+实体)+ADD-only积累+实体链接，业界最佳实践参考。触发：记忆系统设计、长期上下文、AI个性化记忆。
version: 1.0.0
tags: [memory, RAG, vector-search, AI]
triggers: ["长期记忆", "记忆层设计", "Mem0", "个性化AI", "记忆检索"]
---

# Mem0 架构设计参考

## 核心定位
Mem0 = AI应用的**记忆层**（Memory Layer），专解决大模型"无持久记忆"问题。56k⭐，2026年刷新benchmark（LoCoMo 91.6 / LongMemEval 94.8）。

## 三层记忆架构

```
user_id ──────► agent_id ──────► run_id
  │                 │                │
  │ 长期偏好/身份    │ 智能体工作记忆   │ 任务会话记忆
  └────────────────┴────────────────┘
              Qdrant 向量存储
```

**关键设计**：不按任务切分记忆，按 `user_id` 聚合所有历史，通过 metadata 隔离 agent/session 维度。

## 多信号检索（融合打分）

三个检索通道**并行计算**，最后 score_and_rank 融合：

| 通道 | 技术 | 作用 |
|------|------|------|
| semantic | 向量相似度 | 语义相关 |
| BM25 | 词频统计（lemmatized） | 关键词命中 |
| entity | 实体匹配 | 专有名词精准 |

融合公式（参考 `utils/scoring.py`）：
```
final_score = α*semantic + β*bm25 + γ*entity_boost
时间衰减因子：recent_memories 权重更高
```

## ADD-Only 积累策略

```python
# 核心原则：只ADD，不UPDATE/DELETE
memory = await mem0.add(
    messages=[{"role": "user", "content": "我明天要去北京出差"}],
    user_id="user_123"
)
```

**优点**：
- 单次LLM调用提取记忆（7.0K tokens, 0.88s p50）
- 一致性保证，无更新冲突
- 历史完整，可追溯

## 实体链接（Entity Linking）

独立 entity store collection（`{collection}_entities`），每个实体关联多个memory：

```
实体 "北京" ──► memory_1（出差任务）
            └──► memory_2（旅游偏好）

实体 boost：相关memory在检索时加权提升
匹配阈值：相似度 ≥ 0.95
```

## 记忆提取Prompt（单Pass）

见 `configs/prompts.py`，核心逻辑：
```
给定对话历史 → 提取：
1. 事实性信息（实体、事件）
2. 用户偏好（风格、习惯）
3. 关系（人与人/人与事）
```

## 与Hermes记忆的对比

| 维度 | Mem0 | Hermes当前方案 |
|------|------|---------------|
| 存储 | Qdrant向量库 | RAG知识库 |
| 检索 | 三路融合 | BM25单路 |
| 层级 | user/agent/run三级 | 会话级 |
| 实体链接 | 有 | 无 |
| 本地化 | 支持Ollama | 支持 |

## 参考实现要点

```python
# 多信号并行检索（伪代码）
async def retrieve(query, user_id):
    # 三个通道并行
    semantic_results = await vector_search(query, top_k=20)
    bm25_results = await bm25_search(query, top_k=20)
    entity_results = await entity_match(query)
    
    # 融合打分
    fused = score_and_rank([semantic, bm25, entity], weights=[0.4, 0.3, 0.3])
    return fused[:top_k]

# 实体链接
def link_entities(memory_text):
    entities = extract_entities(memory_text)  # LLM或NER
    for entity in entities:
        existing = entity_store.search(entity, threshold=0.95)
        if existing:
            existing.memory_ids.append(memory.id)
        else:
            entity_store.add(entity, memory_ids=[memory.id])
```

## 本地部署参考

```python
from mem0 import Memory

mem = Memory.from_llm(
    llm="ollama/llama3.2",
    embedder="ollama/nomic-embed-text",
    vector_store="qdrant",
    vector_store_config={"location": ":memory:"},
)

# 增
mem.add("用户喜欢简约设计", user_id="user_1")

# 查
results = mem.search("用户的设计偏好", user_id="user_1")

# 历史
history = mem.get_all(user_id="user_1")
```

## 适用场景

- ✅ 需要跨会话记住用户偏好
- ✅ Agent多轮对话需要上下文积累
- ✅ 复杂实体关系网络（如客服知识图谱）
- ⚠️ 简单单会话任务 → 没必要用，增加复杂度

## 踩坑提示

1. **Qdrant vs Chroma**：生产用Qdrant（性能高），开发用Chroma（零配置）
2. **实体链接阈值**：0.95太高可能漏匹配，0.85太低噪音多，建议A/B测试
3. **记忆积累上限**：ADD-only会无限增长，需定期压缩（类似知识库老化）
4. **Ollama兼容**：需 `keep_alive` 设置够长，否则每次都要重新加载模型
