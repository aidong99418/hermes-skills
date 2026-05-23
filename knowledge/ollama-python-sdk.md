# Ollama Python SDK 核心知识

## 核心能力
- 纯Python调用本地Ollama API，零额外依赖
- 支持同步/异步请求、流式响应（streaming）
- 兼容所有Ollama模型

## 关键API
```python
from ollama import chat, generate, embeddings

# 聊天
response = chat(model='qwen2.5:3b', messages=[
    {'role': 'user', 'content': '问题'}
])
print(response['message']['content'])

# 流式
for chunk in generate(model='qwen2.5:3b', prompt='提示', stream=True):
    print(chunk['response'], end='', flush=True)

# Embedding
emb = embeddings(model='nomic-embed-text', prompt='文本')
```

## 使用场景
- 作为Hermes Agent的Ollama包装层
- 本地RAG的Embedding生成
- 批量文本处理任务

## 踩坑
1. 模型必须先`ollama pull`到本地，否则超时
2. 流式响应需手动flush，否则输出延迟
3. 异步版本`AsyncClient`需`aiohttp`依赖

## 与hermes集成
- brain_invoke.py用requests直接调API（不等SDK）
- SDK适合长期稳定的服务封装
