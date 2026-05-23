---
name: mcp-servers
description: 本地可运行的MCP服务器快速索引——发现→安装→验证，已在/opt/data/gems/验证通过。支持开发/AI/媒体/数据库等8大类别。
triggers: ["MCP服务器", "MCP server", "model context protocol", "mcp快速入门"]
---

# MCP服务器快速索引

## 发现来源
- 官方：`mcp-getting-started` 仓库（8个官方服务器）
- 聚合：`awesome-mcp-servers`（按用途分类的完整列表）

## 快速安装（MCP-Getting-Started）
```bash
cd /opt/data/gems/mcp-getting-started
cat README.md
```

## 已验证的可用服务器

### 数据库
| 服务器 | 用途 | 特点 |
|--------|------|------|
| **pg-mcp** | PostgreSQL | 本地SQL查询，npx直接跑 |
| **sqlite-mcp** | SQLite | 轻量数据库操作 |
| **mysql-mcp** | MySQL | 关系数据库查询 |

### AI/开发
| 服务器 | 用途 | 特点 |
|--------|------|------|
| **github-mcp** | GitHub API | issues/PR/commit/代码搜索 |
| **filesystem-mcp** | 文件系统 | 安全读写，带路径限制 |
| **openapi-mcp** | OpenAPI | REST API调用 |
| **brave-search-mcp** | 网页搜索 | Brave Search API |

### 媒体
| 服务器 | 用途 | 特点 |
|--------|------|------|
| **image-generation-mcp** | 图片生成 | AI图片创作 |
| **youtube-transcript-mcp** | YouTube | 字幕抓取 |

### 工具
| 服务器 | 用途 | 特点 |
|--------|------|------|
| **memory_neural_maker** | 动态记忆 | 自动生成memory条目 |
| **fastmcp** | 框架 | 装饰器快速创建服务器 |

## 架构参考（可借鉴）
- **CowAgent**: Agent+Memory分离，多渠道消息路由
- **browser-use**: AI浏览器自动化，多Agent并发
- **OpenManus**: plan+react+browser三Agent协作

## 安装Checklist
```bash
# 1. 确认Node.js可用
node --version  # >= 18

# 2. 全局安装MCP CLI
npm install -g @modelcontextprotocol/cli

# 3. 验证服务器
mcp dev /path/to/server.js  # 开发模式
mcp start /path/to/server.js  # 生产模式

# 4. 配置Hermes（config.yaml）
# 在mcp_servers添加新服务器路径
```

## 相关Skills
- skill:brain-github-mining（挖宝流程）
- skill:mcp-builder（构建MCP服务器）
- skill:native-mcp（Hermes内置MCP客户端）
