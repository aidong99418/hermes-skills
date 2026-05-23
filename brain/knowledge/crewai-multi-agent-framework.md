# crewAI Multi-Agent Framework

## 概述
crewAI是52k stars的多Agent协作框架，核心思想：**Agent扮演角色、Task定义目标、Crew编排流程、Process决定执行模式**。

## 核心概念

### 1. Agent（智能体）
```
from crewai import Agent

agent = Agent(
    role="房产研究员",
    goal="深度分析{location}的房地产市场趋势",
    backstory="你是一位有10年经验的房地产分析师，擅长数据挖掘与市场预测",
    tools=[search_tool, scrape_tool],  # 绑定工具
    verbose=True,                        # 输出思考过程
    allow_delegation=True               # 允许委派任务给其他Agent
)
```
- **role**: 角色名，决定Agent的专业方向
- **goal**: 具体目标，必须可量化
- **backstory**: 背景故事，塑造Agent思维方式
- **tools**: 可用工具列表（自定义或内置）
- **verbose**: 开启后输出Agent推理链路

### 2. Task（任务）
```
from crewai import Task

task = Task(
    description="收集{location}近5年房价数据并生成分析报告",
    agent=researcher,          # 指定执行者
    expected_output="包含数据表格和趋势图的Markdown报告",
    tools=[search_tool]
)
```
- **description**: 任务描述，越具体越好
- **agent**: 可指定也可不指定（自动分配或Crew内协商）
- **expected_output**: 定义输出格式，决定最终质量

### 3. Crew（团队）
```
from crewai import Crew

crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[task1, task2, task3],
    process="hierarchical",  # 或 "sequential"
    verbose=2
)
```
- **sequential**: 顺序执行，A→B→C
- **hierarchical**: 层级管理，有Manager Agent统一调度
- Crew自动管理Agent间的通信和数据流转

### 4. Process（流程）
```python
# 顺序流程（默认）
crew = Crew(agents=[a1, a2], tasks=[t1, t2], process="sequential")

# 层级流程（更复杂，更强大）
crew = Crew(
    agents=[manager, worker1, worker2],
    tasks=[complex_task],
    process="hierarchical"
)
crew.kickoff()
```

## Hermes集成思路

crewAI与Hermes的定位互补：
- **crewAI**: 解决"多Agent如何协作"（框架层）
- **Hermes**: 解决"谁来调度哪个Agent执行什么"（编排层）

可探索方向：
1. 用crewAI概念重新设计Hermes的多Agent调用
2. crewAI的Process/hierarchical模式用于复杂任务拆解
3. crewAI的tools机制可复用于Hermes的MCP集成

## 代码示例：完整Crew
```python
from crewai import Agent, Crew, Task

# 定义Agent
researcher = Agent(
    role="市场研究员",
    goal="找到{topic}的最新行业动态",
    backstory="你擅长网络搜索和信息整理"
)
writer = Agent(
    role="技术作家",
    goal="将研究内容写成清晰的技术文章",
    backstory="你有多年技术写作经验"
)

# 定义Task
research_task = Task(
    description="搜索{topic}最新动态",
    agent=researcher,
    expected_output="5条关键发现"
)
write_task = Task(
    description="基于研究结果写作",
    agent=writer,
    expected_output="800字技术文章"
)

# 组装Crew并执行
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process="sequential"
)
result = crew.kickoff()
print(result)
```

## 关键洞察
1. **Task的expected_output是质量关键**——定义不清则输出随机
2. **hierarchical流程需要Manager**——但Crew会自动处理
3. **verbose=2可见完整思考**——调试时必开
4. **backstory决定了Agent的"人设"**——和Prompt engineering同等重要
5. **crewAI处理的是"怎么协作"，Hermes处理的是"何时协作"**——两者可以叠加

## 相关文档
- 源码: crewAIInc/crewAI (52k stars)
- 示例: crewAIInc/crewAI-examples (6k stars)
- 工具库: crewAIInc/crewAI-tools (1.4k stars)
