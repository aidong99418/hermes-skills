---
name: system-health-subprocess-truncation
description: system_health.py subprocess脚本通过-c参数传递大JSON返回值时被命令行截断，导致所有器官被误判为critical。症状与根因完全不同，必须通过JSON输出解析才能定位。修复：改用tempfile传递脚本。
triggers: ["健康", "诊断", "架构", "系统", "检查"]
tags: [debug, subprocess, system-health, organ, health-check, command-line]
owner: hermes
created: 2026-06-06
updated: 2026-06-06
version: 1.0
---

# system_health.py subprocess 截断 Bug 诊断与修复

## 问题症状

运行 `/opt/hermes/.venv/bin/python3 /opt/data/brain/organs/system_health.py` 时：
- 所有器官（13个）显示 `❌ critical`
- 健康度 `0%`
- 但直接 import 器官测试 `health_check()` 全部返回 `healthy=True`

## 根因

`_get_organ_health_subprocess` 用 `-c` 参数传递脚本，当器官返回大JSON（中文+ensure_ascii=False）时，f-string插值后超系统ARG_MAX限制 → 命令行被截断 → `_json.dumps(res`截断成无效代码 → subprocess解析失败 → 所有器官被判`critical`。

**特征**：症状（全部critical）与根因（命令行截断）完全不同。

## 定位方法

1. 运行 `python3 brain/organs/system_health.py --json` 获取原始输出
2. 检查 `"note"` 字段内容
3. 如果看到 `"执行失败: Traceback... _json.dumps(res"` → 命令行截断
4. 对比：直接import器官测试health_check() → 全部正常

## 修复方案

用 tempfile 替代 `-c` 参数（完整代码见 system_health.py _get_organ_health_subprocess 函数，2026-06-06已修复）。

核心原则：subprocess脚本传递内容超50KB或含中文时，**永远用tempfile而非-c参数**。

## 验证

```bash
/opt/hermes/.venv/bin/python3 /opt/data/brain/organs/system_health.py
# 应输出：整体健康度: 100% [low]，13个器官全部 ✅
```
