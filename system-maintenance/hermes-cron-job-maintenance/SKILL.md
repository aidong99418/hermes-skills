---
name: hermes-cron-job-maintenance
description: Hermes scheduler cron jobs维护工作流 — 精简、去重、防burst。触发：job重复/撞车/重启卡顿时使用。
triggers:
  - 发现job重复或撞车
  - 重启后任务爆发卡顿
  - 需要精简或重排job
version: 1.0
---

# Hermes Cron Jobs 维护工作流

## 快速诊断
```bash
python3 -c "
import json
data = json.load(open('/opt/data/cron/jobs.json'))
jobs = data['jobs']
enabled = [j for j in jobs if j.get('enabled', True)]
print(f'总: {len(jobs)} 启用: {len(enabled)}')
for g in [0,60,300,600,1800,3600]:
    n = len([j for j in enabled if j.get('grace_seconds',0)==g])
    if n: print(f'  grace={g}s: {n}个')
"
```

## 常见问题

### burst爆发（重启卡顿根因）
系统cron + Hermes scheduler双套同时跑 → 所有miss的job重启瞬间一起执行

修复：加grace + 只用Hermes scheduler一套

### job重复撞车
- `skill健康守护` vs 技能卫士守护进程 → **删定时job**
- 多个每2小时白日梦 → **只留1个**
- 多个凌晨3点备份 → **合并**

### 彻底清系统cron
只删cron本身相关，不删其他功能配置文件：
- `/usr/sbin/cron` `/usr/bin/crontab` → 删除
- `/etc/crontab` + `cron.d/*` → 删除
- `/etc/supercat/spcrc-crontab` → **不删**（用户其他功能）

**注意**："cron额度文件"=cron相关配置，不是磁盘quota

## 维护纪律
- 删job直接删除，不留enabled=False残留
- 董哥要求直接干，不做冗余分析
