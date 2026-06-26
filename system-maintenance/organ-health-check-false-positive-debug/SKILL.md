---
name: organ-health-check-false-positive-debug
description: 器官健康检测误报修复工作流——区分"检测器bug"与"系统真坏"，2026-05-31实操固化
triggers:
  - 健康检查报告器官❌但系统实际运行正常
  - unified_push报错但飞书实际连通
  - ae4_bridge报错但AE4引擎实际正常
version: 1.0
---

# 器官健康检测误报修复工作流

## 触发条件
健康检查报告显示器官❌，但系统实际运行正常。需要排查是"系统真坏"还是"检测器误报"。

## 诊断三步法

### Step 1: 隔离健康检测器本身
```python
import sys; sys.path.insert(0, '/opt/data')
from organs.器官名 import health_check
import json
r = health_check()
print(json.dumps(r, indent=2, ensure_ascii=False))
```
先看返回结构，找字段名和返回值是否和调用方预期一致。

### Step 2: 追踪返回值的生产链路
常见误报类型：
- **返回值名不匹配**：检测器返回`verdict:"healthy"`，调用方判断`verdict=="ok"` → 永远❌
- **配置模式遗漏**：系统用WebSocket但检测器只看webhook变量 → 永远❌  
- **阈值不适配**：知识积累型系统冷启动期采纳率为0正常，但阈值设0.3 → 永远❌

### Step 3: 交叉验证外部依赖
同一个功能可能有多个配置路径（如飞书：webhook/websocket/配置文件），健康检测必须覆盖所有实际路径。

## 修复优先级
1. **检测器bug**（返回值名/判断逻辑错）→ 直接修检测器，不修被检测对象
2. **阈值不适配**（冷启动/特殊场景）→ 放宽阈值+加注释说明冷启动宽容逻辑
3. **配置覆盖不全**→ 补充所有实际配置模式的检测

## 验证命令
```bash
cd /opt/data && python3 -c "
import sys; sys.path.insert(0, '/opt/data')
from organs.auto_healing import check_organ_heartbeat
for r in check_organ_heartbeat():
    icon = '✅' if r['healthy'] else '❌'
    print(f'{icon} {r[\"organ\"]}: {r.get(\"detail\",{})}')
"
```

## 已知误报模式
| 被检测对象 | 误报类型 | 修复方法 |
|-----------|---------|---------|
| unified_push | 只看webhook，忽略WebSocket | 检测FEISHU_CONNECTION_MODE=websocket |
| ae4_bridge | verdict=="ok"但源码返回"healthy" | 改为 verdict in ("healthy","warning") |
| ae4_bridge | adoption阈值0.3太高（冷启动0.001正常） | 阈值降至0.001 |
| alert_sender | health_check()返回`status`字符串非`healthy`布尔 | 改返回`{"healthy": bool, "detail": "..."}` |
| feishu_card_sender | 同上：返回`status`字段名不匹配 | 同上 |
| task_board | 同上 | 同上 |
| auto_healing.py | 器官评分分母含无health_check的器官→误拉低分 | 评分时用`organ_with_check`替代`organ_results` |
| auto_healing.py | immune_cron正则`^[0-9]$`只匹配个位数(0-9) | 改为`^[0-9]{1,3}$`匹配0-999分钟 |

## 新发现模式：字段名不匹配型误报（2026-06-05）

**症状**：器官有`health_check()`方法，返回看似正常，但`check_organ_heartbeat()`始终计为❌。

**根因**：器官返回`{"status": "healthy", ...}`（字符串字段），而`auto_healing.py`判断逻辑期望`{"healthy": True}`（布尔字段）。`check_organ_heartbeat()`中`result.get("healthy")`对字符串字段返回`None`，被当作失败。

**诊断命令（绕过CLI超时）**：
```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("器官名", "/opt/data/organs/器官名.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
r = module.health_check()
print(f"healthy字段: {r.get('healthy', '❌缺失')}")  # 期望True/False，非字符串
```

**修复标准**：所有器官的`health_check()`必须返回`{"healthy": bool, "detail": str}`，布尔字段名必须是`healthy`。

## 验证时间
2026-05-31，修复后器官层 7/7 ✅
2026-06-05，修复后 92%（基础设施12/12 ✅ 器官11/11 ✅ 免疫日志错误 ✅）
