---
name: mcp-typescript-sdk
description: MCP官方TypeScript SDK——12.5k⭐，MCP协议的TypeScript/JS实现。monorepo架构（core/client/server/middleware/codemod五包）、Zod v4类型生成、双向JSON-RPC协议、中间件系统、Cloudflare Workers兼容。触发：构建MCP TypeScript服务器、MCP客户端TS开发、Zod schema、MCP中间件。
triggers: ["MCP TypeScript", "@modelcontextprotocol", "typescript mcp server", "mcp client typescript"]
---

# MCP TypeScript SDK 深度分析

## 一句话
MCP协议的TypeScript官方实现——monorepo五包架构（core/client/server/middleware/codemod），双向JSON-RPC协议，Zod v4类型生成，Cloudflare Workers兼容。

## 核心数据
| 指标 | 数值 |
|------|------|
| ⭐ Stars | 12,510 |
| 🦜 语言 | TypeScript |
| 📦 安装 | `pnpm add @modelcontextprotocol/server @modelcontextprotocol/client` |
| 🔧 包管理 | pnpm monorepo |
| 📂 包结构 | core / client / server / middleware / codemod |

## 对我们价值评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **契合度** | ⭐⭐⭐⭐ 8/10 | 我们主要用Python，TS是第二选择 |
| **实用性** | ⭐⭐⭐⭐ 7/10 | Node.js环境下构建MCP服务器时用 |
| **学习价值** | ⭐⭐⭐⭐⭐ 10/10 | Zod v4/协议层/monorepo/中间件系统 高质量范本 |
| **集成难度** | ⭐⭐⭐⭐ 7/10 | 需要Node.js环境，我们NAS以Python为主 |
| **综合** | **8/10** | 作为架构学习优先级高，实际用Python SDK |

## 架构全览

```
TypeScript Monorepo
├── @modelcontextprotocol/core      ← 核心层（协议/类型/传输）
│   ├── types/types.ts              ← Zod v4生成所有协议类型
│   ├── shared/protocol.ts          ← 抽象Protocol类（JSON-RPC路由）
│   ├── shared/transport.ts         ← 传输层抽象
│   └── exports/public/             ← 公开API（types/errors/constants/guards）
├── @modelcontextprotocol/client    ← 客户端层
│   ├── client.ts                   ← Client类，扩展Protocol
│   ├── streamableHttp.ts           ← Streamable HTTP客户端
│   ├── sse.ts                      ← SSE传输
│   └── middleware.ts               ← 请求中间件
├── @modelcontextprotocol/server    ← 服务端层
│   ├── server/server.ts            ← Server基础类
│   ├── server/mcp.ts               ← McpServer高级API（tool/resource/prompt注册）
│   ├── server/streamableHttp.ts    ← Streamable HTTP服务端
│   ├── server/sse.ts               ← SSE服务端
│   ├── server/stdio.ts             ← stdio传输
│   ├── server/auth/                ← OAuth2服务端实现
│   └── experimental/tasks/         ← 长任务支持（轮询/恢复）
├── @modelcontextprotocol/middleware ← 框架适配器
│   ├── express/
│   ├── hono/
│   └── node/
└── @modelcontextprotocol/codemod   ← v1→v2迁移工具
```

## 核心概念：双向协议

MCP是**双向协议**——客户端和服务端都能主动发请求：

```
Client ────────────────► Server
  │      JSON-RPC Request
  │◄───────────────     JSON-RPC Response
  │                      
  │◄───────────────     Server → Client Request
  │      (sampling/      (sampling/createMessage等)
  │       elicitation)   
  │                      
  │      或              Server → Client Notification
  │◄───────────────     (logging/message等)
```

**双向能力：**
- **Sampling**：服务器请求客户端调用LLM
- **Elicitation**：服务器请求用户输入（表单/URL）
- **Roots**：客户端暴露文件系统根目录给服务器

## Zod v4 类型系统（核心亮点）

```typescript
// 类型定义用Zod v4，生成类型+验证+JSON Schema
import { z } from 'zod/v4'

// 工具输入schema
const ToolInputSchema = z.object({
  name: z.string(),
  description: z.string(),
  inputSchema: z.object({
    type: z.literal('object'),
    properties: z.record(z.string(), z.object({
      type: z.string(),
      description: z.string()
    }))
  })
})

// 自动导出TypeScript类型
type ToolInput = z.infer<typeof ToolInputSchema>

// 自动生成JSON Schema（用于协议）
const jsonSchema = standardSchemaToJsonSchema(ToolInputSchema)
```

## 快速上手

### 安装
```bash
pnpm install
```

