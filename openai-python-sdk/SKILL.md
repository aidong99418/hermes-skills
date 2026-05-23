---
name: openai-python-sdk
description: OpenAI Python SDK — 30k⭐，同步+异步双客户端，pydantic类型定义，httpx驱动，API兼容SiliconFlow等OpenAI兼容接口。触发：OpenAI API、Python调用LLM、异步LLM调用、API兼容接口。
version: 1.0.0
tags: [openai, python, SDK, async, httpx, pydantic]
triggers: ["openai", "openai-python", "Python LLM", "异步调用", "API客户端", "SiliconFlow兼容"]
---

# OpenAI Python SDK 架构参考

## 核心定位
OpenAI Python SDK = 官方Python客户端（30k⭐），基于httpx的同步/异步双客户端，pydantic类型校验，生成的类型定义完整。从OpenAPI规范自动生成，API格式标准，可对接SiliconFlow等兼容OpenAI接口的平台。

## 核心架构

```
用户代码
    │
    ▼
OpenAI Client（同步/异步）
    ├── API配置（base_url / api_key / timeout）
    ├── httpx.Client / httpx.AsyncClient
    └── pydantic Request/Response 类型
           │
           ▼
    REST API → OpenAI / SiliconFlow / 自建API
```

## 快速开始

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxx",                          # API Key
    base_url="https://api.openai.com/v1",      # 可替换为其他兼容端点
    timeout=30,                                # 超时（秒）
    max_retries=3,                             # 自动重试次数
)

# 同步调用
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"}
    ],
    temperature=0.7,
    max_tokens=200,
)

print(response.choices[0].message.content)
print(response.usage.total_tokens)
```

## 异步调用

```python
import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
        api_key="sk-xxx",
        base_url="https://api.siliconflow.cn/v1",  # SiliconFlow
    )

    # 并发调用
    tasks = [
        client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V2.5",
            messages=[{"role": "user", "content": f"任务{i}"}]
        )
        for i in range(5)
    ]
    responses = await asyncio.gather(*tasks)
    return [r.choices[0].message.content for r in responses]

asyncio.run(main())
```

## 流式响应

```python
# 同步流式
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "写一个故事"}],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# 异步流式
async def stream_chat():
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "解释量子计算"}],
        stream=True,
    )
    async for chunk in stream:
        print(chunk.choices[0].delta.content, end="")
```

## 图像理解

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "这张图里有什么？"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}
        ]
    }]
)
```

## 函数调用（Tool Use）

```python
# 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"}
                },
                "required": ["city"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京今天热吗？"}],
    tools=tools,
)

# 提取函数调用
tool_call = response.choices[0].message.tool_calls[0]
fn_name = tool_call.function.name
fn_args = json.loads(tool_call.function.arguments)
print(f"调用函数: {fn_name}, 参数: {fn_args}")
```

## 兼容SiliconFlow（免翻+低价）

```python
from openai import OpenAI

sf = OpenAI(
    api_key="sk-xxx",  # SiliconFlow API Key
    base_url="https://api.siliconflow.cn/v1",  # 关键：换base_url
)

# 完全兼容OpenAI格式，换model名即可
response = sf.chat.completions.create(
    model="deepseek-ai/DeepSeek-V2.5",  # SiliconFlow模型
    messages=[{"role": "user", "content": "你好"}],
)
```

## 错误处理

```python
from openai import OpenAI, APIError, RateLimitError

client = OpenAI(api_key="sk-xxx", max_retries=3)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
    )
except RateLimitError:
    print("触达速率限制，等待后重试")
except APIError as e:
    print(f"API错误: {e.status_code} {e.message}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 与本项目的契合点

| OpenAI SDK特性 | 借鉴场景 |
|---------------|---------|
| 异步客户端 | Ollama SDK也可参考此模式 |
| 流式响应 | 实时TTS/对话流式输出 |
| 工具调用 | Agent的工具注册机制 |
| base_url替换 | 一套代码切换OpenAI/SiliconFlow/Ollama |
| pydantic类型 | Request/Response强类型设计 |
| httpx底层 | 比requests更现代的HTTP客户端 |

## 坑/注意事项

1. **API Key安全**：不要硬编码，用环境变量`os.environ["OPENAI_API_KEY"]`
2. **base_url末尾斜杠**：必须带`/v1`，否则404
3. **异步必须用AsyncOpenAI**：同步客户端在异步函数里会阻塞事件循环
4. **流式响应不是list**：需要`async for`或`for`遍历
5. **max_retries默认3**：对速率限制自动重试，生产环境建议开启
6. **模型名格式**：SiliconFlow用`provider/model`格式如`deepseek-ai/DeepSeek-V2.5`
