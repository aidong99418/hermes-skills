---
name: langgraph
description: LangGraph状态机Agent框架 — 32k⭐，图结构+状态持久化+循环+检查点，构建有状态、长期运行的LLM Agent。触发：状态机Agent、LangGraph、Agent持久化、图结构工作流。
version: 1.0.0
tags: [agent, state-machine, langchain, graph, checkpoint, persistence]
triggers: ["LangGraph", "langgraph", "状态机Agent", "图结构工作流", "Agent持久化", "checkpointer"]
---

# LangGraph 架构设计参考

## 核心定位
LangGraph = LangChain团队的低级编排框架（32k⭐），用**图结构**描述Agent工作流，支持**状态持久化**、**循环**、**检查点**。比LangChain更底层，适合构建复杂、有状态的长期运行Agent。

## 核心概念

```
StateGraph（状态图）
    ├── nodes（节点）：具体执行步骤
    ├── edges（边）：节点间的流向
    ├── state（状态）：跨节点的共享数据
    └── checkpoint（检查点）：状态的快照/恢复

亮点：支持条件分支、循环、并行，满足复杂Agent需求
```

## 状态机四件套

### 1. State（状态）
```python
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: list[str]           # 对话历史（追加合并）
    memory: Annotated[list, add]  # 记忆累积
    step: int                     # 当前步数
    context: dict                 # 工具返回的上下文
```

### 2. Nodes（节点）
```python
def reason_node(state: AgentState) -> AgentState:
    """推理节点"""
    msg = llm.reason(state["messages"])
    return {"messages": [msg], "step": state["step"] + 1}

def tool_node(state: AgentState) -> AgentState:
    """工具执行节点"""
    result = execute_tool(state["messages"][-1])
    return {"messages": [f"[tool]: {result}"]}
```

### 3. Edges（边）
```python
# 条件边：根据状态决定下一步
def should_continue(state: AgentState) -> str:
    if state["step"] >= 10:
        return "end"
    return "continue"

graph.add_conditional_edges(
    "reason",                      # 从reason节点出发
    should_continue,               # 条件函数
    {"continue": "tool", "end": END}
)

# 普通边：固定流向
graph.add_edge("tool", "reason")   # tool执行完回到reason
```

### 4. Checkpoint（检查点/持久化）
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()  # 内存存储
# 生产环境用：PostgresSaver / SqliteSaver

graph = StateGraph(AgentState).compile(
    checkpointer=checkpointer,
    interrupt_before=["tool"],  # 在tool前中断，支持人工干预
)
```

## 完整Agent示例

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 1. 定义状态
class AgentState(TypedDict):
    query: str
    plan: list[str]
    current_step: int
    result: str

# 2. 定义节点
def planner(state):
    plan = llm.plan(state["query"])
    return {"plan": plan, "current_step": 0}

def executor(state):
    step = state["plan"][state["current_step"]]
    result = run_step(step)
    return {"current_step": state["current_step"] + 1, "result": result}

def should_continue(state):
    if state["current_step"] >= len(state["plan"]):
        return END
    return "executor"

# 3. 构建图
graph = StateGraph(AgentState)
graph.add_node("planner", planner)
graph.add_node("executor", executor)
graph.set_entry_point("planner")
graph.add_conditional_edges("executor", should_continue)
graph.add_edge("planner", "executor")

# 4. 编译 + 检查点持久化
app = graph.compile(checkpointer=MemorySaver())

# 5. 运行（支持中断和恢复）
config = {"configurable": {"thread_id": "user-123"}}
for event in app.stream({"query": "分析销售数据"}, config):
    print(event)
```

## Checkpointer持久化机制

这是LangGraph最强大的特性——**中断后恢复**：

```python
# 中断执行（在tool调用前暂停）
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["tool_node"]  # 支持人工审核
)

# 恢复执行（用相同thread_id）
for event in app.stream(None, config):
    # 继续从中断点执行
    pass

# 生产检查点存储
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
checkpointer.setup()  # 创建表
```

## 与本项目的契合点

| LangGraph特性 | 借鉴场景 |
|-------------|---------|
| 状态机+循环 | 复杂任务的多步骤执行控制 |
| Checkpointer | 任务中断/恢复机制（断点续跑） |
| interrupt_before | 人工审核节点（高风险操作前暂停） |
| Annotated operator | 记忆累积策略（add/等） |
| 多线程checkpoint | 并发任务隔离（thread_id） |
| 图可视化 | 复杂工作流的调试和展示 |

## 快速安装

```bash
pip install -U langgraph
```

## 坑/注意事项

1. **状态必须可序列化**：状态里不能有不可JSON序列化的对象
2. **死循环防护**：一定要有终止条件（END），否则可能无限循环
3. **checkpoint版本**：升级LangGraph后检查点格式可能不兼容
4. **interrupt_before**：只在指定节点前中断，不是全局中断
5. **节点顺序**：add_edge的顺序很重要，注意拓扑排序
