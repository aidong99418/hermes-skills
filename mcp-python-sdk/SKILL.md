---
name: mcp-python-sdk
description: MCP官方Python SDK——23k⭐，构建MCP服务器和客户端的完整Python实现。FastMCP装饰器模式+Pydantic v2类型+uv包管理+Streamable HTTP传输+v2版本重构中。触发：构建MCP服务器、编写MCP工具、Python MCP开发、MCP客户端连接。
triggers: ["MCP Python", "FastMCP", "mcp.server", "MCPServer Python", "model context protocol python"]
---

# MCP Python SDK 深度分析

## 一句话
MCP协议的官方Python实现——用装饰器5行代码写一个MCP服务器，支持stdio/Streamable HTTP两种运行方式。

## 核心数据
| 指标 | 数值 |
|------|------|
| ⭐ Stars | 23,099 |
| 🐍 语言 | Python（>=3.10） |
| 📦 安装 | `uv add "mcp[cli]"` |
| 🔧 包管理 | 强制uv（禁止pip） |
| 📂 源码 | src/mcp/{server,client,shared,types}/ |
| ⚠️ 版本 | v1.x稳定，v2开发中（pre-alpha） |

## 对我们价值评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **契合度** | ⭐⭐⭐⭐⭐ 10/10 | 我们正在用MCP，这是官方SDK必须掌握 |
| **实用性** | ⭐⭐⭐⭐⭐ 10/10 | 所有自制MCP服务器都用它 |
| **学习价值** | ⭐⭐⭐⭐⭐ 9/10 | 最佳Python异步编程范本、Pydantic v2实战 |
| **集成难度** | ⭐⭐⭐⭐⭐ 10/10 | uv安装即用，代码质量极高 |
| **综合** | **9.8/10** | 核心中的核心，优先级最高 |

## 架构全览

```
MCP Server (我们的工具暴露层)
├── MCPServer（v2推荐，高级API）
│   ├── @server.tool() — 暴露工具
│   ├── @server.resource() — 暴露资源
│   ├── @server.prompt() — 暴露prompt模板
│   └── lifespan — 启动/关闭生命周期
├── FastMCP（v1风格，快速开发）
│   ├── @mcp.tool()
│   ├── @mcp.resource()
│   └── @mcp.prompt()
└── 低级Server（手写协议，特殊需求）

Transport（传输层）
├── stdio — 本地进程通信（Claude Desktop等）
└── Streamable HTTP — 远程服务器（推荐）

MCP Client（连接消费层）
├── Client — 连接任意MCP服务器
├── Context — 请求上下文
└── 认证 — OAuth2 / Bearer Token
```

## 源码结构（重点目录）

```
src/mcp/
├── server/
│   ├── mcpserver/server.py      ← v2新版MCPServer核心
│   ├── fastmcp/                 ← v1 FastMCP装饰器
│   ├── lowlevel/server.py       ← 底层协议实现
│   ├── auth/                    ← OAuth2服务端
│   └── {stdio,streamable_http,sse,websocket}/  ← 传输层
├── client/
│   ├── client.py                ← MCP客户端核心
│   ├── session.py               ← 会话管理
│   ├── auth/                    ← OAuth2客户端
│   └── {stdio,streamable_http,sse,websocket}/  ← 传输层
├── shared/
│   ├── exceptions.py            ← 统一异常定义
│   ├── tool_name_validation.py  ← 工具名规范
│   └── {memory,message,response_router}/ ← 共享工具
└── types/
    ├── _types.py                ← Zod schemas生成的所有类型
    └── jsonrpc.py               ← JSON-RPC协议类型
```

## 快速上手

### 安装
```bash
# 强制用uv（禁止pip）
uv init mcp-server-demo
cd mcp-server-demo
uv add "mcp[cli]"
```

### v2新版MCPServer（推荐）
```python
"""MCPServer quickstart — v2推荐写法"""
from mcp.server.mcpserver import MCPServer, Context
from dataclasses import dataclass
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

@dataclass
class AppContext:
    db: "Database"

@asynccontextmanager
async def app_lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    # 启动时：连接数据库等
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # 关闭时：清理资源
        await db.disconnect()

mcp = MCPServer("MyApp", lifespan=app_lifespan)

@mcp.tool()
def query_db(ctx: Context[AppContext]) -> str:
    """查询数据库工具"""
    db = ctx.request_context.lifespan_context.db
    return db.query()

# 运行（Streamable HTTP，推荐远程部署）
if __name__ == "__main__":
    mcp.run(transport="streamable-http", json_response=True)
```

