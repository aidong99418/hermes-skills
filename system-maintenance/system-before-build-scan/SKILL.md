---
name: system-before-build-scan
description: 系统改造前扫描 — 先摸清已有系统，再决定是复用还是新建。触发：任何涉及改造/修复/新增系统功能的场景。
triggers:
  - 要修复某个功能，却发现写好的代码不跑
  - 要新增监控系统，却不知道已有什么
  - 要改进某块功能，不知道有没有现成的
  - 任何"我以为系统是这样的"的场景
version: 1.0
---

# 系统改造前扫描规范

## 核心理念

**先摸清有什么，再决定做什么。** 机器猫系统经过大量迭代，到处是"你以为可以新建但其实已有"的东西。动手前花5分钟扫描，节省2小时返工。

## 扫描清单（按优先级）

### 🔴 优先级0：系统架构核心
```
/opt/data/organs/          # 器官系统（8个器官）
  auto_healing.py          # 免疫层（全量健康检测）
  organ_bus.py             # 事件总线
  unified_push.py          # 推送通道

/opt/data/neural_network/  # 神经网络
  neural_breath.py         # 呼吸引擎（权值进化）
  organ_gateway.py         # 器官网关API
  organ_registry.json      # 器官注册表

/opt/data/brain/           # 大脑知识网络
  neural/                  # 神经网络脉络
  plugins/                 # 盲区插件（情绪/意图/资源等）

/opt/data/scripts/iron_*.py # 铁律脉络（守护cron等）
```

### 🟡 优先级1：搜索已有实现
遇到问题时，先搜索：
```
# 看是否有现成器官能做这件事
grep -rn "功能关键字" /opt/data/organs/*.py

# 看organ_registry里有没有类似器官
python3 -c "import json; data=json.load(open('/opt/data/neural_network/organ_registry.json')); print([k for k in data if '关键字' in k])"

# 看skill里有没有现成方案
grep -rn "关键字" /opt/data/skills/*/SKILL.md

# 看cron里有没有相关调度
crontab -l | grep -i "关键字"
```

### 🟡 优先级2：验证关键依赖
```
# 验证目标脚本能跑通
python3 /opt/data/organs/auto_healing.py full

# 验证函数可以import（最可靠的方式）
python3 -c "import sys; sys.path.insert(0,'/opt/data/organs'); from auto_healing import full_health_check; print(full_health_check()['score'])"

# 验证cron已在跑
crontab -l
```

## 典型反模式（踩过的坑）

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| 不扫描就新建 | 新文件和旧功能重复，冲突 | 先 grep 再决定新建还是复用 |
| 用CLI文本解析函数输出 | 格式脆弱，容易坏 | 直接 import 调用函数，最可靠 |
| 删旧daemon前不备份替代 | 守护链断裂，系统裸奔 | 删前先写好替代方案 |
| 不加载已有skill | 框架存在却不用，靠自己推理 | 遇到复杂任务先 load skill |
| 用 in 做字符串匹配 | "OK" in "DOWN" → 误判 | 用正则精确匹配 `^OK$` |

## 关键路径映射

| 需求 | 已有器官/系统 | 调用方式 |
|------|-------------|----------|
| 全天候健康检测 | auto_healing.py | `from auto_healing import full_health_check` |
| 器官心跳检测 | auto_healing.check_organ_heartbeat() | `from auto_healing import check_organ_heartbeat` |
| 推送飞书 | unified_push.py | `from unified_push import push_warning/push_error` |
| 事件总线 | organ_bus.py | `from organ_bus import emit, subscribe` |
| 器官注册 | organ_registry.json | `json.load(open(path))` |
| 神经网络权值 | neural_breath.py | `NeuralBreath().learn(from, to, success)` |
| 器官网关 | organ_gateway.py | `from organ_gateway import register_organ, send_to, broadcast` |

## 落地流程

遇到改造/修复任务时：
1. **扫描** → 用grep/文件搜索找已有实现（2分钟）
2. **验证** → 跑通关键依赖（1分钟）
3. **决策** → 有现成→复用，无→新建，模糊→继续挖
4. **执行** → 复用现成接口，不重造轮子
5. **收尾** → 写进交接记录，注明用了哪个已有系统

## 记忆锚点

- **2026-06-03实操教训**：接到"全天候监控"任务，第一反应是想新建守护脚本。
  扫描后发现 auto_healing.py 已有完整免疫层（9项基础设施+8个器官心跳）。
  只需要写一个 cron 包装器调用 `full_health_check()` → unified_push 飞书推送。
  auto_healing.py 有两处语法bug：DETECTION_RULES 重复 healthy_pattern 键 + 缺 severity 字段。
  正确路径：用函数不用CLI文本解析。
