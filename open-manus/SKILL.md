---
name: open-manus
description: OpenManus多Agent系统 — MetaGPT团队出品，56k⭐，Plan+React+Browser三阶段Agent流式编排，MCP协议，python main.py即可运行。触发：多Agent协作、MetaGPT架构、Plan驱动Agent。
version: 1.0.0
tags: [multi-agent, plan, MCP, playwright, MetaGPT]
triggers: ["OpenManus", "MetaGPT", "Plan驱动Agent", "多Agent流式编排", "playwright自动化"]
---

# OpenManus 架构设计参考

## 核心定位
OpenManus = MetaGPT团队开源的多Agent系统（56k⭐），让LLM自主操控浏览器和文件系统完成任务。核心三阶段：Plan规划 → React执行 → Browser操作。

## 核心架构

```
User Task
    │
    ▼
PlanAgent（规划阶段）
    │ 理解任务 → 拆解子任务 → 生成执行计划
    ▼
ReactAgent（执行阶段） × N
    │ 循环：思考→工具调用→观察→决策
    │ 工具集：MCP协议 + 内置Actions + Playwright
    ▼
BrowserAgent/FileAgent（操作阶段）
    │ CDP/Playwright 浏览器控制
    │ 文件系统读写
    ▼
Result
```

## 三阶段详解

### 1. Plan阶段（规划大脑）
- 接收用户自然语言任务
- 拆解为可执行的Agent序列
- 每个子任务分配给对应的Agent
- 输出：结构化执行计划（JSON/流式）

### 2. React阶段（执行引擎）
- ReAct循环：`Thought → Action → Observation → ... → Output`
- 支持多Agent并行/串行执行
- 内置错误重试 + 回退机制

### 3. Browser阶段（操作层）
- **Playwright**驱动浏览器（比CDP更简单）
- 支持：点击/输入/滚动/截图/提取内容
- 可处理登录态/Cookie持久化

## MCP协议集成

OpenManus将MCP作为工具注册到Agent：

```python
# MCP工具注入示例
from open manus.config import MCPConfig
config = MCPConfig.from_file("mcp_servers.toml")
agent = ReactAgent(mcp_config=config)
```

TOML配置文件：

```toml
[mcp_servers.github]
command = "npx"
args = ["@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "xxx" }
```

## 快速启动

```bash
# 安装
uv venv --python 3.12
source .venv/bin/activate
uv sync

# 运行（python main.py）
python main.py

# 配置文件
cat config.toml        # Agent配置
cat mcp_servers.toml   # MCP服务器
```

## 核心代码示例

### 创建自定义Agent

```python
from open_manus.agent.react import ReactAgent
from open_manus.tools.browser import BrowserTool
from open_manus.tools.mcp import MCPTool

agent = ReactAgent(
    name="DataAnalyst",
    role="数据分析专家",
    tools=[
        BrowserTool(),
        MCPTool(server_name="github"),
    ],
    model="claude-sonnet-4",
)
result = await agent.run("分析过去7天GitHub热榜趋势")
```

### PlanAgent自定义

```python
from open_manus.agent.plan import PlanAgent

planner = PlanAgent(model="gpt-4.1")
plan = await planner.create_plan(
    task="帮我做市场竞品分析",
    constraints=["只用公开数据", "输出markdown报告"],
)
# plan = { "steps": [...], "agents": [...], "estimated_time": "30m" }
```

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 包管理 | uv + pyproject.toml |
| LLM接口 | OpenAI / Anthropic / 本地Ollama |
| 浏览器自动化 | Playwright（主流） |
| 工具协议 | MCP（Model Context Protocol） |
| 配置格式 | TOML |
| 流式输出 | SSE / WebSocket |

## 与本项目的契合点

- **多Agent调度**：可借鉴其Plan+React分层设计
- **MCP集成**：MCP工具注册到Agent的模式
- **Playwright**：替代CDP做浏览器自动化
- **TOML配置**：比JSON/YAML更简洁的配置方式
- **skills机制**：可内化到本项目的skill系统

## 坑/注意事项

1. Python版本要求3.12+，不要用3.11
2. MCP服务器需要单独启动（npx/uvx）
3. Playwright首次运行需要`playwright install`
4. Agent并行时注意token上下文长度
5. TOML配置文件里的MCP servers需要真实安装才能用
