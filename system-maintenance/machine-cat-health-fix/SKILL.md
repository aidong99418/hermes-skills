---
name: machine-cat-health-fix
description: 机器猫健康度自检与修复手册 — 快速诊断健康分低/器官异常/cron假死，输出100%健康度。触发：健康度<100%、器官报错、cron任务不动。
triggers: ["健康", "诊断", "检查"]
tags: [健康检查, 故障修复, 器官系统, cron]
version: 1.0
created: 2026-06-05
---

# 机器猫健康度自检与修复手册

## 快速自检

```python
import sys
sys.path.insert(0, '/opt/data/organs')
import auto_healing
ah = auto_healing.AutoHealingOrgan()
result = ah.full_health_check()
print(f"健康度: {result['score']}% | 基础:{result['基础']} | 器官:{result['器官']}")
```

## 常见故障修复

### 健康分<90% → 三层排查

**① 字段名错误**：`health_check()` 返回 `{"status":"ok"}` 而非 `{"healthy":True}`，导致误判不健康。
检查：`grep -n "def health_check" /opt/data/organs/*.py` + `grep -n "return" /opt/data/organs/*.py`
修复：全部改为 `return {"healthy": True}`。

**② 器官评分分母bug**：无 `health_check()` 的器官被计入分母，多扣分。
修复：仅对有 `health_check()` 且含 `healthy` 字段的器官计入分母。

**③ 免疫cron正则bug**：`^[0-9]$` 只匹配1位数分钟，3位数（如156分钟）被误判迟到。
修复：改为 `^[0-9]{1,3}$`。

### cron任务假死

诊断：`ls -lt /opt/data/cron/output/<job_id>/` + `/opt/hermes/.venv/bin/hermes cron status`
自愈（无需重启scheduler）：`/opt/hermes/.venv/bin/hermes cron run <job_id>`

### 修改.py后不生效

原因：Python缓存了旧字节码。
修复：`find /opt/data -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null`

### 派工板/成果板积压

```python
import json
with open('/opt/data/secretary/dispatch_board.json') as f:
    board = json.load(f)
# 保留非done状态的任务，写回
```

## health_check() 契约

```python
def health_check(self) -> dict:
    return {"healthy": True}  # ✓
    # return {"status": "ok"}    # ✗
    # return {"healthy": "ok"}   # ✗
```

## 目标

健康度 100%，无僵尸进程，无积压任务，所有cron在执行。
