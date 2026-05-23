---
name: crewai-multi-agent
description: CrewAI 多Agent编排框架 — Agent/Crew/Task/Process 四元组架构，独立于 LangChain，52k⭐ 工业级框架
version: 1.0.0
tags: [multi-agent, orchestration, AI, python]
triggers: ["多Agent协作", "CrewAI", "agent crew", "multi-agent", "自主Agent编排"]
---

# CrewAI 多Agent框架核心技能

## 核心架构（四元组）

```
Crew ( crew )
  └── Agents ( agents[] )
        ├── role: 角色定位 ("数据分析师")
        ├── goal: 具体目标 ("提取关键指标")
        ├── backstory: 背景故事 (让LLM理解角色)
        └── tools: 工具列表 (可选)
  └── Tasks ( tasks[] )
        ├── description: 任务描述
        ├── expected_output: 期望输出格式
        ├── agent: 谁来做
        └── dependencies: 依赖哪些任务 (可选)
  └── Process ( process )
        └── sequential | parallel | hierarchical
  └── verbose: 详细日志级别
```

## 关键决策点

| 场景 | 推荐配置 |
|------|---------|
| 线性依赖任务 | `process=Process.sequential`，每个任务依赖前一个 |
| 独立并行任务 | `process=Process.parallel`，所有Agent同时开工 |
| 领导-执行模式 | `process=Process.hierarchical`，自动产生Manager Agent |
| 需要Agent间通信 | Crew + Process.sequential，通过 Task output 传递 |
| 单一Agent多工具 | 直接用 `Agent` + `tools=[]`，不用 Crew |

## 适用条件

✅ **适合：**
- 需要多个专业化 Agent 协作完成复杂任务
- 任务有明确的流程/依赖关系
- 需要记忆 Memory 在 Agent 间共享
- 企业级工作流自动化

❌ **不适合：**
- 单 Agent 简单任务（用 Tool/Function Calling 更轻量）
- 需要实时流式响应（Event-driven 用 Flows 替代）
- 极度资源受限环境

## 快速模板

```python
from crewai import Agent, Task, Crew, Process

# 1. 创建 Agent
researcher = Agent(
    role="行业研究员",
    goal="收集并分析{topic}的最新动态",
    backstory="你是一名专业的行业分析师...",
    verbose=True
)

writer = Agent(
    role="内容编辑",
    goal="将研究报告转化为通俗易懂的文章",
    backstory="你是一名资深内容编辑...",
    verbose=True
)

# 2. 创建 Task
task1 = Task(
    description="搜索{topic}相关的最新新闻和报告",
    expected_output="一份包含5个关键发现的列表",
    agent=researcher
)

task2 = Task(
    description="将研究结果写成一篇800字文章",
    expected_output="markdown格式文章",
    agent=writer,
    context=[task1]  # 依赖task1输出
)

# 3. 创建 Crew 并执行
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential
)

result = crew.kickoff()
print(result)
```

## Memory 机制

```python
crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,           # 启用记忆
    embedder={             # 向量嵌入配置
        "provider": "openai",
        "model": "embeddings"
    }
)
```

Memory 三层：
- **Short-term**: 当前对话上下文
- **Long-term**: 持久化记忆，跨会话
- **Entity**: 实体记忆（人物/公司/概念）

## 与其他框架对比

| 特性 | CrewAI | LangGraph | AutoGen |
|------|--------|-----------|---------|
| 多Agent编排 | ✅ 原生 | ⚠️ 需手动 | ✅ 原生 |
| 独立于LangChain | ✅ 完全独立 | ❌ 依赖 | ⚠️ 部分依赖 |
| Flow/事件驱动 | ✅ Flows组件 | ✅ | ❌ |
| 记忆系统 | ✅ 内置 | ⚠️ 需自行实现 | ⚠️ 需自行实现 |
| 企业级监控 | ✅ AMP Suite | ⚠️ 自行集成 | ❌ |

## Flows（事件驱动模式）

适合需要精确控制执行顺序或单次 LLM 调用编排多个 Agent 的场景：

```python
from crewai.flow import Flow, Router, or_

class MyFlow(Flow):
    @router()
    def start(self):
        if condition:
            return "path_a"
        return "path_b"

    def path_a(self):
        # 执行路径A
        pass
```

## 坑

1. **Task dependencies 要在创建 Crew 前定义好**，运行时改不了
2. **verbose=True 会输出大量日志**，生产环境改 False
3. **Agent backstory 太长会吃 token**，保持 50-150 字
4. **hierarchical 模式会自动产生 Manager**，可能超出预算
5. **Memory 需要嵌入模型**，没配 embedder 不会报错但记忆无效
