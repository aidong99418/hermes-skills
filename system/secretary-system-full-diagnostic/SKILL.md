---
name: secretary-system-full-diagnostic
description: V1秘书处系统全面诊断与修复——派工板格式/结果板/Daemon进程/神经网络/器官系统端到端排查，2026-06-21实操固化。
tags: [secretary, V1, daemon, dispatch-board, brain]
created: 2026-06-21
---

# V1秘书处系统全面诊断工作流

## 触发场景
- 派工任务写进去但没人处理
- result_board永远是空的
- Daemon进程状态不明
- 神经网络16天没更新
- 系统全面体检

## 诊断范围（按优先级）

### P0 必须查
1. **派工板格式** — `dispatch_board.json` 的 `tasks[]` vs `pending[]` 割裂问题
2. **Daemon进程** — `ps aux | grep deputy` 是否存活
3. **result_board** — 是否有真实内容写入
4. **派工链路端到端** — 写入→认领→执行→结果写回→推送

### P1 例行查
5. **神经网络** — `last_grow` 时间戳是否新鲜
6. **launch_daemons.sh** — 是否还在启动废弃的 `deputy_result.py`
7. **6个秘书子目录** — 是否只有空壳run.py

## 关键文件路径
```
/opt/data/secretary/
├── dispatch_board.json      # 派工板（写入方）
├── result_board.json       # 结果板（执行器写回）
├── deputy_dispatch.py      # 派工调度Daemon
├── deputy_worker.py        # 任务执行Daemon
├── active_pusher.py        # 结果推送Daemon（替换废弃的deputy_result.py）
└── launch_daemons.sh       # 启动脚本
```

## 已知Bug模式（记住）

### Bug1: 派工板格式割裂（最高频）
**现象**：任务写进dispatch_board但永远pending无人处理
**根因**：`dispatch_board.json` 有两套数据结构共存
- `tasks[]` — 实际有任务，`status="pending"`
- `pending[]` — 永远是空的
- `deputy_dispatch.py` 写入 `tasks[]`，但 `deputy_worker.py` 轮询 `pending[]`，永远匹配不到

**诊断命令**：
```bash
python3 -c "
import json
with open('/opt/data/secretary/dispatch_board.json') as f:
    d = json.load(f)
tasks = d.get('tasks', [])
pending = d.get('pending', [])
print(f'tasks: {len(tasks)}, pending: {len(pending)}')
for t in tasks:
    if t.get('status') == 'pending':
        print(f'  task {t.get(\"id\")} 在tasks里但status=pending')
"
```

**修复**：改 `deputy_worker.py` 的匹配逻辑，从 `pending[]` 改为 `tasks[]` 中 `status="pending" AND claimed_by is None`

### Bug2: Daemon全死
**现象**：ps没进程但PID文件还在
**诊断**：
```bash
ps aux | grep -E "deputy_dispatch|deputy_worker|active_pusher" | grep -v grep
```
**修复**：`bash /opt/data/secretary/launch_daemons.sh start`

### Bug3: result_board死节点
**现象**：`{"results":[],"last_updated":""}` 从未被写入
**诊断**：直接读文件看条数
```bash
python3 -c "
import json
with open('/opt/data/secretary/result_board.json') as f:
    d = json.load(f)
print(f'结果数: {len(d.get(\"results\",[]))}')
"
```
**修复**：在 `deputy_worker.py` 的任务完成逻辑里，加上写result_board的代码

### Bug4: launch_daemons.sh启动废弃进程
**现象**：`deputy_result.py` 已标注废弃，仍在启动列表
**诊断**：看launcher日志里deputy_result是否启动失败
**修复**：把 `DAEMONS` 数组里的 `deputy_result.py` 换成 `active_pusher.py`

### Bug5: 神经网络last_grow不更新
**现象**：`last_grow` 时间戳停在十几天前
**根因**：`grow_network()` 在 `total_activations == 0` 时早退（第1072行），跳过第5步元数据更新
**诊断**：
```bash
python3 -c "
import json
with open('/opt/data/brain/neural/connections.json') as f:
    d = json.load(f)
meta = d.get('_meta', {})
print(f'last_grow: {meta.get(\"last_grow\",\"无\")}')
"
```
**修复**：在早退分支里也写入元数据（第5步），保持last_grow鲜活

## 快速验证命令（6个）
```bash
# 1. Daemon进程
ps aux | grep -E "deputy_dispatch|deputy_worker|active_pusher" | grep -v grep

# 2. 派工板状态
python3 -c "
import json; d=json.load(open('/opt/data/secretary/dispatch_board.json'))
t=[x for x in d.get('tasks',[]) if x.get('status')=='pending']
print(f'pending任务: {len(t)}')
"

# 3. result_board
python3 -c "
import json; d=json.load(open('/opt/data/secretary/result_board.json'))
print(f'结果数: {len(d.get(\"results\",[]))}, 更新: {d.get(\"last_updated\",\"无\")}')
"

# 4. 神经网络
python3 -c "
import json; d=json.load(open('/opt/data/brain/neural/connections.json'))
m=d.get('_meta',{}); print(f'last_grow: {m.get(\"last_grow\",\"无\")}')
"

# 5. connections边数
python3 -c "
import json; d=json.load(open('/opt/data/brain/neural/connections.json'))
print(f'边数: {sum(len(v) for v in d.get(\"connections\",{}).values())}')
"

# 6. cron任务
bash /opt/data/secretary/launch_daemons.sh status
```

## 架构教训
- dispatch_board的写入方(deputy_dispatch)和读取方(deputy_worker)必须用同一套数据模型
- Daemon进程必须有进程监控+自动重启
- result_board是必须打通的节点，不能是死数据
- 废弃进程要及时从启动脚本移除
