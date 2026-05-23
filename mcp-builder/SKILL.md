---
name: mcp-builder
description: 创建高质量MCP (Model Context Protocol) 服务器，使LLM能与外部服务交互。用于构建MCP服务器集成外部API/服务，无论Python (FastMCP) 还是 Node/TypeScript。
triggers:
  - "mcp"
  - "MCP服务器"
  - "model context protocol"
  - "构建MCP"
---

# MCP Server Development Guide

## 概述

MCP服务器让LLM通过精心设计的工具与外部服务交互。质量衡量标准：它让LLM完成真实任务的效率。

---

## 流程

### Phase 1: 深度研究

#### 1.1 理解现代MCP设计

**API覆盖 vs 工作流工具**：
- 平衡全面的API端点覆盖与专门的工作流工具
- 不确定时，优先全面的API覆盖

**工具命名**：
- 清晰、描述性的工具名帮助Agent快速找到正确工具
- 用一致前缀（如 `github_create_issue`、`github_list_repos`）
- 用动作导向命名

**上下文管理**：
- 工具描述要简洁，Agent能过滤/分页结果
- 设计返回聚焦、相关数据的工具

**可操作的错误消息**：
- 错误消息应带具体建议和下一步引导

#### 1.2 研究MCP协议文档

从 sitemap 开始：`https://modelcontextprotocol.io/sitemap.xml`

关键页面：
- 规范概述和架构
- 传输机制（streamable HTTP、stdio）
- 工具、资源、提示定义

#### 1.3 研究框架文档

**推荐技术栈**：
- **语言**：TypeScript（高质量SDK，AI模型擅长生成TS代码）
- **传输**：远程服务器用Streamable HTTP，本地服务器用stdio

#### 1.4 规划实现

- 审查服务的API文档，识别关键端点、认证要求、数据模型
- 列出要实现的端点，从最常见操作开始

---

### Phase 2: 实现

#### 2.1 设置项目结构

按语言指南设置：
- TypeScript: package.json + tsconfig.json
- Python: 模块组织 + 依赖

#### 2.2 实现核心基础设施

创建共享工具：
- 带认证的API客户端
- 错误处理助手
- 响应格式化（JSON/Markdown）
- 分页支持

#### 2.3 实现工具

每个工具：
- **输入Schema**：用 Zod（TS）或 Pydantic（Python），含约束和清晰描述
- **输出Schema**：定义 `outputSchema`，用 `structuredContent`
- **工具描述**：简洁的功能摘要、参数描述、返回类型
- **实现**：async/await，正确的可操作错误处理，支持分页，返回文本内容和结构化数据

**注解**：
- `readOnlyHint`: true/false
- `destructiveHint`: true/false
- `idempotentHint`: true/false
- `openWorldHint`: true/false

---

### Phase 3: 审查和测试

#### 代码质量审查
- 无重复代码（DRY原则）
- 一致的错误处理
- 完整类型覆盖
- 清晰的工具描述

#### 构建和测试

**TypeScript**：
```bash
npm run build  # 验证编译
npx @modelcontextprotocol/inspector  # MCP Inspector测试
```

**Python**：
```bash
python -m py_compile your_server.py  # 验证语法
# MCP Inspector测试
```

---

### Phase 4: 创建评估

创建综合评估来测试有效性：

1. **工具检查**：列出可用工具，理解其能力
2. **内容探索**：用只读操作探索可用数据
3. **问题生成**：创建10个复杂现实问题
4. **答案验证**：自己解决每个问题来验证答案

#### 问题要求

每个问题必须：
- **独立**：不依赖其他问题
- **只读**：只需非破坏性操作
- **复杂**：需要多个工具调用和深度探索
- **现实**：基于人类关心的真实用例
- **可验证**：单一明确答案可字符串比对
- **稳定**：答案不会随时间变化

---

## MCP设计最佳实践

### 工具命名
- 用 `service_action_noun` 格式：`github_create_issue`、`github_list_repos`
- 动作前缀要一致：create/read/update/delete/list

### 响应格式
- **结构化数据**：JSON格式便于Agent处理
- **可读文本**：人类友好的文本输出
- 两者都给，让客户端选择

### 分页
- 所有列表工具支持分页
- 返回总计数和下一页标记
- 支持 `limit` 和 `offset` 或 `cursor` 参数

### 错误处理
- 每个错误带HTTP状态码
- 提供可操作的建议
- 不暴露内部实现细节

### 认证
- 环境变量存储密钥
- 清晰的认证流程文档
- 支持OAuth/PAT/API Key多种方式
