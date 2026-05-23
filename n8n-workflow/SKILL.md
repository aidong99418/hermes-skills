---
name: n8n-workflow
description: n8n工作流自动化平台 — 189k⭐，fair-code许可，400+集成，原生AI（LangChain），visual+code双模式，Docker一键部署。触发：工作流自动化、n8n集成、IM消息编排、无代码+代码混合。
version: 1.0.0
tags: [workflow, automation, langchain, docker, no-code]
triggers: ["n8n", "工作流自动化", "workflow automation", "无代码工作流", "IM消息编排", "fair-code"]
---

# n8n 工作流自动化参考

## 核心定位
n8n = 189k⭐的工作流自动化平台，fair-code许可可自托管，400+集成，原生AI能力（LangChain），visual+code双模式让技术和业务都能用。

## 核心架构

```
用户操作（Web界面 / API / CLI）
    │
    ▼
┌─────────────────────────────────────┐
│         n8n 执行引擎                  │
│  ┌─────────┐  ┌─────────┐  ┌──────┐│
│  │ Trigger │→│  Node   │→│ Node │→│
│  │ 触发器   │  │  处理   │  │ 输出 ││
│  └─────────┘  └─────────┘  └──────┘│
│  支持并行/条件/循环/错误处理          │
└─────────────────────────────────────┘
    │
    ▼
集成层（400+）：Slack/GitHub/飞书/Dify/ollama/...
```

## 两种工作流模式

### 1. Visual模式（无代码）
- 拖拽式节点编排
- 适合：简单IFTTT类自动化
- 触发器：Webhook/定时/事件

### 2. Code模式（代码）
- 在工作流中写JavaScript/Python
- 可以import npm包/PyPI包
- 适合：复杂逻辑、数据处理、AI调用

```javascript
// Code节点示例：调用本地Ollama
const response = await fetch('http://localhost:11434/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'qwen2.5:3b',
    prompt: $input.item.json.user_input,
    stream: false
  })
});
const data = await response.json();
return { json: { reply: data.response } };
```

## AI Native：LangChain集成

n8n原生支持LangChain，可构建AI Agent工作流：

```javascript
// AI Agent工作流节点
const { OpenAI } = require('langchain/llms/openai');
const { AgentExecutor, loadAgent } = require('langchain/agents');
// 构建Agent → 连接Tools → 执行任务
```

关键AI节点：
| 节点 | 用途 |
|------|------|
| AI Agent | LangChain Agent执行 |
| LLMs | OpenAI/Ollama/本地模型 |
| Memory | 对话记忆存储 |
| Chain | Prompt模板链 |

## Docker一键部署

```bash
# 最简部署
docker volume create n8n_data
docker run -it --rm --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n

# 数据持久化+外部数据库
docker run -it --rm --name n8n \
  -p 5678:5678 \
  -e N8N_DB_TYPE=postgresdb \
  -e N8N_DB_POSTGRESDB_HOST=localhost \
  -e N8N_DB_POSTGRESDB_PORT=5432 \
  -e N8N_ENCRYPTION_KEY=your-key \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

访问：`http://localhost:5678`

## 与本项目的契合点

| n8n特性 | 借鉴场景 |
|--------|---------|
| Trigger + Node链式 | cron触发→任务执行的pipeline设计 |
| Code节点 | 复杂逻辑用代码，通用逻辑用visual |
| LangChain集成 | Ollama/LLM接入的统一接口 |
| 400+集成 | 飞书/Slack/微信/钉钉消息统一处理 |
| Webhook触发 | 与Hermes的webhook系统对接 |
| Fair-code | 完全自托管，数据不出NAS |

## 坑/注意事项

1. **AI节点耗资源**：Ollama连接要设超时，避免阻塞工作流
2. **节点版本兼容**：n8n升级后部分自定义节点可能不兼容
3. **PostgreSQL推荐**：数据量大时用外部PostgreSQL替代SQLite
4. **npx开发模式**：生产环境建议Docker，生产数据不丢
5. **执行并发限制**：免费版并发受限，企业版放开
