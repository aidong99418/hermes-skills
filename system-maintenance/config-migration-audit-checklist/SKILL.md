---
name: config-migration-audit-checklist
description: 配置迁移后必查清单 — 防止改动config结构导致下游脚本静默失效（2026-06-08 ENV迁移教训）
triggers:
  - 改了config.yaml结构
  - 改了.env变量
  - 改了custom_providers格式
  - 重构了provider配置布局
  - 配置迁移后发现异常
---

# 配置迁移后必查清单

## 教训来源
2026-06-08 统一配置架构迁移（`.env`单源管理）将 `wisemodel` API key/URL 从 `custom_providers` 迁移到 `model.base_url/api_key` 直接字段，导致 `hermes_code_guard.py` 的 `check_model_api()` 持续报 "provider[custom]配置缺失"（实际上配置存在，只是位置变了）。

## 核心教训
**改config结构时，必须同时审计所有读取该config的脚本。**

Config结构迁移后，常见静默失效点：
1. `check_model_api()` / health check 脚本 — 读provider配置的入口
2. `try_fallback_switch()` — 根据provider名称查找配置
3. 任何读取 `custom_providers` 但没回退逻辑的代码

## 审查步骤

### 第1步：定位所有读config的脚本
```bash
grep -rl "custom_providers\|config.yaml" /opt/data/scripts/ /opt/data/hooks/ 2>/dev/null
```

### 第2步：检查每个脚本的读取模式
- 是否只从 `custom_providers` 数组查找？
- 是否有回退到 `model.base_url` / `model.api_key` 的逻辑？
- 是否有其他读取路径？

### 第3步：对比新旧config结构
写一个对照表：

| 字段 | 迁移前 | 迁移后 |
|------|--------|--------|
| provider名称 | 直接读 | `model.provider` |
| API key | `custom_providers[name].api_key` | `model.api_key` + `${ENV}` |
| base_url | `custom_providers[name].base_url` | `model.base_url` + `${ENV}` |

### 第4步：为每个reader加双重回退逻辑
正确模式：
```python
# 优先从custom_providers查
custom = cfg.get("custom_providers", [])
providers = {p.get("name", ""): p for p in custom}
prov = providers.get(primary, {})

# 回退：2026-06-08 ENV迁移后，部分provider直接写在model段
base_url = prov.get("base_url", "")
api_key = prov.get("api_key", "")
if not base_url or not api_key:
    model_section = cfg.get("model", {})
    base_url = model_section.get("base_url", "")
    api_key = model_section.get("api_key", "")
```

### 第5步：验证health check
```bash
python3 /opt/data/scripts/hermes_code_guard.py
# 确认无 "配置缺失" 误报
```

## 关键文件清单（当前NAS）

| 文件 | 读取方式 | 状态 |
|------|----------|------|
| `hermes_code_guard.py` | `custom_providers` + `model.base_url` 回退 | ✅ 已修复 |
| `switch_to_provider()` | `custom_providers` only | ⚠️ 需迁移前先检查 |
| `try_fallback_switch()` | 依赖`custom_providers`有siliconflow | ✅ siliconflow已加入 |

## 铁律
- 每次改 `config.yaml` 结构，当天内更新 MEMORY.md + 本skill
- 改之前先 grep 所有引用路径，改完立刻验证所有reader
