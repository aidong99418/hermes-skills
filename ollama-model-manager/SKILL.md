---
name: ollama-model-manager
description: Ollama模型保活+智能降级管理器。定时warmup关键模型（smollm2快手），主模型故障自动降级到备选，防止OOM并发冲突。NAS常驻必备。
triggers:
  - "ollama挂了"
  - "模型调不通"
  - "保活"
  - "模型故障"
  - "oom"
  - "内存不够"
category: devops
tags: [Ollama, 模型管理, 保活, 故障转移, OOM]
version: 1.0
author: 打工仔
date: 2026-05-23
---

# 🤖 ollama_model_manager — 模型保活+故障降级

## 核心能力
- **保活策略**：定时warmup关键模型（smollm2每分钟一次，其他每10分钟一次）
- **故障降级**：主模型失败→自动切换备选模型（qwen2.5:3b→qwen2.5:7b→deepseek-r1:7b）
- **并发控制**：防止同时加载多个大模型导致OOM
- **状态监控**：实时查看模型健康状态

## 模型层级配置
| 角色 | 模型 | 用途 | 优先级 |
|------|------|------|--------|
| fast（快手） | smollm2:1.7b | 快速响应/批量任务 | ⭐⭐⭐最高 |
| worker（打工仔） | qwen2.5:3b-instruct-q4_K_M | 后台学习/分析报告 | ⭐⭐高 |
| expert（专家） | deepseek-r1:7b-instruct-q4 | 复杂推理/分析 | ⭐⭐中 |
| tool（工具专家） | qwen2.5:7b-instruct-q4_K_M | 工具调用/精确输出 | ⭐⭐中 |

## CLI用法

```bash
# 检查所有模型健康状态
python3 /opt/data/scripts/ollama_model_manager.py --check

# Warmup所有模型
python3 /opt/data/scripts/ollama_model_manager.py --warmup

# 保活模式（持续运行）
python3 /opt/data/scripts/ollama_model_manager.py --keepalive

# 查看状态摘要
python3 /opt/data/scripts/ollama_model_manager.py --status
```

## API用法

```python
import sys
sys.path.insert(0, '/opt/data/scripts')
from ollama_model_manager import OllamaManager

mgr = OllamaManager()

# 检查模型状态
status = mgr.check_all_models()
for model, ok in status.items():
    print(f"{'✅' if ok else '❌'} {model}")

# 带fallback的调用
resp = mgr.call_with_fallback("分析这个问题", prefer="expert")
# 自动降级：expert → tool → worker → fast

# Warmup快手模型
mgr.warmup_fast()
```

## 保活策略实现
```python
MODEL_KEEPALIVE = {
    "smollm2:1.7b": 60,        # 每分钟保活
    "qwen2.5:3b-instruct-q4_K_M": 600,  # 每10分钟
    "deepseek-r1:7b": 600,
    "qwen2.5:7b": 600,
}
```

## 降级路径
```
deepseek-r1:7b → qwen2.5:7b → qwen2.5:3b → smollm2 → 全部失败
```

## 常驻后台
```bash
# nohup后台运行
nohup python3 /opt/data/scripts/ollama_model_manager.py --keepalive > /opt/data/logs/ollama_keepalive.log 2>&1 &
```

## 坑与经验
1. 多模型同时加载会OOM → 加锁控制，同一时间只加载一个
2. smollm2保活不能太频繁 → 每次生成20 token即可，避免占用响应时间
3. Ollama服务挂了 → 捕获requests异常，返回"unavailable"
