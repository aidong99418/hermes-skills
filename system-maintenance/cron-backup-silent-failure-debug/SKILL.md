---
name: cron-backup-silent-failure-debug
description: 诊断cron备份任务静默失败——job显示运行但备份文件未生成，标准输出为空。触发：manifest日期未更新/备份文件缺失/输出文件4KB空文件。
triggers: ["恢复", "调试", "定时", "错误", "bug", "cron", "调度", "备份"]
trigger: cron backup failed silently / 备份未生成但cron显示运行
tags: [cron, backup, debug]
version: 1.0
created: 2026-06-05
---

# Cron备份静默失败诊断流程

## 症状
- cron job `last_run_at` 已更新，但备份文件未生成
- manifest.json mtime 停在旧日期
- 输出文件大小 4096 字节（几乎为空 = 脚本无print输出）
- 备份脚本执行了，但静默中断

## 诊断三板斧

### 1. 交叉验证时间线
```python
import os
from datetime import datetime

# manifest mtime
mf_mtime = os.path.getmtime('/volume2/数据备份/memory_backup/manifest.json')
print(f"manifest: {datetime.fromtimestamp(mf_mtime).strftime('%Y-%m-%d %H:%M')}")

# 备份文件是否存在
date = "2026-06-04"
mem_bak = f"/volume2/数据备份/memory_backup/MEMORY_{date}.md"
print(f"MEMORY backup exists: {os.path.exists(mem_bak)}")

# cron job output mtime  
job_id = 'bc98a626ae1c'
out_mtime = os.path.getmtime(f'/opt/data/cron/output/{job_id}')
out_size = os.path.getsize(f'/opt/data/cron/output/{job_id}')
print(f"Output: {datetime.fromtimestamp(out_mtime)} - {out_size} bytes")
```

### 2. 检查输出文件内容
- 4096字节空输出 = 脚本捕获了异常但没print
- 0字节 = 脚本根本没运行到
- 正常输出应有 `✅ 备份完成` 字样

### 3. 直接运行脚本验证
```bash
python3 /opt/data/scripts/memory_backup.py
```
看是否有报错，是否生成了文件。

## 根因模式
1. `shutil.copy2` 源文件不存在（路径错误）→ 直接跳过，无报错
2. 脚本在Python虚拟环境外执行，import失败 → 静默退出
3. 权限问题 → 静默退出
4. Cron触发但实际执行的是旧版本脚本（prompts没更新）

## 修复方向
- 脚本开头加venv路径或用正确shebang
- 所有文件操作加try/except并print错误
- 备份前后对比文件数量/大小，不匹配则报警
