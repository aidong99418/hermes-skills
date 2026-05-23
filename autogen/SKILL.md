---
name: autogen
description: AutoGen微软多Agent框架 — 58k⭐，Conversational+CodeExecution双Agent，对话协作+代码生成执行，GroupChat多Agent轮询。触发：多Agent对话、微软AutoGen、代码生成执行、GroupChat协作。
version: 1.0.0
tags: [multi-agent, code-execution, Microsoft, conversation, groupchat]
triggers: ["AutoGen", "autogen", "微软多Agent", "代码生成执行", "GroupChat", "ConversationalAgent"]
---

# AutoGen 架构设计参考

## 核心定位
AutoGen = 微软开源的多Agent编程框架（58k⭐），核心：让多个LLM Agent对话协作解决问题，支持代码生成+执行。最独特的设计：**ConversationalAgent（对话）+ CodeExecutionAgent（代码执行）分离**。

## 核心架构

```
用户任务
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              AutoGen Agent生态                       │
│                                                     │
│  ┌────────────────┐    ┌────────────────────────┐  │
│  │ Conversational │←──→│  CodeExecutionAgent    │  │
│  │ Agent          │    │  （代码生成+执行）       │  │
│  │ （对话决策）     │    │  支持Python/Shell      │  │
│  └───────┬────────┘    └────────────────────────┘  │
│          │                                            │
│          ▼                                            │
│  ┌───────────────────────────────────────────────┐  │
│  │ GroupChat（多Agent轮询协作）                     │  │
│  │  Agent1 ↔ Agent2 ↔ Agent3 ↔ ...               │  │
│  │  管理员控制发言顺序，可设置终止条件               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 两种核心Agent

### 1. ConversationalAgent（对话Agent）
```python
from autogen import ConversationalAgent

assistant = ConversationalAgent(
    name="assistant",
    system_message="你是一个Python专家，擅长写高质量代码。",
    llm_config={
        "model": "gpt-4o",
        "api_key": os.environ["OPENAI_API_KEY"],
        "temperature": 0.7,
    }
)
```

### 2. CodeExecutionAgent（代码执行Agent）
```python
from autogen import CodeExecutionAgent

executor = CodeExecutionAgent(
    name="executor",
    code_execution_config={
        "use_docker": True,  # Docker沙箱执行
        "timeout": 60,
    }
)
```

### 3. UserProxyAgent（用户代理）
```python
from autogen import UserProxyAgent

user = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",  # NEVER/TERMINATE/ALWAYS
    max_consecutive_auto_reply=10,
    code_execution_config={"use_docker": False}
)
```

## GroupChat多Agent协作

```python
from autogen import GroupChat, GroupChatManager

groupchat = GroupChat(
    agents=[user, assistant, executor, critic],
    messages=[],
    max_round=12,
    speaker_selection_method="round_robin",  # 轮询
    # 或 "auto"（LLM自动选下一个发言者）
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# 启动群聊
user.initiate_chat(
    manager,
    message="帮我分析这个CSV文件并生成报告"
)
```

## 对话模式示例

```python
import autogen

llm_config = {
    "model": "gpt-4o",
    "api_key": os.environ["OPENAI_API_KEY"],
}

# 创建Agent
assistant = autogen.ConversationalAgent(
    name="writer",
    system_message="你是一个技术写作者，负责撰写清晰简洁的文档。",
    llm_config=llm_config,
)

user = autogen.UserProxyAgent(name="user", human_input_mode="NEVER")

# 开始对话
user.initiate_chat(
    assistant,
    message="帮我写一个关于n8n工作流自动化的介绍文档，200字。"
)
```

## 代码执行示例

```python
from autogen import ConversationalAgent, CodeExecutionAgent

# 对话Agent生成代码 → CodeAgent执行
math_agent = ConversationalAgent(
    name="math_expert",
    system_message="你擅长数学计算，用Python解决复杂问题。",
    llm_config=llm_config,
)

code_executor = CodeExecutionAgent(
    name="python_executor",
    code_execution_config={
        "use_docker": "python:3.11-slim",
        "timeout": 30,
    }
)

# 自动对话+执行
math_agent.initiate_chat(
    code_executor,
    message="计算1000以内所有素数的和"
)
```

## 与本项目的契合点

| AutoGen特性 | 借鉴场景 |
|------------|---------|
| Agent分离设计 | 决策Agent和执行Agent解耦 |
| GroupChat轮询 | 多Agent顺序协作模式 |
| Docker代码沙箱 | 代码执行安全性 |
| Conversational模式 | 对话式任务分解 |
| 终止条件控制 | 避免Agent无限循环 |

## 快速安装

```bash
pip install autogen[gemini,anthropic]

# 或最新版
pip install autogen
```

## 坑/注意事项

1. **代码执行风险**：use_docker=True建议开启，避免恶意代码
2. **token消耗大**：多Agent对话上下文增长快，设max_round限制
3. **GroupChat死锁**：发言顺序设计不当会导致循环，设终止条件
4. **API兼容性**：AutoGen更新快，新版本API可能有breaking change
5. **本地模型支持**：需要配置Ollama或其他本地LLM的API endpoint