### v1 FastMCP（简洁快速）
```python
"""FastMCP quickstart — v1风格，最快上手"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo", json_response=True)

@mcp.tool()
def add(a: int, b: int) -> int:
    """加法工具"""
    return a + b

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """动态问候资源"""
    return f"Hello, {name}!"

@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """生成prompt模板"""
    return f"Please write a {style} greeting for {name}."

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### MCP Client（连接服务器）
```python
from mcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        # 列出可用工具
        tools = await client.list_tools()
        
        # 调用工具
        result = await client.call_tool("add", {"a": 3, "b": 5})
        
        # 读取资源
        greeting = await client.read_resource("greeting://Alice")
```

### 挂载到现有ASGI服务器
```python
# 挂载到FastAPI
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

app = FastAPI()
mcp = FastMCP("MyApp")

# 将MCP挂载到 /mcp 路径
await mcp.mount_to_app(app, "/mcp")
```

## Pydantic v2 类型实战

```python
from pydantic import BaseModel, Field
from typing import Annotated

class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词", min_length=1)
    limit: int = Field(default=10, ge=1, le=100)

class SearchOutput(BaseModel):
    results: list[dict]
    total: int

@mcp.tool()
def search(input: SearchInput) -> SearchOutput:
    """带Pydantic验证的搜索工具"""
    results = do_search(input.query, input.limit)
    return SearchOutput(results=results, total=len(results))
```

## Streamable HTTP（推荐传输方式）

```python
# 服务端
mcp.run(
    transport="streamable-http",
    host="0.0.0.0",
    port=8000,
    json_response=True,  # v2支持结构化JSON响应
)

# 客户端（与stdio用法一致）
async with Client("http://localhost:8000/mcp") as client:
    result = await client.call_tool("tool_name", args)
```

## 认证机制

```python
# Bearer Token认证（服务端）
mcp.run(
    transport="streamable-http",
    json_response=True,
    secret="your-secret-key",
)

# 客户端使用
async with Client(
    url="http://localhost:8000/mcp",
    auth={"type": "bearer", "token": "..."}
) as client:
    ...
```

## 我们的集成点

### 1. 构建定制MCP服务器
将GitHub API、文件操作、WeChat等封装为MCP服务器，用MCPServer重写mcp-builder中的示例。

### 2. 替换现有简单实现
- 现有`/opt/data/gems/mcp-getting-started/`用raw实现 → 迁移到MCPServer
- 自定义工具用Pydantic v2加强类型安全

### 3. MCP客户端能力
用Client连接官方`github-mcp`、`filesystem-mcp`等服务器

### 4. 异步模式学习
MCPServer是Python异步编程的最佳范例：
- `@asynccontextmanager`生命周期管理
- `Context[AppContext]`类型安全的依赖注入
- `AsyncIterator`流式资源

## 关键设计模式

```python
# 1. 类型安全的生命周期Context
@dataclass
class DBContext:
    pool: AsyncSessionPool

@asynccontextmanager
async def db_lifespan(server: MCPServer) -> AsyncIterator[DBContext]:
    pool = await create_pool()
    yield DBContext(pool=pool)
    await pool.close()

@mcp.tool()
async def query(ctx: Context[DBContext], sql: str) -> str:
    # 通过ctx访问启动时初始化的资源
    result = await ctx.request_context.lifespan_context.pool.execute(sql)
    return str(result)

# 2. 工具注解（v2新特性）
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
def safe_query(sql: str) -> str:
    ...

# 3. Structured Output（v2）
mcp.run(transport="streamable-http", json_response=True)
# 返回Pydantic模型自动序列化为JSON
```

## v1 vs v2 对比

| 特性 | v1 (FastMCP) | v2 (MCPServer) |
|------|-------------|----------------|
| API | `@mcp.tool()` | `@server.tool()` |
| Context | 隐式全局 | 类型安全显式 |
| 生命周期 | 简单 | `asynccontextmanager` |
| JSON响应 | 普通文本 | `json_response=True`结构化 |
| 稳定性 | 稳定 | 开发中（Q1 2026发布） |

## 规范（开发准则）
- **强制uv**：所有操作必须`uv add/uv run`，禁止`pip`
- **类型提示**：所有公开API必须有类型注解
- **docstring**：所有异常情况在`Raises:`中注明
- **异常处理**：必须`logger.exception()`，禁止裸`except Exception:`
- **覆盖率**：CI要求100%，`strict-no-cover`检查

## 参考资源
- PyPI：pypi.org/project/mcp/
- 文档：modelcontextprotocol.github.io/python-sdk/
- v2开发文档：`README.v2.md`（在仓库中）
- 开发规范：`AGENTS.md`（源码中有完整指南）
