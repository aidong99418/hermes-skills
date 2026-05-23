---
name: brain-invoke
description: brain_thinker轻量包装。agent/子脚本一行调用思考引擎：brain_think("问题")→自动判断tier→检索brain→外部获取→团队派发→返回结构化结论。比直接调brain_thinker.py更简单。
triggers:
  - "一行调用思考引擎"
  - "外部脚本调用brain"
  - "subagent调brain"
category: brain
tags: [brain, 思考引擎, 轻量包装, 一行调用]
version: 1.0
author: 打工仔
date: 2026-05-23
---

# ⚡ brain_invoke — 一行调用思考引擎

## 为什么需要这个

`brain_thinker.py` 是完整的CLI工具，但agent/子脚本调用时不需要CLI参数解析，只需要一行函数调用。

## 用法（只要这一行）

```python
from brain_invoke import brain_think

result = brain_think("Python KeyError怎么处理")
```

## 与brain_thinker.py的区别

| 对比项 | brain_thinker.py | brain_invoke.py |
|--------|------------------|-----------------|
| 调用方式 | CLI或import完整模块 | 一行import | 
| 依赖 | 大部分brain_thinker代码 | 只引用需要的函数 |
| 用途 | 独立测试/CLI | agent/子脚本内部调用 |
| 参数 | --tier/--question/--no-external | tier=2/tier=None |

## 参数

```python
brain_think(question: str, tier: int = None, timeout: int = 90)
```

- `question`：问题文本
- `tier`：强制指定层级（可选，默认自动判断）
- `timeout`：外部获取超时，默认90秒

## 返回结构

```python
{
    "question": "...",
    "tier": 2,                                  # 1=快速/2=思考/3=团队
    "tier_name": "🧠思考通道",
    "brain_hits": [
        {"score": 6, "text": "...", "source": "...", "type": "..."}
    ],
    "external_used": True,                      # 是否触发了外部获取
    "external_answer": "...",                   # 外部知识结论
    "team_results": [],                         # tier3团队分析
    "conclusion": "...",                        # 最终结论（取external_answer或brain摘要）
    "should_save": True,                        # 是否建议沉淀
    "save_target": "brain/scenarios/external_...",  # 建议沉淀路径
    "thinking_steps": ["..."]                   # 思考步骤日志
}
```

## 使用场景

```python
# 1. 子agent调用
from brain_invoke import brain_think
r = brain_think("Docker网络故障排查步骤")
print(r["conclusion"])

# 2. 判断是否需要沉淀
if r["should_save"]:
    save_to_brain(r["save_target"], r["external_answer"])

# 3. 强制tier3团队派发
r = brain_think("NAS架构选型", tier=3)
for视角 in r["team_results"]:
    print(f"{视角['name']}: {视角['result']}")
```

## 内部实现

- `detect_tier()`：关键词权重判断（与brain_thinker.py同步）
- `search_brain()`：直接读`/tmp/brain_bm25_cache.json`，BM25评分
- `fetch_external()`：调用external_fetcher.fetch_and_learn()
- `team_delegate()`：3个Ollama模型并行，各150 token

## 依赖
- `/tmp/brain_bm25_cache.json`（BM25缓存，408个知识块）
- `external_fetcher.py`
- Ollama服务（localhost:11434）
