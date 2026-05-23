---
name: brain-thinker
description: 机器猫大脑思考引擎 — 三层思考自动路由。输入问题→判断层级→执行推理→输出结构化结论。tier1直接答/tier2检索brain+外部获取/tier3三模型团队并行分析。
triggers:
  - "分析一下"
  - "为什么"
  - "帮我想想"
  - "哪个好"
  - "怎么选"
  - "原因是什么"
  - "区别是"
  - tier1快速响应
category: brain
tags: [思考引擎, 三层思考, brain, RAG, 推理]
version: 1.0
author: 打工仔
date: 2026-05-23
---

# 🧠 brain_thinker — 机器猫思考引擎

## 核心能力

将问题自动路由到三个思考层级之一：

| 层级 | 触发条件 | 响应方式 | 耗时 |
|------|----------|----------|------|
| ⚡tier1 | 查看/查/剩多少/看看/ls/ps/df | 直接执行，不检索brain | <1秒 |
| 🧠tier2 | 为什么/怎么/分析/区别/不确定 | 检索brain→外部获取→结论 | <5秒 |
| 🔴tier3 | 架构/方案选型/安全/全局分析 | 3模型并行→汇总→结论 | <15秒 |

## 调用方式

### Python调用（推荐）
```python
import sys
sys.path.insert(0, '/opt/data/scripts')
from brain_thinker import brain_think

result = brain_think("Python KeyError怎么处理")
# 返回: {tier, brain_hits, external_used, external_answer, team_results, conclusion, should_save, save_target}
```

### CLI调用
```bash
python3 /opt/data/scripts/brain_thinker.py "你的问题"
python3 /opt/data/scripts/brain_thinker.py --tier 3 "架构选型问题"
python3 /opt/data/scripts/brain_thinker.py --question "问题" --no-external
```

### 轻量包装（agent用）
```python
from brain_invoke import brain_think
result = brain_think("你的问题")  # 一行调用
```

## 返回结构
```python
{
  "tier": 2,
  "tier_name": "🧠思考通道",
  "brain_hits": [{"score": 6, "text": "...", "source": "...", "type": "..."}],
  "external_used": True,
  "external_answer": "...",
  "team_results": [],
  "conclusion": "...",
  "should_save": True,
  "save_target": "brain/scenarios/external_learn_20260523.md",
  "thinking_steps": ["步骤日志..."]
}
```

## 思考层级判断逻辑

### tier1 快速通道（直接答）
- 问题以"查/看/问/告我/帮我找"开头
- 包含"查看/查/剩多少/看看/有没有/在不在/多少/哪个/谁在"
- 长度<20字+不含复杂词
- 执行命令类（ls/cat/ps/df/status）

### tier2 思考通道（检索+获取）
- 包含"为什么/怎么/分析/区别/原理/原因/优化"
- 包含"不确定/不太确定/可能/估计/推荐"
- 长度>30字或含多个空格

### tier3 团队协作（3模型并行）
- 包含"设计/架构/方案/怎么选/哪个好/权衡/取舍"
- 包含"安全/攻击/漏洞/权限/可行性"
- 包含"全局/整体/整体规划"

## tier3团队派发规则

三个模型并行分析同一问题：

| 角色 | 模型 | 职责 | num_predict |
|------|------|------|-------------|
| 推理专家 | deepseek-r1:7b | 深入推理，找深层原因 | 150 |
| 工具专家 | qwen2.5:7b | 从实际执行角度分析 | 150 |
| 打工仔 | qwen2.5:3b | 从事实数据角度分析 | 100 |

结果合并，只保留有实质内容的回复。

## 外部获取链路（tier2）

```
brain检索（BM25）→ 分数<5 → 触发external_fetcher
    ↓
3路并行：HN热帖 + ArXiv论文 + StackOverflow问答
    ↓
Ollama分析（qwen2.5:3b，150字结论，超时60秒）
    ↓
写进 brain/scenarios/external_learn_YYYYMMDD.md
    ↓
后台自动rebuild BM25缓存（408→409个知识块）
```

## 依赖文件
- `/opt/data/scripts/brain_thinker.py` — 主引擎
- `/opt/data/scripts/brain_invoke.py` — 轻量包装（外部调用）
- `/opt/data/scripts/external_fetcher.py` — 外部知识获取
- `/opt/data/scripts/brain_retriever.py` — BM25检索
- `/tmp/brain_bm25_cache.json` — 知识块缓存

## 坑与经验
1. `import auto_learning` 太慢导致超时 → external_fetcher直接用requests调Ollama
2. ArXiv atom XML entry标签带xmlns → 用正则匹配或SOAP解析
3. tier3派发结果为0时不输出空结论 → 只合并非空结果
4. 写brain后必须rebuild缓存 → external_fetcher自带后台rebuild

## ⚠️ 规则顺序陷阱（已踩坑，勿调换顺序）

**tier判断规则执行顺序必须严格遵守，乱序会导致误判：**

```
tier3优先判断 → action开头+result_word → 诊断类短句 → tier1短句 → tier2关键词 → 长度/问号/上下文
                                                                                              ↑
                                                           诊断类短句如果放在tier1短句规则之后，
                                                           会被"问"字匹配误杀为tier1！
```

**当前 `detect_tier()` 中 `diagnostic_patterns` 必须在 tier1短句规则之前：**

```python
# ✅ 正确顺序
if any(pat in q for pat in diagnostic_patterns):
    return 2  # 先拦住诊断类

if len(q) <= 12 and any(kw in q for kw in ["查", "看", "问", "找"]):
    return 1  # 再匹配tier1短句

# ❌ 错误：诊断类会被"问"字误杀
```

**受影响的短语模式**（会误判为tier1）：
- "哪里出了问题" → 包含"问"字 → ❌ 被tier1短句规则误杀为tier1
- "和之前有什么不同" → 包含"问"字 → ❌ 同上
- "有什么问题" → 包含"问"字 → ❌ 同上

**如果修改 `brain_invoke.py` 的 `detect_tier()` 函数，务必确保：**
1. `diagnostic_patterns` 检查在 tier1短句规则之前
2. 修改后用测试题验证：`detect_tier("哪里出了问题")` 必须返回2

## 自进化监控（2026-05-24 已部署）

自进化五层架构已落地运行：

| 组件 | 文件 | cron | 状态 |
|------|------|------|------|
| dialog_watchdog | `/opt/data/scripts/dialog_watchdog.py` | 每分钟 | ✅ |
| self_observer | `/opt/data/brain/performance/self_observer.py` | 23:00每日报告 | ✅ |
| brain_backup | `/opt/data/skills/tools/brain_backup_trigger.py` | 每小时 | ✅ |
| feedback_tracking | `brain_invoke.py` 内置 `record_feedback()` | 被动记录 | ✅ |

**指标文件：**
- `/opt/data/brain/performance/behavior_log.jsonl` — 行为日志
- `/opt/data/brain/performance/brain_retriever_metrics.json` — 检索指标
- `/opt/data/brain/performance/confidence_tracking.json` — 置信度追踪
- `/opt/data/brain/performance/feedback_tracking.json` — 用户反馈

**自进化目标：** tier准确率>90% / brain命中率>80% / 好奇机制触发
