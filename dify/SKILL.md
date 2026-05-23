---
name: dify
description: Dify低代码LLM应用平台 — 142k⭐，中文社区活跃，Agentic Workflow，RAG流程编排，Prompt工程，多模型支持，云+自部署。触发：Dify、LLM应用开发、低代码AI、RAG编排、Agent工作流。
version: 1.0.0
tags: [llm-app, rag, workflow, low-code, agent, chinese]
triggers: ["Dify", "dify", "低代码AI", "LLM应用平台", "RAG编排", "Agent工作流", "Prompt工程"]
---

# Dify 架构设计参考

## 核心定位
Dify = 低代码LLM应用构建平台（142k⭐），中文社区极度活跃，支持Agent工作流、RAG流程编排、Prompt工程，多模型接入。核心价值：**让非开发者也能快速上线AI应用**。

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                    Dify 平台                             │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  应用类型    │  │   能力模块    │  │   模型接入    │   │
│  │  ├─ Chatbot │  │  ├─ Agent   │  │  ├─ OpenAI   │   │
│  │  ├─ Agent   │  │  ├─ Workflow│  │  ├─ Claude   │   │
│  │  ├─ Workflow│  │  ├─ RAG     │  │  ├─ Ollama   │   │
│  │  └─ Assistant│ │  └─ Prompt │  │  └─ 本地模型  │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
      用户界面        可视化编排        模型层
    (Web/App/API)  (低代码画布)     (云+本地)
```

## 应用类型

### 1. Chatbot（对话机器人）
- 开箱即用的对话界面
- 支持多轮对话、函数调用
- 可嵌入网站/App

### 2. Agent（智能体）
- LLM自主决策+工具调用
- ReAct模式
- 支持自定义工具

### 3. Workflow（工作流）
- 可视化流程编排
- 支持代码节点、模板节点
- 定时/触发器启动

### 4. Completion（文本补全）
- 纯Prompt工程
- API调用

## Workflow可视化编排

```
┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐
│ LLM  │───→│ HTTP │───→│ Code │───→│ RAG  │───→ 输出
│ 节点  │    │ 请求  │    │ 节点  │    │ 检索  │
└──────┘    └──────┘    └──────┘    └──────┘
   │                                          
   └──────────→ 条件分支 ──────────→ [A] / [B]
```

关键节点：
| 节点 | 用途 |
|------|------|
| LLM | 模型调用 |
| HTTP | 调用外部API |
| Code | Python/JS处理 |
| RAG | 知识库检索 |
| Template | 文本模板 |
|_IF/Else| 条件分支 |
| Loop | 循环执行 |
| Iterator | 批量处理 |

## RAG流程编排

Dify的RAG是完整pipeline：

```python
# RAG流程：文档上传 → 分块 → 向量化 → 检索 → 生成

# 1. 文档上传（支持PDF/TXT/Markdown/URL）
# 2. 预处理器：自动分块（按段落/句子/固定长度）
# 3. 向量化：选Embedding模型（本地Ollama也行）
# 4. 检索：语义相似度 + 重排序
# 5. 生成：Context注入Prompt
```

支持的知识源：
- 上传文档（自动分块）
- Web站点抓取
- Notion同步
- API数据拉取
- 数据库查询

## Prompt工程

```markdown
## 系统提示词模板
你是一个{{role}}，专门负责{{task}}。

## 上下文
{{context}}

## 限制
1. {{constraint_1}}
2. {{constraint_2}}

## 输出格式
{{format_instruction}}
```

变量类型：text / number / select / paragraph / date / file

## 多模型接入

```python
# Dify支持的主流模型
# 云端：OpenAI / Claude / Gemini / DeepSeek
# 本地：Ollama（推荐！零成本接入本地模型）

# Ollama接入配置
基础URL: http://your-nas-ip:11434/v1
模型: qwen2.5:7b-instruct
```

## Docker一键部署

```bash
# 最简部署
git clone https://github.com/langgenius/dify.git
cd dify/docker
docker-compose up -d

# 访问 http://localhost:80
# 默认管理员: admin@dify.local / admin@dify.local

# 仅启动后端（节省资源）
docker-compose -f docker-compose.yaml up -d
```

## 与本项目的契合点

| Dify特性 | 借鉴场景 |
|---------|---------|
| 低代码Workflow | 可视化任务编排（n8n对比） |
| RAG完整pipeline | 知识库检索流程（分块→向量→重排→生成） |
| Agent工具调用 | 外部工具注册机制 |
| 多模型统一接入 | Ollama/SiliconFlow模型切换 |
| API发布 | AI应用一键发布为API |
| 中文社区 | 文档和示例更贴近中文场景 |

## 坑/注意事项

1. **资源占用**：Docker完整部署需要4GB+内存
2. **RAG质量**：分块策略直接影响检索效果，需要调优
3. **Agent循环**：ReAct模式需要设置最大步数，避免无限循环
4. **模型配额**：云端模型API费用要监控
5. **数据安全**：自部署时注意数据隔离
