---
name: multi-agent-crew
description: 本地多Agent协作调度框架 — 基于Ollama并行调用，零依赖，支持模型分级、任务依赖链、结果聚合、错误降级
version: 1.0.0
tags: [multi-agent, Ollama, parallel, orchestration]
triggers: ["多Agent", "并行调用", "Agent协作", "crew调度", "multi-agent"]
---

# Multi-Agent Crew 调度框架

一句话定位：用 Ollama 本地模型实现 crewAI 式的多Agent并行/串行调度，零外部依赖，38GB内存下可同时跑 3-4 个 Agent。

## 核心架构

```
Crew (调度器)
  ├── Agents[]           — 注册Agent，绑定角色+系统提示+模型
  ├── Tasks[]            — 任务列表，带描述和Agent归属
  ├── Process            — parallel | sequential
  ├── Strategy           — 模型选择策略
  └── hooks              — on_start / on_result / on_complete
```

## 快速上手（最小模板）

```python
from multi_agent_crew import Crew, Agent, Task, Process

crew = Crew(
    agents=[
        Agent(id="researcher", role="研究员",
              system="你是专业行业研究员...",
              model="qwen2.5:3b"),
        Agent(id="writer", role="编辑",
              system="你是资深内容编辑...",
              model="qwen2.5:7b"),
    ],
    process=Process.parallel
)

results = crew.kickoff([
    Task(task_id="t1", description="分析{topic}的市场趋势", agent_id="researcher"),
    Task(task_id="t2", description="搜集行业竞品信息", agent_id="researcher"),
    Task(task_id="t3", description="将研究报告写成通俗文章", agent_id="writer",
         depends_on=["t1", "t2"]),  # 等待t1,t2完成
])
print(results["t3"])  # 最终汇总结果
```

## 完整示例：数据分析报告

```python
from multi_agent_crew import Crew, Agent, Task, Process, ModelStrategy

# 1. 策略：任务类型 → 模型自动映射
strategy = ModelStrategy({
    "quick": "smollm2:1.7b",      # 清洗/格式化（<1秒）
    "normal": "qwen2.5:3b",       # 常规分析（<3秒）
    "heavy": "qwen2.5:7b",        # 深度推理（<10秒）
    "critical": "deepseek-r1:7b", # 高价值决策（<15秒）
})

# 2. 注册Agent（角色+能力边界）
agents = [
    Agent(id="fetcher", role="数据采集员",
          system="你负责从原始文本中提取结构化数据。只输出JSON数组，不解释。",
          strategy=strategy, tier="quick"),
    Agent(id="analyzer", role="数据分析师",
          system="你分析数据，给出3个关键洞察和支撑数据。格式：## 洞察N\n数据\n结论",
          strategy=strategy, tier="normal"),
    Agent(id="writer", role="报告撰写员",
          system="你把分析结果写成业务报告，800字以内，分3节，有建议。",
          strategy=strategy, tier="heavy"),
    Agent(id="reviewer", role="质量审核",
          system="你审查报告，指出2个逻辑漏洞或数据问题，否则输出'无问题'。",
          strategy=strategy, tier="normal"),
]

# 3. 定义任务（含依赖链）
tasks = [
    Task(id="fetch", description="从以下文本提取所有数值数据：{text}", agent_id="fetcher"),
    Task(id="analyze", description="分析提取的数据，找出趋势和异常", agent_id="analyzer",
         depends_on=["fetch"]),
    Task(id="write", description="写报告，主题：{topic}", agent_id="writer",
         depends_on=["analyze"]),
    Task(id="review", description="审核报告质量", agent_id="reviewer",
         depends_on=["write"]),
]

# 4. 执行
crew = Crew(agents=agents, tasks=tasks, process=Process.sequential)
results = crew.kickoff({"text": "2024年Q1营收1200万，Q2营收1450万...", "topic": "季度业绩分析"})

for task_id, result in results.items():
    print(f"\n=== {task_id} ===\n{result}")
```

## 并行 vs 串行选择

| 场景 | Process | 原因 |
|------|---------|------|
| 独立任务（多个研究员并行搜） | `parallel` | 无依赖，速度×N |
| 依赖链（先搜→再分析→再写） | `sequential` | 结果依赖上游输出 |
| 混合（并行搜 + 串行写） | `hybrid` | 大任务拆分并行子任务 |

