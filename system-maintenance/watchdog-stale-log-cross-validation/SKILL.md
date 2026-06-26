---
name: watchdog-stale-log-cross-validation
description: Watchdog日志失真交叉验证诊断法 — 当日志显示"很久没更新"但实际任务在运行时，用三维度交叉验证法快速定位根因。触发：日志mtime旧/widget无反应/日志末尾时间戳与文件系统不符。
tags: [watchdog, cron, debug, diagnostics]
created: 2026-06-09
---

# Watchdog日志失真诊断技能

## 触发场景

watchdog/crontab脚本日志文件修改时间(MTIME)很旧，但实际任务在正常运行。典型症状：
- 日志文件`mtime`显示"很久没更新"
- 但`last_run_at`时间戳显示最近刚运行
- 或者日志末尾时间戳看起来很旧，但文件系统中有新产出

## 核心诊断方法

**交叉验证三步法**：

### Step 1：对比日志文件MTIME vs Job.last_run_at

```python
import json
from pathlib import Path
jobs = json.loads(Path('/opt/data/cron/jobs.json').read_text())
for j in jobs['jobs']:
    if 'watchdog' in j.get('name', ''):
        print(f"last_run_at: {j['last_run_at']}")
        print(f"last_status: {j['last_status']}")
        print(f"next_run_at: {j['next_run_at']}")

# 同时检查日志文件stat
log_stat = Path('/opt/data/logs/scheduler_watchdog.log').stat()
print(f"Log mtime: {log_stat.st_mtime}")
```

**判断规则**：
- `last_run_at` ≈ `日志文件mtime` → 日志正在写入，只是日志内容旧（正常）
- `last_run_at` 新 但 `日志文件mtime` 旧 → 日志写入失败或路径错误

### Step 2：直接扫描产出目录验证

不要只看日志，用`rglob`直接扫描产出目录的mtime：

```bash
# 最近N分钟的新文件数
find /opt/data/cron/output -name "*.md" -mmin -3 | wc -l

# 最近修改的子目录
ls -lt /opt/data/cron/output/ | head -20
```

### Step 3：检查job执行状态

```bash
# 查看hermes进程
ps aux | grep hermes | grep -v grep

# 验证hermes cron jobs列表
/opt/hermes/.venv/bin/hermes cron list 2>/dev/null
```

## 典型场景分析

### 场景：日志末尾时间旧，但watchdog正常运行

**症状**：
```
# 日志内容末尾
[06-08 19:59:00] OK (3个新文件, 最近: 7s ago)

# 但log文件mtime是03:59，和job.last_run_at一致
```

**根因**：
watchdog每分钟执行，每次都找到新文件，走OK分支。日志文件mtime = 最后一次关闭文件的时间，与日志内容时间戳无直接关联。追加写入同一文件时，内容可能已经被后续运行覆盖。

**验证**：用`stat`看文件真实`mtime`而非日志内容时间戳。

### 场景：强制tick但日志无记录

日志写了`rc=0`但后续产出恢复——说明强制tick成功但产出延迟，watchdog下次运行又找到了新文件。

## 关键教训

1. **日志内容时间戳 ≠ 日志文件mtime** — 文件系统层面的mtime才是写入真实时刻
2. **不要只看日志末尾** — 追加写入的文件末尾时间戳可能是缓存/显示问题
3. **交叉验证三维度**：Job.last_run_at + log.stat().st_mtime + 实际产出目录状态
4. **watchdog静默成功** — 多数情况下"强制tick"从未触发，因为Scheduler本身运行正常
