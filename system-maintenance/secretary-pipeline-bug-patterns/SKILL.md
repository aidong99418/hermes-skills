---
name: secretary-pipeline-bug-patterns
description: 秘书处管道Bug模式诊断与修复 — 派工板格式断链、成果板状态机断裂、result_board迁移机制。触发：任务卡住/通知不到/结果石沉大海时系统诊断。
triggers: ["秘书", "协调"]
version: 1.0
---

# 秘书处管道Bug模式诊断与修复

## 经验教训（2026-06-03全面诊断固化）

### 根因分层模型

| 层次 | 常见Bug | 症状 |
|------|--------|------|
| **格式层** | 写入方和读取方 schema 不一致 | 读不到任务、任务消失 |
| **状态机层** | 写入状态 != 读取方期望状态 | result_board 积压，永远推不出 |
| **推送层** | webhook 占位符 / open_message_id 失效 | 通知石沉大海 |
| **网关层** | recursion depth 过低 / timeout 过短 | 消息被丢队列、任务做一半被砍 |
| **执行层** | 无认领机制 / 无守护进程 | 任务写进板子但没人跑 |

---

## Bug模式0：`_migrate_board()` 迁移逻辑误判（2026-06-09 新发现）

### 现象
`deputy_result` 启动后立即 crash：`'str' object has no attribute 'get'`。但 `deputy_dispatch` 和 `deputy_worker` 同样有这个函数却"安全"运行。

### 根因：错误的格式检测条件

三态派工板有**三种格式**：
- **原始格式**：`{"tasks": [...]}` （旧数组）
- **当前格式**：`{"tasks": {"pending": [], "done": {}}}` （无 `processing` key）
- **真正新格式**：`{"tasks": {"pending": [], "processing": {}, "done": {}}}` （三态齐全）

迁移函数的检测条件有缺陷：
```python
# ❌ 错误条件
if "pending" in board.get("tasks", {}) and "processing" in board.get("tasks", {}):
    return board  # 认为是新格式，跳过迁移

# 实际情况：当前格式有 "pending" 但无 "processing" → 条件 False
# → 错误走旧迁移路径 → old_tasks = {"pending":[],"done":{}}
# → 遍历 dict.items() → 拿到 ("pending", []) 字符串key → str.get() 不存在
# → deputy_result crash（无 isinstance 保护）
# → deputy_dispatch/worker 不 crash（有 isinstance(t, dict) 保护）但迁移也被跳过
```

### 关键教训
- 有 `isinstance` 保护的代码**不等于正确**，它只是防止了 crash 但同时**静默跳过**了迁移逻辑
- 格式检测要用**正向判断**：先确认不是原始数组格式，再确认不是新格式，剩余才是需要迁移的旧格式

### 修复模板
```python
def _migrate_board(board):
    """旧格式数组→三态结构，自动执行一次"""
    if not isinstance(board.get("tasks"), dict):
        return board  # 既不是新格式也不是旧数组格式，安全返回
    tasks = board["tasks"]
    # 真正的新格式：tasks是dict且同时有pending(Array)和processing(Dict)
    if "pending" in tasks and "processing" in tasks:
        return board
    # 当前格式（2026-06-10后）：tasks={"pending":[], "done":{}}，无processing key
    old_tasks = (tasks.get("pending", [])
                 + list(tasks.get("done", {}).values())
                 + list(tasks.get("processing", {}).values()))
    new_tasks = {"pending": [], "processing": {}, "done": {}}
    for t in old_tasks:
        if not isinstance(t, dict):  # 防御：跳过非dict项
            continue
        sid = t.get("id") or t.get("task_id") or f"legacy_{len(new_tasks['done'])}"
        status = t.get("status", "pending")
        if status == "done":
            new_tasks["done"][sid] = t
        elif t.get("processing_at") and status == "pending":
            new_tasks["processing"][sid] = t
        else:
            new_tasks["pending"].append(t)
    board["tasks"] = new_tasks
    return board
```

### 诊断命令
```bash
# 直接测迁移函数逻辑
python3 -c "
import json
d = json.load(open('/opt/data/secretary/dispatch_board.json'))
tasks = d.get('tasks', {})
print('tasks类型:', type(tasks).__name__)
print('tasks keys:', list(tasks.keys()))
print('has pending?', 'pending' in tasks)
print('has processing?', 'processing' in tasks)
print('pending是数组?', isinstance(tasks.get('pending'), list))
"
```

---

## Bug模式1：派工板格式断链（最常见）

### 现象
cron 写 `{"version":"1.0","tasks":[...]}` 格式，但秘书脚本读 `{"pending_tasks":[]}` 格式。读不到 pending 任务。

### 诊断命令
```bash
python3 -c "
import json
with open('/opt/data/secretary/dispatch_board.json') as f:
    d = json.load(f)
print('keys:', list(d.keys()))
if 'tasks' in d:
    print('v1格式: tasks数组, 条数:', len(d.get('tasks',[])))
if 'pending_tasks' in d:
    print('v2格式: pending_tasks数组, 条数:', len(d.get('pending_tasks',[])))
"
```