### McpServer 高级API（推荐）
```typescript
import { McpServer, type ServerOptions } from '@modelcontextprotocol/server'
import { z } from 'zod/v4'

const server = new McpServer({
  name: 'my-server',
  version: '1.0.0',
})

// 注册工具
server.registerTool(
  'search',
  {
    description: 'Search for information',
    inputSchema: z.object({
      query: z.string().describe('Search query'),
      limit: z.number().default(10)
    })
  },
  async ({ arguments: args }) => {
    const results = await search(args.query, args.limit)
    return { content: [{ type: 'text', text: JSON.stringify(results) }] }
  }
)

// 注册资源
server.registerResourceTemplate(
  'file://{path}',
  {
    description: 'Read a file',
    mimeType: 'text/plain'
  },
  async ({ params }) => {
    const content = await readFile(params.path)
    return { contents: [{ uri: `file://${params.path}`, text: content }] }
  }
)

// 注册prompt模板
server.registerPrompt(
  'summarize',
  {
    description: 'Summarize a document',
    arguments: [
      { name: 'document', description: 'Document to summarize', required: true }
    ]
  },
  ({ arguments: args }) => ({
    messages: [{
      role: 'user',
      content: { type: 'text', text: `Please summarize: ${args.document}` }
    }]
  })
)

// 运行（stdio本地模式）
server.start()
```

### Streamable HTTP（推荐远程模式）
```typescript
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/server/streamableHttp'
import { McpServer } from '@modelcontextprotocol/server'

const server = new McpServer({ name: 'my-server', version: '1.0.0' })
const transport = new StreamableHTTPServerTransport({
  validateSessions: true,
  onSessionEnd: async (session) => { /* cleanup */ }
})

await server.connect(transport)
const port = 3000
app.listen(port, () => console.log(`MCP server on http://localhost:${port}/mcp`))
```

### MCP Client
```typescript
import { Client } from '@modelcontextprotocol/client'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/client/streamableHttp'

const transport = new StreamableHTTPClientTransport({
  url: 'http://localhost:3000/mcp'
})

const client = new Client({
  name: 'my-client',
  version: '1.0.0',
}, {
  capabilities: {}
})

await client.connect(transport)

// 列出工具
const tools = await client.request({ method: 'tools/list' })

// 调用工具
const result = await client.request({
  method: 'tools/call',
  params: {
    name: 'search',
    arguments: { query: 'MCP protocol', limit: 5 }
  }
})

// 中间件示例
client.middleware.use(async (request, next) => {
  console.log(`Calling: ${request.method}`)
  const response = await next(request)
  console.log(`Response: ${response.method}`)
  return response
})
```

## 中间件系统

```typescript
// 请求/响应拦截
client.middleware.use(async (request, next) => {
  // 修改请求
  if (request.method === 'tools/call') {
    request.params.arguments = sanitize(request.params.arguments)
  }
  const response = await next(request)
  // 处理响应
  return response
})
```

## 框架适配器（middleware包）

```typescript
// Express适配器
import { expressRequestHandler } from '@modelcontextprotocol/middleware/express'

app.use('/mcp', expressRequestHandler({ server }))

// Hono适配器
import { handle as honoHandler } from '@modelcontextprotocol/middleware/hono'
app.post('/mcp', honoHandler({ server }))

// Node.js HTTP适配器
import { nodeHandler } from '@modelcontextprotocol/middleware/node'
```

## 与Python SDK的对比

| 特性 | Python SDK | TypeScript SDK |
|------|-----------|----------------|
| 装饰器风格 | `@mcp.tool()` | `server.registerTool()` |
| 类型系统 | Pydantic v2 | Zod v4 |
| 生命周期 | `@asynccontextmanager` | 构造函数+connect |
| 中间件 | 无 | 完整中间件系统 |
| 框架适配 | ASGI (FastAPI等) | Express/Hono/Node |
| 浏览器支持 | ❌ | ✅（Cloudflare Workers兼容）|
| 我们的优先级 | **最高** | 次高（架构学习） |

## 我们的使用场景

| 场景 | 用哪个SDK | 原因 |
|------|----------|------|
| 构建MCP服务器 | **Python** | 我们的工具多是Python脚本 |
| Node.js环境MCP | TypeScript | 现有JS项目时 |
| 架构学习 | **TypeScript** | 中间件/协议层代码质量更高 |
| Zod v4实战 | TypeScript | 类型生成最佳范本 |

## 构建命令
```bash
pnpm install              # 安装
pnpm build:all            # 编译所有包
pnpm lint:all             # 检查
pnpm test:all             # 测试
pnpm check:all            # 类型+lint

# 单包开发
pnpm --filter @modelcontextprotocol/core test
pnpm --filter @modelcontextprotocol/server build
```

## 参考资源
- 文档：modelcontextprotocol.io
- 规范：spec.modelcontextprotocol.io
- 源码：modelcontextprotocol/typescript-sdk
- 迁移指南：docs/migration.md（v1→v2）
