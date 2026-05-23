---
name: brain-invoke
description: brain_thinker轻量包装。agent/子脚本一行调用思考引擎：brain_think("问题")→自动判断tier→检索brain→外部获取→团队派发→返回结构化结论。比直接调brain_thinker.py更简单。
triggers:
  - "一行调用思考引擎"
  - "外部脚本调用brain"
  - "subagent调brain"
category: brain
tags: [brain, 思考引擎, 轻量包装, 一行调用]
version: 1.1
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
    "brain_hit_count": 5,                       # 命中条数
    "brain_max_score": 6,                       # 最高分
    "external_used": True,                      # 是否触发了外部获取
    "external_answer": "...",                   # 外部知识结论
    "team_results": [],                         # tier3团队分析，每个含model/took_ms/answer
    "conclusion": "...",                        # 最终结论
    "self_observation": {"elapsed_ms": 4, "tier": 2, "skipped_brain": False},
    "working_memory_updated": True,
    "recommended_skills": ["..."],
    "confidence": 0.75,
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
for res in r["team_results"]:
    print(f"{res['model']}: {res['answer']}")
```

## 三层思考通道

| tier | 名称 | 耗时 | 行为 |
|------|------|------|------|
| 1 | ⚡快速通道 | **0ms** | 不检索brain，直接执行 |
| 2 | 🧠思考通道 | ~5-15s | 检索brain → 本地Ollama分析 → 按需外部获取 |
| 3 | 🔴团队协作 | ~20-30s | 检索brain → **3个Ollama模型并行推理** → 汇总 |

## 内部实现

- `detect_tier()`：关键词权重判断，动作指令开头→检查结果词列表（诊断/修复/解决等→tier2，否则tier1）
- `search_brain()`：读`/tmp/brain_bm25_cache.json`，**中英文分开tokenize后BM25评分**
- `fetch_external()`：调用external_fetcher（HN/ArXiv/SO 3路并行）
- `team_delegate()`：3个Ollama模型（qwen2.5:3b + smollm2:1.7b + qwen2.5:7b）真实并行，各10s超时

## ⚠️ 已知陷阱

### ⚡ search_brain中文分词Bug（2026-05-23修复）

**错误写法（会中英混合串token）：**
```python
terms = re.findall(r'[\w]{2,}', question.lower())  # "docker报错怎么解决" → 1个超长token
```

**正确写法（已写入brain_invoke.py）：**
```python
en_terms = re.findall(r'[a-z0-9]+', question.lower())
cn_chars = re.findall(r'[\u4e00-\u9fff]', question)
cn_bigrams = [question[i:i+2] for i in range(len(question)-1)
              if '\u4e00' <= question[i] <= '\u9fff' and '\u4e00' <= question[i+1] <= '\u9fff']
terms = en_terms + cn_chars + cn_bigrams
```

**后果**：修复前中英混合Query（如"Docker报错怎么解决"）检索永远返回0命中。修复后正常命中5条。

### ⚡ Ollama在Docker容器内

Ollama监听在当前容器内，`ps aux | grep ollama` 看到 defunct 不代表服务挂了——只要 `curl localhost:11434/api/tags` 返回正常即可。`nohup ollama serve &` 重启。

### ⚡ COMPLEX_KEYWORDS防重复

列表里不要出现重复词（"异常""搞不定"各2次），会导致BM25权重异常。用 `from collections import Counter` 检查。

## 依赖

- `/tmp/brain_bm25_cache.json`（BM25缓存，399个知识块）
- `external_fetcher.py`
- Ollama服务（localhost:11434，在Docker容器内）
- Python标准库：json, time, datetime, re, os, concurrent.futures, requests, hashlib
- **需额外安装**：`pip install ollama feedparser beautifulsoup4 requests --break-system-packages`
- **注意**：web_scraper.py 也依赖 feedparser + beautifulsoup4 + requests，三个一起装