## 核心 API

### Agent
```python
Agent(
    id="unique_id",           # 唯一标识
    role="角色名",            # 出现在system prompt
    system="系统提示词",       # LLM角色定义
    model="模型名",           # 可选，默认用strategy
    strategy=ModelStrategy,   # 或用策略自动选模型
    tier="normal",            # 策略映射键
    max_retries=2,            # 失败重试次数
    timeout=30,               # 秒
)
```

### Task
```python
Task(
    id="task_id",
    description="任务描述，支持{template}插值",
    agent_id="对应的Agent.id",
    depends_on=["prev_task_id"],  # 依赖任务ID列表
    context_template={"key": "value"},  # 插值变量
    on_fail="skip|retry|abort",  # 失败策略
)
```

### Crew
```python
Crew(
    agents=[...],
    tasks=[...],
    process=Process.parallel,  # parallel | sequential | hybrid
    hooks={                   # 回调钩子
        "on_task_start": lambda t: print(f"开始: {t.id}"),
        "on_task_result": lambda t, r: print(f"完成: {t.id}"),
        "on_complete": lambda r: print(f"全部完成"),
    },
    verbose=True,
)
```

## 内存管理（重要）

38GB 机器的建议配置：

```python
# 内存限制配置
crew = Crew(
    agents=agents,
    memory_limit_gb=20,       # 总消耗不超过20GB
    max_concurrent=3,         # 最多同时加载3个模型
    model_unload_after=True,  # 任务完成后卸载模型
)

# 内存监控（运行时）
crew.memory_snapshot()  # 打印当前内存使用
```

**模型内存参考：**
| 模型 | 内存占用 |
|------|---------|
| smollm2:1.7b | ~1.2GB |
| qwen2.5:3b | ~3.5GB |
| qwen2.5:7b | ~7.5GB |
| deepseek-r1:7b | ~7.5GB |

**最大并发参考：**
- 4GB机器：同时1个
- 16GB机器：同时2个（qwen2.5:7b + smollm2）
- 32GB机器：同时3个（qwen2.5:7b + qwen2.5:3b + smollm2）
- 38GB机器（你）：同时3-4个

## 结果聚合

```python
# 方式1：字典（默认）
results = crew.kickoff(inputs)
# {"task1": "结果...", "task2": "结果...", ...}

# 方式2：按角色聚合
by_role = crew.kickoff_aggregate(inputs, group_by="agent_id")
# {"researcher": ["任务1结果", "任务2结果"], "writer": ["任务3结果"]}

# 方式3：最终结果（只返回最后一个任务）
final = crew.kickoff_final(inputs)
# "报告已完成"
```

## 错误处理

```python
crew = Crew(
    agents=agents,
    error_strategy="graceful",  # graceful | strict
    fallback_model="smollm2:1.7b",  # 模型OOM时降级目标
)

# 任务级失败策略
Task(id="t1", on_fail="skip", ...)     # 失败跳过，继续执行
Task(id="t2", on_fail="retry", ...)    # 重试max_retries次
Task(id="t3", on_fail="abort", ...)    # 中止整个crew
```

## 性能调优

```python
# Ollama连接池（复用连接，减少握手）
crew = Crew(agents=agents,
    ollama_base_url="http://localhost:11434",
    connection_pool_size=10,
    keep_alive="10m",           # 模型常驻10分钟
)

# 批量任务
crew.kickoff_batch([
    {"topic": "AI发展趋势"},   # 任务1输入
    {"topic": "新能源市场"},   # 任务2输入
], max_workers=2)              # 最多2个crew并行
```

## 坑

1. **depends_on 必须在 tasks 列表中先定义**，Circular dependency 会抛异常
2. **parallel 模式下同时发起多个 Ollama 请求**，需要确认 `localhost:11434` 能并发处理（实测可支持5-10并发）
3. **模板插值用 `{key}`**，和 `format()` 一致，不要漏引号
4. **deepseek-r1:7b 首次推理慢**（~8秒），设置 `timeout=20`
5. **`keep_alive` 太长会占内存**，跑完大批量记得调小或清空
