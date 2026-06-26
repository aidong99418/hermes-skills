---
name: task-recovery-cron-audit
description: task_recovery_cron.py 执行与审计规范 — 脚本静默成功设计，正确审计方法
triggers:
  - 执行 task_recovery_cron.py 后验证结果
  - 派工板任务卡住排查
  - result_board 推送管道异常
---

# task_recovery_cron.py 执行与审计规范

## 触发场景
执行 task_recovery_cron.py 后，需要验证是否真正完成了恢复操作。

## 关键发现

### 1. 脚本设计：静默成功
- exit_code=0 但 stdout/stderr 全空是正常现象
- 所有操作日志写入 `/opt/data/secretary/logs/recovery/recovery_YYYYMMDD.log`
- 不产生任何终端输出（设计如此）

### 2. 审计正确方法
```python
# 读派工板
import json
with open("/opt/data/secretary/dispatch_board.json") as f:
    dispatch = json.load(f)
for t in dispatch.get("tasks", []):
    print(f"[{t['status']}] {t.get('task_id','?')} | {t.get('worker_type','?')} | created={t.get('created_at')}")

# 读结果板
with open("/opt/data/secretary/result_board.json") as f:
    result = json.load(f)
for r in result.get("results", []):
    print(f"[{r.get('status')}] {r.get('from_dispatch_id','?')} | {r.get('from_secretary','?')}")
```

### 3. pending_orphaned 任务不会被自动清理
- 脚本只恢复 `processing` 状态任务（超时重置为 pending）
- `pending_orphaned` 任务不会被自动删除或重置
- 需要人工决策是否手动清理
- 判断标准：created_at 超过 2h 无 worker 认领 → 孤立任务

### 4. 执行命令
```bash
python3 /opt/data/scripts/task_recovery_cron.py
```

## 审计检查清单
1. 读日志文件确认本次执行有记录
2. 扫派工板：processing=0 则无卡住任务
3. 扫 pending_orphaned：判断是否需要手动清理
4. 扫结果板：pushed 数量变化确认推送管道正常