---
name: external-fetcher
description: 外部知识获取模块。brain无相关记录时，从ArXiv/Hacker News/StackOverflow三路并行抓取+Ollama分析→自动写进brain→rebuild缓存。全自动闭环。
triggers:
  - "外部获取"
  - "最新论文"
  - "HN热门"
  - "stackoverflow"
  - "网上查"
category: brain
tags: [外部获取, ArXiv, HackerNews, StackOverflow, RAG]
version: 1.0
author: 打工仔
date: 2026-05-23
---

# 🌐 external_fetcher — 外部知识获取

## 核心能力

当brain检索不到相关知识时，自动从外部获取并沉淀：

```
用户问题 → brain检索 → 分数<5 → external_fetcher
    ↓
3路并行抓取（ArXiv + HN + SO）
    ↓
Ollama分析（qwen2.5:3b，150字结论，60秒超时）
    ↓
写进 brain/scenarios/external_learn_YYYYMMDD.md
    ↓
后台自动rebuild BM25缓存
```

## 数据源

| 来源 | 接口 | 内容 | 数量 |
|------|------|------|------|
| ArXiv | REST API (export.arxiv.org/api/query) | 学术论文标题+摘要 | 默认3篇 |
| Hacker News | Algolia API (hn.algolia.com/api/v1) | 热帖标题+URL+摘要 | 默认3条 |
| StackOverflow | Stack Exchange API (api.stackexchange.com) | Q&A问答 | 默认2条 |

## 用法

### Python调用
```python
import sys
sys.path.insert(0, '/opt/data/scripts')
from external_fetcher import fetch_and_learn

result = fetch_and_learn("Python异常处理最佳实践")
# result: {"question": ..., "sources": [...], "answer": "...", "saved": True/False}
```

### CLI调用
```bash
python3 /opt/data/scripts/external_fetcher.py "你的问题"
python3 /opt/data/scripts/external_fetcher.py "问题" --max-results 5
```

## 返回结构
```python
{
    "question": "Python KeyError和TypeError区别",
    "sources": {
        "arxiv": [{"title": "...", "abstract": "...", "url": "...", "source": "arXiv"}],
        "hn": [{"title": "...", "url": "...", "points": N, "source": "HN"}],
        "so": [{"title": "...", "answer_count": N, "source": "SO"}]
    },
    "total_results": 8,
    "answer": "..."  # Ollama分析结论（150字）
    "saved_path": "brain/scenarios/external_learn_20260523.md",
    "saved": True,
    "cache_rebuilt": True
}
```

## 写入brain的路径
- **主路径**：`/opt/data/brain/scenarios/external_learn_YYYYMMDD.md`
- **备选**：`/opt/data/brain/reasoning_patterns/`（如果目录存在）

## 坑与经验
1. **ArXiv Atom XML解析失败**：`<entry>`标签带xmlns属性导致正则不匹配 → 用`(.*?)`贪婪匹配替代
2. **HN API限流**：hn.algolia.com/api/v1/search免费，无需key
3. **StackOverflow API**：需要user-agent头，否则403
4. **Ollama超时**：60秒超时，失败时返回空answer
5. **import太慢**：`import auto_learning`导致整体超时 → 改用直接requests调Ollama API
6. **写brain后必须rebuild**：缓存不会自动更新，手动调用brain_retriever rebuild

## OOM注意事项
- ArXiv并发抓取，HN和SO同时发起
- Ollama分析独立，不阻塞抓取
- 写文件用`append`模式，避免覆盖
