---
name: secretary-daemon-health-check
description: 秘书处守护进程深度健康诊断 — 追踪 result_board → 推送管道 → 死循环 → 无重启机制。触发：cron健康检查、守护进程疑似死亡、pending_push积压。
triggers: ["健康", "诊断", "秘书", "检查", "协调"]
version: 1.0
---

# 秘书处守护进程深度健康诊断

## 快速诊断命令（5秒定位）

```bash
# 1. 进程存活检查
ps aux | grep -E 'deputy|executive' | grep -v grep

# 2. 最后心跳时间（看哪个死了多久）
tail -1 /opt/data/secretary/logs/deputy_result.log
tail -1 /opt/data/secretary/logs/deputy_dispatch.log
tail -1 /opt/data/secretary/logs/deputy_worker.log


# 3. result_board pending_push 数量
python3 -c "import json; d=json.load(open('/opt/data/secretary/result_board.json')); p=[r for r in d.get('results',[]) if r.get('status')=='pending_push']; print(f'pending_push: {len(p)}')"

# 4. pending任务数量
python3 -c "import json; d=json.load(open('/opt/data/secretary/dispatch_board.json')); p=d.get('pending_tasks',[]); print(f'pending_tasks: {len(p)}'); [print(f'  {t.get(\"dispatch_id\")} | {t.get(\"type\")}') for t in p]"
```

## 完整诊断树

### 第一层：系统基础
```bash
uptime && free -h && df -h /opt
ps aux | grep hermes | grep -v grep      # gateway是否存活
curl -s --max-time 3 http://localhost:11434/  # ollama是否存活
```

### 第二层：派工板 + 成果板
- 路径: `/opt/data/secretary/dispatch_board.json`, `/opt/data/secretary/result_board.json`
- pending_tasks: 任务卡在pending多久了？
- pending_push: 成果是否在等推送？最早积压是哪个？
- completed_tasks: 最近完成的是什么？

### 第三层：锁文件 → 判断守护进程
```bash
# 所有锁文件及创建时间
for f in /tmp/*.lock; do echo "$(stat -c '%Y %y' $f) $f"; done | sort

# 关键锁文件:
# /tmp/deputy_dispatch.lock     → deputy_dispatch是否活着
# /tmp/deputy_worker.lock       → deputy_worker是否活着
# /tmp/deputy_result.lock       → deputy_result是否活着
# /tmp/executive_secretary.lock → executive_secretary是否活着
```
**原则**: 锁文件存在 ≠ 进程存活（进程崩溃后锁文件残留）。必须结合日志心跳时间判断。

### 第四层：追踪死循环（1852任务问题）
```bash
# deputy_dispatch 每3秒重复报"发现1852个新任务"，数字不变
tail -20 /opt/data/secretary/logs/deputy_dispatch.stdout.log
```
**根因**: 扫描 `/opt/data/async_tasks/` 历史任务文件（1852个），每次轮询都重复全量扫描 → 资源耗尽 → 崩溃。

### 第五层：推送管道追踪（最关键）

**架构真相（实测确认）**:
1. `deputy_result.py` → 写 `result_board.json` → status=`pending_push`
2. `deputy_result` **不推送**，只写文件
3. 真正推送发生在 `Avatar Worker` 内部：
   - `board_utils.py:100` 的 `_push_to_dongge()` 是内存函数
   - 只有 Avatar Worker 进程内才存在此函数
4. Gateway **不读** `result_board.json`
5. 结论：当所有 Avatar Worker 死掉，`pending_push` 会无限积压

**验证推送管道**:
```bash
```

## 已知根因模式

### 模式1: Deputy三组件 + Avatar 全部死亡（最常见）
**症状**: 56条pending_push积压，所有守护进程日志停在同一时间
**根因**: 无自动重启机制，守护进程手动启动，崩溃后不拉起
**修复**:
```bash
# 重启 deputy_result（最紧急，恢复推送）
rm -f /tmp/deputy_result.lock
python3 /opt/data/secretary/deputy_result.py &

# 重启其他守护进程
rm -f /tmp/deputy_dispatch.lock
python3 /opt/data/secretary/deputy_dispatch.py &
python3 /opt/data/secretary/deputy_worker.py &
```

### 模式2: deputy_dispatch 死循环（1852任务）
**症状**: 日志每3秒报"发现1852个新任务"，数字不变
**根因**: 扫描历史任务文件无过滤，每次重复扫描全量
**修复**: 添加扫描范围限制（只扫当日/新任务，避免重复扫描已处理文件）

### 模式3: PID 1 僵尸进程累积
**症状**: 12+个 `<defunct>` 进程，PPID=1
**根因**: Gateway (PID 1) fork子进程后未正确wait()回收
**当前影响**: 无危害，容器重启自动清理
**长期方案**: 给gateway加subprocess回收逻辑

## 关键文件速查表

| 文件 | 作用 | 生死判断依据 |
|------|------|------------|
| `/opt/data/secretary/deputy_dispatch.py` | 扫描任务→写派工板 | 日志心跳 |
| `/opt/data/secretary/deputy_worker.py` | 执行任务→写原始结果 | 日志心跳 |
| `/opt/data/secretary/deputy_result.py` | 收集结果→特秘推理→写成果板 | 日志心跳 |
| `/opt/data/secretary/executive_secretary.py` | 异步特助推理 | 日志心跳 |
| `/opt/data/secretary/result_board.json` | 所有成果（pending_push积压在此） | pending_push数量 |
| `/opt/data/secretary/dispatch_board.json` | 所有任务（pending/completed） | pending_tasks数量 |

## 推送恢复优先级
1. **deputy_result** — 积压成果只有它能写入pending_push
2. **Avatar daemon** — 只有它有`_push_to_dongge()`才能真正推送
3. **deputy_dispatch** — 新任务来源
4. **deputy_worker** — 任务执行
5. **executive_secretary** — 异步特助推理
