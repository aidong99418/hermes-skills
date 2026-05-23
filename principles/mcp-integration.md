# MCP (Model Context Protocol) 集成

## 概览
MCP是连接Hermes Agent和外部工具的桥梁协议。通过配置，可以把任意MCP服务器的工具注册成本地工具调用。

## 两种传输方式

### Stdio传输（本地子进程）
```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxx"
```

### HTTP传输（远程服务器）
```yaml
mcp_servers:
  remote_api:
    url: "https://mcp.example.com/mcp"
    headers:
      Authorization: "Bearer sk-xxx"
```

## 常用MCP服务器

| 服务器 | 命令 | 能力 |
|--------|------|------|
| github | `npx -y @modelcontextprotocol/server-github` | Issues/PR/Commits |
| filesystem | `npx -y @modelcontextprotocol/server-filesystem /path` | 文件读写 |
| time | `uvx mcp-server-time` | 获取当前时间 |
| sqlite | `uvx mcp-server-sqlite /data.db` | SQLite查询 |

## 工具命名规则
MCP工具注册后统一前缀：`mcp_{服务器名}_{工具名}`
例如：`mcp_github_create_pull_request`

## 安全注意
- 环境变量默认不过滤，只有在config里显式声明才传给子进程
- 错误消息自动过滤credentials
- 不信任的服务器可用 `sampling: { enabled: false }`

## 与mcporter的区别
- **native-mcp**: 配置一次，常驻所有对话可用
- **mcporter**: 临时调用，无需配置

## 核心要点
1. **协议**: MCP是标准化工具集成协议
2. **传输**: 支持stdio(本地)和HTTP(远程)两种方式
3. **命名**: 统一使用 `mcp_{server}_{tool}` 前缀
4. **安全**: 环境变量需显式声明才传递，自动过滤敏感信息
5. **用途**: 将GitHub、文件系统、数据库等外部能力集成到Agent
