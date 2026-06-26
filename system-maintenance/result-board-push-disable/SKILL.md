---
name: result-board-push-disable
description: 永久禁用秘书处result_board飞书推送，保留任务处理链路
triggers:
  - 关闭秘书处刷屏推送
  - result_board推送永久停用
  - 推理秘书结果不推送飞书
---

# Result Board 推送永久禁用 Skill

## 触发场景
永久关闭秘书处 result_board 推送飞书通知，但保留任务处理链路。

## 完整操作步骤

### 第一步：清空积压的 pending_push
直接修改 result_board.json，把所有 pending_push 标记为 skipped_no_push：
```python
import json
with open('/opt/data/secretary/result_board.json') as f:
    board = json.load(f)

results = board.get('results', [])
for r in results:
    if r.get('status') == 'pending_push':
        r['status'] = 'skipped_no_push'
        r['skipped_at'] = datetime.now().isoformat()

board['results'] = results
board['last_updated'] = datetime.now().isoformat()
with open('/opt/data/secretary/result_board.json', 'w') as f:
    json.dump(board, f, ensure_ascii=False, indent=2)
```

### 第二步：堵死 queue_worker_cron.py 推送入口
文件：`/opt/data/scripts/queue_worker_cron.py`
找到 `if not pending:` 之后的推送循环，替换为：
```python
# 【2026-06-18修复】result_board推送已永久停用（刷屏问题）
pushed_ids = [r.get("id") for r in pending if r.get("id")]
for r in results:
    if r.get("id") in pushed_ids:
        r["status"] = "pushed"
        r["pushed_at"] = datetime.now().isoformat()

board["results"] = results
board["last_updated"] = datetime.now().isoformat()
write_json(RESULT_BOARD, board)
print(f"[OK] 已静默处理 {len(pushed_ids)} 条（不推送飞书）")
```

### 第三步：堵死 task_recovery_cron.py 两个入口
文件：`/opt/data/scripts/task_recovery_cron.py`

**入口1**：`recover_result_board()` 中的 completed→pending_push 迁移
```python
for r in results:
    # 【2026-06-18永久禁用】不再迁移任何状态到pending_push，推送已停用
    pass
```

**入口2**：`retry_stuck_pending_push()` 整体改为空操作
```python
def retry_stuck_pending_push():
    """【2026-06-18永久禁用】result_board推送已停用"""
    return [], []
```

### 第四步：修复 patch 导致的重复函数定义
多次 patch 同一函数容易留下两个 `def funcname`。验证：
```bash
grep -n "^def retry_stuck_pending_push" /opt/data/scripts/task_recovery_cron.py
```
如果两行，读取上下文后合并为单一函数定义。

### 第五步：语法验证
```bash
python3 -m py_compile /opt/data/scripts/task_recovery_cron.py
python3 -m py_compile /opt/data/scripts/queue_worker_cron.py
```

### 第六步：验证结果板状态
```python
with open('/opt/data/secretary/result_board.json') as f:
    board = json.load(f)
results = board.get('results', [])
pending = [r for r in results if r.get('status') == 'pending_push']
print(f"pending_push={len(pending)}")
```
预期：pending_push=0

## 关键教训
- patch 不能注释掉 if/for 行而保留循环体，会破坏缩进结构
- 多次 patch 同一区域可能留下重复函数定义，事后要 grep 验证
- 推送禁用必须同时处理三个入口：completed→pending_push迁移、pending_push→pushed推送、重试推送函数
