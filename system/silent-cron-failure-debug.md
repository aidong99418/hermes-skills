---
name: silent-cron-failure-debug
description: 诊断 cron 脚本静默失灵——脚本 exit 0 但什么都没干。根因：JSON 路径不匹配 + stale lock file。
trigger: cron 任务日志空/无输出/脚本 exit 0 但功能疑似不生效
tags: [cron, debug, lock-file, json-format-mismatch]
author: hermes
created: 2026-06-05
---

# 静默失灵诊断三板斧

## 症状
- cron 脚本 `exit 0` 但系统状态无变化
- 日志文件未生成或为空
- 锁文件残留导致后续实例直接退出

## 三步排查

### 第一板斧：锁文件
```bash
ls -la /tmp/*.lock /tmp/*recovery*.lock 2>/dev/null
cat /tmp/xxx_cron.lock  # 看残留 PID
ps aux | grep <PID>     # 确认进程是否还在跑
```
**处理：** 锁文件残留且进程已死 → 直接 `rm /tmp/xxx_cron.lock` 解锁

### 第二板斧：JSON 结构摸底
脚本假设的 board 格式 vs 实际格式可能不一致：
```python
import json
board = json.loads(Path("/opt/data/secretary/dispatch_board.json").read_text())
print(f"顶层字段: {list(board.keys())}")   # 看实际有什么字段
print(f"任务总数: {len(board.get('tasks', board.get('results', [])))}")
```
**常见不匹配：**
- 脚本查 `board['processing']`，实际是 `board['tasks']`
- 脚本查 `board['pending_push']`，实际用 `board['unread']`

### 第三板斧：直接执行看输出
```bash
python3 /opt/data/scripts/xxx_cron.py 2>&1
echo "EXIT: $?"
ls -la /opt/data/xxx/logs/  # 检查日志是否生成
```
**注意：** 如果 print() 被重定向到日志文件而非 stdout，脚本可能实际有输出但 cron 的 stdout capture 为空。

## 实战案例

### task_recovery_cron.py（2026-06-05）
- **症状：** 脚本 exit 0，无输出，无日志
- **根因1：** 锁文件 `/tmp/task_recovery_cron.lock` 残留 PID 3176，进程已死但锁未释放
- **根因2：** 脚本假设派工板结构为 `{"pending":[],"processing":[]}`，实际为 `{"tasks":[]}`，JSON 路径全不匹配导致扫描为空
- **结果：** 脚本"正确退出"，但什么都没做，pending_push 结果数为 0 是真实状态（无积压）而非扫描失败

### 修正方向
更新 task_recovery_cron.py 的 JSON 解析路径，或在脚本头部加一次格式探测。