### 修复：兼容层模式
```python
def load_board():
    raw = json.loads(BOARD.read_text())
    if "pending_tasks" in raw:
        return raw  # v2格式，直接返回
    # v1格式转换
    tasks = raw.get("tasks", [])
    pending = [t for t in tasks if t.get("status") in ("pending","processing")]
    completed = [t for t in tasks if t.get("status") == "done"]
    return {
        "pending_tasks": pending,
        "completed_tasks": completed,
        "_raw_tasks": tasks,
    }

def save_board(db):
    if "_raw_tasks" in db:
        raw_tasks = db.pop("_raw_tasks")
        status_map = {}
        for t in db.get("pending_tasks", []):
            status_map[t["task_id"]] = t.get("status","pending")
        for t in db.get("completed_tasks", []):
            status_map[t["task_id"]] = "done"
        for t in raw_tasks:
            if t.get("task_id") in status_map:
                t["status"] = status_map[t["task_id"]]
        BOARD.write_text(json.dumps({"version":"1.0","tasks":raw_tasks}, ...))
    else:
        BOARD.write_text(json.dumps(db, ...))
```

---

## Bug模式2：result_board 状态机断裂

### 现象
200条结果全是 `archived` 状态，queue_worker 找 `pending_push`，0条能推送。

### 根因
写入方写 `archived`，queue_worker 期望 `pending_push`，状态机断在中间。

### 诊断命令
```bash
python3 -c "
import json
from collections import Counter
with open('/opt/data/secretary/result_board.json') as f:
    d = json.load(f)
r = d.get('results', [])
print('总条数:', len(r))
print('状态分布:', Counter(x.get('status') for x in r))
"
```

### 修复：三处同时打补丁

1. **queue_worker_cron.py** — 自动迁移：
```python
pending = [r for r in results if r.get("status") == "pending_push"]
archived = [r for r in results if r.get("status") == "archived"]
if archived:
    for r in results:
        if r.get("status") == "archived":
            r["status"] = "pending_push"
    board["results"] = results
    write_json(RESULT_BOARD, board)
```

2. **iron_rules_registry.json** 的 result_pusher — 同理迁移

3. **根本修复** — 让写入方直接写正确状态

---

## Bug模式3：Gateway recursion depth 导致消息丢队列

### 现象
日志 `Interrupt recursion depth 3 reached for session xxx — queueing message instead of recursing`。用户感觉"发消息没反应"。

### 根因
`gateway/run.py` 硬编码 `_MAX_INTERRUPT_DEPTH = 3`，超过3层递归消息被丢进队列。subagent 并行调用时容易触发。

### 诊断命令
```bash
grep "recursion depth" /opt/data/logs/errors.log
```

### 修复
```python
# /opt/hermes/gateway/run.py line ~8134
_MAX_INTERRUPT_DEPTH = int(os.getenv("HERMES_MAX_INTERRUPT_DEPTH", 10))
```
**需要重启 gateway 生效。**

---

## Bug模式4：Terminal 超时砍断长任务

### 现象
日志 `Agent idle for 1803s (timeout 1800s)`，terminal 任务跑了30分钟被强制中断。

### 修复
```python
# /opt/hermes/gateway/run.py
_raw_stale_timeout = float(os.getenv("HERMES_AGENT_TIMEOUT", 3600))
```

---

## 完整诊断清单

```bash
# 1. 派工板格式
python3 -c "import json; d=json.load(open('/opt/data/secretary/dispatch_board.json')); print(list(d.keys())[:5])"

# 2. 结果板状态分布
python3 -c "import json; d=json.load(open('/opt/data/secretary/result_board.json')); from collections import Counter; r=d.get('results',[]); print(Counter(x.get('status') for x in r))"

# 3. recursion报错
grep "recursion depth" /opt/data/logs/errors.log | tail -5

# 4. 超时报错
grep "idle for.*timeout" /opt/data/logs/agent.log | tail -5
```

---

## 任务续接恢复 Cron
文件：`/opt/data/scripts/task_recovery_cron.py`（每5分钟执行）

**重要：此脚本不输出到 stdout**，exit_code=0 也不代表有任何操作。必须查看自己的日志文件：
```bash
cat /opt/data/secretary/logs/recovery/recovery_$(date +%Y%m%d).log
```

**board 结构（2026-06-06 实测确认）：**
- dispatch_board: `{"tasks": [...]}`，status 字段为 `completed`/`done`，无 `processing` 卡死
- result_board: `{"version", "last_updated", "results": [...]}`，**没有 `push_status` 字段**，推送状态用 `pushed_at` 字段判断（有值=已推送，None/空=未推送）

**诊断命令（直接用，不要用 task_recovery_cron.py 的 stdout）：**
```bash
# 派工板卡住任务
python3 -c "
import json
from collections import Counter
d = json.load(open('/opt/data/secretary/dispatch_board.json'))
tasks = d.get('tasks', [])
print('Total:', len(tasks), '|', Counter(t.get('status') for t in tasks))
stuck = [t for t in tasks if t.get('status') == 'processing']
print('Stuck (processing):', len(stuck))
"

# 结果板推送管道
python3 -c "
import json
d = json.load(open('/opt/data/secretary/result_board.json'))
results = d.get('results', [])
print('Total results:', len(results))
# 推送状态用 pushed_at 判断，不是 push_status
unpushed = [r for r in results if not r.get('pushed_at')]
print('Unpushed (no pushed_at):', len(unpushed))
pushed = [r for r in results if r.get('pushed_at')]
print('Pushed (has pushed_at):', len(pushed))
for r in unpushed[:5]:
    print(f'  [{r[\"id\"]}] created={r.get(\"created\",\"?\")[:19]}')
"
