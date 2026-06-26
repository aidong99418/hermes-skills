---
name: unified-dispatcher-event-driven-architecture
description: 统一事件驱动派工守护进程 — 替代11个监控类 cron 轮询，用30秒防抖轮询11个路径实现事件驱动。触发：需要将散落的监控类 cron 合并为统一守护进程。
---

# 统一事件驱动派工守护进程

## 设计目标
用单个 daemon 替代11个散落的监控类 cron，实现：
- 30秒防抖轮询（避免频繁触发）
- 幂等去重（防止同一事件重复处理）
- 统一派工入口

## 监控路径（11个）
```python
WATCH_PATHS = [
    "/opt/data/secretary/dispatch_board.json",      # 派工板
    "/opt/data/secretary/result_board.json",       # 结果板
    "/opt/data/secretary/pending_push.json",      # 待推送队列
    "/opt/data/secretary/super_secretary_board.json",
    "/opt/data/ai_learning/pending_tasks.json",
    "/opt/data/brain/neural/evolution_state.json",
    "/opt/data/brain/neural/skill_neural.json",
    "/opt/data/brains/total_gems.json",
    "/opt/data/organs/organ_state.json",
    "/opt/data/ai_learning/pending_invitations.json",
    "/opt/data/mcp_tools/mcp_tools.json",
]
```

## 核心逻辑
```python
def scan_and_dispatch():
    for path in WATCH_PATHS:
        # 1. 防抖：检查文件 mtime，30秒内已处理过的跳过
        if is_recently_processed(path, debounce=30):
            continue
        # 2. 读取文件
        data = read_json(path)
        # 3. 派工：根据路径类型决定派给哪个执行器
        dispatch(data, path)
        # 4. 标记已处理
        mark_processed(path)

# 30秒轮询
while True:
    scan_and_dispatch()
    time.sleep(30)
```

## 防抖机制
防止同一文件在30秒内被多次处理：
```python
processed_cache = {}  # {path: last_processed_time}

def is_recently_processed(path, debounce=30):
    last = processed_cache.get(path, 0)
    return (time.time() - last) < debounce
```

## 派工规则
| 路径 | 执行器 | 说明 |
|---|---|---|
| dispatch_board.json | deputy_worker | pending 任务消费 |
| pending_push.json | woker | 推送队列 |
| pending_tasks.json | ai_learning | 学习任务 |
| 其他 | 对应子模块 | 各自处理 |

## 启动方式
```bash
nohup python3 /opt/data/scripts/unified_dispatcher.py \
    > /opt/data/logs/unified_dispatcher.log 2>&1 &
echo $! > /tmp/unified_dispatcher.pid
```

## 自启动
建议用 systemd service 或 rc.local确保重启后自动运行。

## 相关文件
- `/opt/data/scripts/unified_dispatcher.py` — 主脚本
- `/opt/data/secretary/dispatch_board.json` — 派工板
- `/opt/data/secretary/result_board.json` — 结果板

## 替代的 Cron（已暂停）
11个监控类 cronjob（brain_treasure_hunt、secretary_supervisor 等）已暂停，功能由本 daemon 覆盖。
