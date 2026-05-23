# Ollama 模型分层调度体系

## 核心原则

> 按问题复杂度分配模型资源——简单问题用小模型快响应，复杂问题用大模型深推理。

## 四层架构

| 层级 | 模型 | 角色 | 内存 | 触发场景 |
|------|------|------|------|----------|
| fast | smollm2:1.7b | 快速响应 | ~1GB | 查看/查/剩多少 等简单查询 |
| worker | qwen2.5:3b | 后台分析 | ~1GB | 工具调用/脚本生成/后台学习 |
| expert | deepseek-r1:7b | 复杂推理 | ~4GB | 架构/安全/权衡/为什么 |
| tool | qwen2.5:7b-instruct-q4 | 工具调用 | ~4GB | 带工具的复杂任务 |

## 降级链

```
expert故障 → worker → fast，逐级降级保证服务不中断
```

- 降级链要按内存从大到小排列，避免OOM
- 并发调用同一模型会导致队列堆积
- 冷启动deepseek-r1:7b需要约15秒
- 3个模型并行派发时内存占用约9GB

## 保活策略

- smollm2 每分钟warmup一次
- qwen2.5:3b 每10分钟warmup一次
- deepseek-r1:7b 有任务时自动加载
- 超过5分钟空闲自动降级

## 使用场景

- 简单查询：smollm2 直接答（<1秒）
- 需要查资料：qwen2.5:3b 先brain检索再答
- 复杂推理：deepseek-r1:7b 思考后答
- 带工具任务：qwen2.5:7b-instruct-q4 工具调用链

## 常用命令

```bash
# 检查模型健康
curl -s localhost:11434/api/ps

# warmup模型
curl -s localhost:11434/api/generate -d '{"model":"smollm2:1.7b","prompt":"hi"}'

# 卸载模型
curl -s localhost:11434/api/generate -d '{"model":"","keep_alive":0}'
```
